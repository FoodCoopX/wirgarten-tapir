import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import BIDDING_ROUND_STATUS_CLOSED
from tapir.bidding_round.models import (
    BiddingRound,
    BiddingRoundCreatedSubscription,
)
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.services.non_bidder_contribution_service import (
    NonBidderContributionService,
)
from tapir.payments.services.mandate_reference_provider import (
    MandateReferenceProvider,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.utils import get_now

logger = logging.getLogger(__name__)


class ContractCreator:
    @classmethod
    def create_contracts_from_bids(
        cls,
        bidding_round,
        cache,
        bid_ids=None,
        actor=None,
        bid_level=None,
        create_auto_renewed_contracts=False,
    ):
        if bidding_round.status != BIDDING_ROUND_STATUS_CLOSED:
            raise ValidationError(
                _("Verträge können erst nach Ende der Beitragsrunde erstellt werden.")
            )
        if bidding_round.contracts_created_at is not None:
            raise ValidationError(
                _("Für diese Beitragsrunde wurden bereits Verträge erstellt.")
            )
        other_round_with_contracts = BiddingRound.objects.filter(
            growing_period=bidding_round.growing_period,
            contracts_created_at__isnull=False,
        ).exclude(pk=bidding_round.pk)
        if other_round_with_contracts.exists():
            raise ValidationError(
                _(
                    "Für diese Periode wurden bereits Verträge aus einer anderen Beitragsrunde erstellt."
                )
            )

        bids = list(bidding_round.bids.select_related("member").all())
        if bid_ids:
            selected_ids = {str(bid_id) for bid_id in bid_ids}
            bids = [bid for bid in bids if str(bid.id) in selected_ids]

        if bid_level is not None and bid_level not in range(
            1, (bidding_round.bid_levels or 1) + 1
        ):
            raise ValidationError(_("Unbekannte Gebotsstufe."))
        position = (
            BiddingRoundStatsService.get_level_position(bid_level, bidding_round)
            if bid_level is not None
            else BiddingRoundStatsService.get_default_position(
                bidding_round, cache=cache
            )
        )

        errors = []
        created_subscriptions = []
        for bid in bids:
            try:
                with transaction.atomic():
                    created_subscriptions.extend(
                        cls._create_contracts_for_bid(
                            bid,
                            bidding_round,
                            actor=actor,
                            cache=cache,
                            position=position,
                        )
                    )
            except ValidationError as error:
                errors.append(
                    {
                        "bid_id": bid.id,
                        "member": bid.member,
                        "error": str(error),
                    }
                )

        if create_auto_renewed_contracts:
            created_subscriptions.extend(
                cls._create_auto_renewed_contracts(bidding_round, cache=cache)
            )

        if created_subscriptions:
            NonBidderContributionService.apply_non_bidder_contributions(
                bidding_round, actor=actor, cache=cache
            )
            bidding_round.contracts_created_at = get_now(cache=cache)
            bidding_round.save(update_fields=["contracts_created_at", "updated_at"])

        logger.info(
            "Bidding round %s contract creation by %s: %s subscriptions created, %s errors",
            bidding_round.id,
            getattr(actor, "id", actor),
            len(created_subscriptions),
            len(errors),
        )
        return {"errors": errors, "subscriptions": created_subscriptions}

    @classmethod
    def _create_auto_renewed_contracts(cls, bidding_round, cache) -> list:
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        product_type_ids = set(
            bidding_round.product_types.values_list("product_type_id", flat=True)
        )
        try:
            renewing_subscriptions = AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=bidding_round.growing_period.start_date,
                cache=cache,
            )
        except KeyError:
            return []

        created = []
        for subscription in renewing_subscriptions:
            if subscription.member_id in bid_member_ids:
                continue
            if subscription.product.type_id not in product_type_ids:
                continue
            if Subscription.objects.filter(
                member_id=subscription.member_id,
                period=bidding_round.growing_period,
                product_id=subscription.product_id,
                cancellation_ts__isnull=True,
            ).exists():
                continue
            renewed_subscription = (
                AutomaticSubscriptionRenewalService.build_renewed_subscription(
                    subscription, cache=cache
                )
            )
            if renewed_subscription.period_id != bidding_round.growing_period_id:
                continue
            renewed_subscription.save()
            BiddingRoundCreatedSubscription.objects.create(
                round=bidding_round,
                subscription=renewed_subscription,
            )
            created.append(renewed_subscription)
        return created

    @classmethod
    def _create_contracts_for_bid(cls, bid, bidding_round, actor, cache, position):
        period = bidding_round.growing_period

        new_subscriptions = []
        for item in bid.items.select_related("product").all():
            subscription = cls._get_existing_subscription(bid.member, item, period)
            if subscription is None:
                subscription = cls._build_subscription(bid, item, period, cache)
                subscription.save()
            else:
                subscription.quantity = item.quantity
                subscription.price_override = None
                subscription.price_mode = Subscription.PriceMode.BIDDING_ROUND_BID
                subscription.save(
                    update_fields=[
                        "quantity",
                        "price_override",
                        "price_mode",
                        "updated_at",
                    ]
                )

            BiddingRoundCreatedSubscription.objects.create(
                round=bidding_round,
                subscription=subscription,
            )
            new_subscriptions.append(subscription)

        cls._assign_solidarity_contribution(
            bid, new_subscriptions, period, actor, cache, position, bidding_round
        )
        return new_subscriptions

    @classmethod
    def _get_existing_subscription(cls, member, item, period):
        """Contract creation never deletes anything: a subscription that already
        exists for the same member, product and season is reused and only its
        quantity is adjusted to the bid."""
        return (
            Subscription.objects.filter(
                member=member,
                period=period,
                product=item.product,
                cancellation_ts__isnull=True,
            )
            .order_by("created_at")
            .first()
        )

    @classmethod
    def _build_subscription(cls, bid, item, period, cache):
        now = get_now(cache=cache)
        return Subscription(
            member=bid.member,
            product=item.product,
            period=period,
            quantity=item.quantity,
            start_date=period.start_date,
            end_date=period.end_date,
            mandate_ref=MandateReferenceProvider.get_or_create_mandate_reference(
                member=bid.member, cache=cache
            ),
            consent_ts=now,
            withdrawal_consent_ts=now,
            auto_confirmed=now,
            price_override=None,
            price_mode=Subscription.PriceMode.BIDDING_ROUND_BID,
            notice_period_duration=NoticePeriodManager.get_notice_period_duration(
                product_type=item.product.type,
                growing_period=period,
                cache=cache,
            ),
            notice_period_unit=NoticePeriodManager.get_notice_period_unit(
                product_type=item.product.type,
                growing_period=period,
                cache=cache,
            ),
        )

    @classmethod
    def _assign_solidarity_contribution(
        cls, bid, new_subscriptions, period, actor, cache, position, bidding_round
    ):
        contract_monthly_total = sum(
            (
                SubscriptionPriceCalculator.get_monthly_price(
                    subscription, reference_date=period.start_date, cache=cache
                )
                for subscription in new_subscriptions
            ),
            Decimal("0"),
        )
        bid_monthly_total = sum(
            (
                BiddingRoundStatsService.get_effective_amount(
                    item, position, bidding_round
                )
                * item.quantity
                for item in bid.items.all()
            ),
            Decimal("0"),
        )
        MemberSolidarityContributionService.assign_contribution_to_member(
            member=bid.member,
            change_date=period.start_date,
            amount=bid_monthly_total - contract_monthly_total,
            cache=cache,
            actor=actor,
        )
