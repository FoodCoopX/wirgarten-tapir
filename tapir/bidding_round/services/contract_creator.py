import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import BIDDING_ROUND_STATUS_CLOSED
from tapir.bidding_round.models import (
    Bid,
    BiddingRound,
    BiddingRoundCreatedSubscription,
)
from tapir.payments.services.mandate_reference_provider import (
    MandateReferenceProvider,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.models import GrowingPeriod, Member, Product, Subscription
from tapir.wirgarten.utils import get_now

logger = logging.getLogger(__name__)


class ContractCreator:
    @classmethod
    def create_contracts_from_bids(
        cls,
        bidding_round: BiddingRound,
        cache: dict,
        bid_ids: list[str] | None = None,
        actor: Member | None = None,
    ) -> dict:
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

        bids = list(bidding_round.bids.select_related("member", "product").all())
        if bid_ids:
            selected_ids = {str(bid_id) for bid_id in bid_ids}
            bids = [bid for bid in bids if str(bid.id) in selected_ids]

        errors = []
        created_subscriptions = []
        for bid in bids:
            try:
                with transaction.atomic():
                    created_subscriptions.extend(
                        cls._create_contracts_for_bid(
                            bid, bidding_round, actor=actor, cache=cache
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

        if created_subscriptions:
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
    def _create_contracts_for_bid(
        cls,
        bid: Bid,
        bidding_round: BiddingRound,
        actor: Member | None,
        cache: dict,
    ) -> list[Subscription]:
        period = bidding_round.growing_period
        subscription = cls._get_existing_subscription(bid.member, bid.product, period)
        if subscription is None:
            subscription = cls._build_subscription(bid, period, cache)
            subscription.save()
        else:
            subscription.quantity = bid.quantity
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
        subscriptions = [subscription]

        cls._assign_solidarity_contribution(bid, subscriptions, period, actor, cache)
        return subscriptions

    @classmethod
    def _get_existing_subscription(
        cls, member: Member, product: Product, period: GrowingPeriod
    ) -> Subscription | None:
        """Contract creation never deletes anything: a subscription that already
        exists for the same member, product and season is reused and only its
        quantity is adjusted to the bid."""
        return (
            Subscription.objects.filter(
                member=member,
                period=period,
                product=product,
                cancellation_ts__isnull=True,
            )
            .order_by("created_at")
            .first()
        )

    @classmethod
    def _build_subscription(
        cls, bid: Bid, period: GrowingPeriod, cache: dict
    ) -> Subscription:
        now = get_now(cache=cache)
        return Subscription(
            member=bid.member,
            product=bid.product,
            period=period,
            quantity=bid.quantity,
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
                product_type=bid.product.type,
                growing_period=period,
                cache=cache,
            ),
            notice_period_unit=NoticePeriodManager.get_notice_period_unit(
                product_type=bid.product.type,
                growing_period=period,
                cache=cache,
            ),
        )

    @classmethod
    def _assign_solidarity_contribution(
        cls,
        bid: Bid,
        new_subscriptions: list[Subscription],
        period: GrowingPeriod,
        actor: Member | None,
        cache: dict,
    ) -> None:
        contract_monthly_total = sum(
            (
                SubscriptionPriceCalculator.get_monthly_price(
                    subscription, reference_date=period.start_date, cache=cache
                )
                for subscription in new_subscriptions
            ),
            Decimal("0"),
        )
        bid_monthly_total = (bid.amount_1 or Decimal("0")) * bid.quantity
        MemberSolidarityContributionService.assign_contribution_to_member(
            member=bid.member,
            change_date=period.start_date,
            amount=bid_monthly_total - contract_monthly_total,
            cache=cache,
            actor=actor,
        )
