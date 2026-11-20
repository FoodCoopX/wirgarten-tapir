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
    def _validate_can_create_contracts(cls, bidding_round):
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
        if bidding_round.average_bid_locked_at is None:
            raise ValidationError(
                _(
                    "Das durchschnittliche Gebot muss fixiert sein, bevor Verträge erstellt werden können."
                )
            )

    @classmethod
    def create_contracts_from_bids(
        cls,
        bidding_round,
        cache,
        bid_ids=None,
        actor=None,
        bid_level=None,
        create_auto_renewed_contracts=False,
        auto_renewed_member_ids=None,
    ):
        cls._validate_can_create_contracts(bidding_round)

        bids = list(bidding_round.bids.select_related("member").all())
        if bid_ids:
            selected_ids = {str(bid_id) for bid_id in bid_ids}
            bids = [bid for bid in bids if str(bid.id) in selected_ids]

        unconfirmed_bids = [bid for bid in bids if bid.admin_confirmed is None]
        if unconfirmed_bids:
            raise ValidationError(
                _(
                    "Alle ausgewählten Gebote müssen bestätigt sein, bevor Verträge erstellt werden können. Noch unbestätigt: %(names)s"
                )
                % {"names": ", ".join(str(bid.member) for bid in unconfirmed_bids)}
            )
        capacity_errors = BiddingRoundStatsService.get_capacity_exceeded_errors(
            bidding_round, cache
        )
        if capacity_errors:
            raise ValidationError(" ".join(capacity_errors))

        is_locked = bidding_round.average_bid_locked_at is not None
        if (
            bid_level is not None
            and not is_locked
            and bid_level not in range(1, (bidding_round.bid_levels or 1) + 1)
        ):
            raise ValidationError(_("Unbekannte Gebotsstufe."))
        position = (
            BiddingRoundStatsService.get_level_position(bid_level, bidding_round)
            if bid_level is not None and not is_locked
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
                        "product_name": cls._get_bid_product_type_names(bid),
                    }
                )

        if create_auto_renewed_contracts:
            created_subscriptions.extend(
                cls._create_auto_renewed_contracts(
                    bidding_round,
                    cache=cache,
                    member_ids=auto_renewed_member_ids,
                )
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
    def check_contracts_from_bids(cls, bidding_round, cache, bid_ids=None) -> list:
        """Pre-check: returns one entry per bid that cannot be turned into a
        contract, without writing anything.

        A bid is rejected when it is not confirmed yet or when the round's bids
        and auto-renewals exceed the share or pickup location capacity.
        """
        bids = list(bidding_round.bids.select_related("member").all())
        if bid_ids:
            selected_ids = {str(bid_id) for bid_id in bid_ids}
            bids = [bid for bid in bids if str(bid.id) in selected_ids]

        capacity_errors = BiddingRoundStatsService.get_capacity_exceeded_errors(
            bidding_round, cache
        )
        if capacity_errors and bids:
            first_bid = bids[0]
            errors = [
                {
                    "bid_id": first_bid.id,
                    "member": first_bid.member,
                    "error": " ".join(capacity_errors),
                    "product_name": cls._get_bid_product_type_names(first_bid),
                }
            ]
        else:
            errors = []

        for bid in bids:
            if bid.admin_confirmed is None:
                errors.append(
                    {
                        "bid_id": bid.id,
                        "member": bid.member,
                        "error": str(
                            _(
                                "Das Gebot ist noch nicht bestätigt und kann noch nicht in einen Vertrag überführt werden."
                            )
                        ),
                        "product_name": cls._get_bid_product_type_names(bid),
                    }
                )
        return errors

    @classmethod
    def _get_bid_product_type_names(cls, bid) -> str:
        return ", ".join(
            sorted(
                {
                    item.product.type.name
                    for item in bid.items.select_related("product__type").all()
                }
            )
        )

    @classmethod
    def _create_auto_renewed_contracts(
        cls, bidding_round, cache, member_ids=None
    ) -> list:
        context = cls._build_auto_renewal_context(bidding_round, member_ids, cache)
        if context is None:
            return []
        bid_member_ids, product_type_ids, selected_member_ids, subscriptions = context

        created = []
        for subscription in subscriptions:
            if not cls._should_renew_subscription(
                subscription,
                bid_member_ids,
                product_type_ids,
                selected_member_ids,
                bidding_round,
            ):
                continue
            renewed_subscription = cls._create_renewed_subscription(
                subscription, bidding_round, cache
            )
            if renewed_subscription is not None:
                created.append(renewed_subscription)
        return created

    @classmethod
    def _build_auto_renewal_context(cls, bidding_round, member_ids, cache):
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
            return None
        selected_member_ids = (
            {str(member_id) for member_id in member_ids}
            if member_ids is not None
            else None
        )
        return (
            bid_member_ids,
            product_type_ids,
            selected_member_ids,
            renewing_subscriptions,
        )

    @classmethod
    def _should_renew_subscription(
        cls,
        subscription,
        bid_member_ids,
        product_type_ids,
        selected_member_ids,
        bidding_round,
    ) -> bool:
        if subscription.member_id in bid_member_ids:
            return False
        if subscription.product.type_id not in product_type_ids:
            return False
        if (
            selected_member_ids is not None
            and subscription.member_id not in selected_member_ids
        ):
            return False
        return not Subscription.objects.filter(
            member_id=subscription.member_id,
            period=bidding_round.growing_period,
            product_id=subscription.product_id,
            cancellation_ts__isnull=True,
        ).exists()

    @classmethod
    def _create_renewed_subscription(cls, subscription, bidding_round, cache):
        renewed_subscription = (
            AutomaticSubscriptionRenewalService.build_renewed_subscription(
                subscription, cache=cache
            )
        )
        if renewed_subscription.period_id != bidding_round.growing_period_id:
            return None
        if subscription.price_override == 0:
            renewed_subscription.price_override = Decimal("0")
        else:
            renewed_subscription.price_override = None
        renewed_subscription.price_mode = (
            Subscription.PriceMode.BIDDING_ROUND_AUTO_RENEWED
        )
        renewed_subscription.save()
        BiddingRoundCreatedSubscription.objects.create(
            round=bidding_round,
            subscription=renewed_subscription,
            is_bidder_contract=False,
        )
        return renewed_subscription

    @classmethod
    def _create_contracts_for_bid(cls, bid, bidding_round, actor, cache, position):
        period = bidding_round.growing_period

        new_subscriptions = []
        for item in bid.items.select_related("product").all():
            subscription = cls._get_existing_subscription(bid.member, item, period)
            was_reused = subscription is not None
            original_quantity = subscription.quantity if was_reused else None
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
                is_bidder_contract=True,
                was_reused=was_reused,
                original_quantity=original_quantity,
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
