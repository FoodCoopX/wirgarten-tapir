import logging
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from tapir.bidding_round.config import BIDDING_ROUND_STATUS_CLOSED
from tapir.bidding_round.models import (
    Bid,
    BiddingRound,
    BiddingRoundCreatedSubscription,
    BiddingRoundProductPrice,
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
from tapir.wirgarten.forms.subscription import cancel_or_delete_subscriptions
from tapir.wirgarten.models import GrowingPeriod, Member, Product, Subscription
from tapir.wirgarten.utils import get_now, get_today

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ContractCreationError:
    bid_id: str
    member: Member
    error: str


@dataclass(frozen=True)
class ContractCreationResult:
    errors: list[ContractCreationError]
    subscriptions: list[Subscription]


class ContractCreator:
    @classmethod
    def validate_round_can_create_contracts(cls, bidding_round: BiddingRound) -> None:
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

    @classmethod
    def create_contracts_from_bids(
        cls,
        bidding_round: BiddingRound,
        cache: dict,
        bid_ids: list[str] | None = None,
        actor: Member | None = None,
        bid_level: int | None = None,
        create_auto_renewed_contracts: bool = False,
    ) -> ContractCreationResult:
        cls.validate_round_can_create_contracts(bidding_round)

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

        bids = bidding_round.bids.select_related("member", "product")
        if bid_ids:
            bids = bids.filter(id__in=bid_ids)

        errors: list[ContractCreationError] = []
        created_subscriptions: list[Subscription] = []
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
                    ContractCreationError(
                        bid_id=bid.id,
                        member=bid.member,
                        error=str(error),
                    )
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
        return ContractCreationResult(
            errors=errors, subscriptions=created_subscriptions
        )

    @classmethod
    def _create_auto_renewed_contracts(
        cls, bidding_round: BiddingRound, cache: dict
    ) -> list[Subscription]:
        bid_member_ids = set(bidding_round.bids.values_list("member_id", flat=True))
        product_type_id = bidding_round.product_type_id
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
            if subscription.product.type_id != product_type_id:
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
                monthly_price_per_share=cls._get_auto_renewed_price_per_share(
                    bidding_round, renewed_subscription.product, cache
                ),
            )
            created.append(renewed_subscription)
        return created

    @classmethod
    def _get_auto_renewed_price_per_share(
        cls, bidding_round: BiddingRound, product: Product, cache: dict
    ) -> Decimal:
        """The round price for a member who did not bid.

        Non-bidders pay at least the round's reference value; if the bidders' rate is
        higher, it wins. The per-share amount is scaled to the product's share size and
        frozen on the link, so later round changes cannot move the contract's price.
        """
        price = BiddingRoundProductPrice.objects.filter(
            round=bidding_round,
            product=product,
        ).first()
        rate = BiddingRoundStatsService.build_non_bidder_rate_per_share(
            bidding_round, cache
        )
        if price is not None and price.reference_value is not None:
            rate = max(price.reference_value, rate)
        size = BiddingRoundStatsService.get_product_size(
            product, bidding_round, cache
        )
        return (rate * size).quantize(Decimal("0.0001"))

    @classmethod
    def _create_contracts_for_bid(
        cls,
        bid: Bid,
        bidding_round: BiddingRound,
        actor: Member | None,
        cache: dict,
        position,
    ) -> list[Subscription]:
        period = bidding_round.growing_period
        cls._replace_other_share_sizes(bid, bidding_round, actor, cache)
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
            monthly_price_per_share=cls._get_price_per_share(
                bid, bidding_round, cache, position
            ),
        )
        subscriptions = [subscription]

        cls._assign_solidarity_contribution(
            bid, subscriptions, period, actor, cache, position, bidding_round
        )
        return subscriptions

    @classmethod
    def _replace_other_share_sizes(
        cls, bid: Bid, bidding_round: BiddingRound, actor: Member | None, cache: dict
    ) -> None:
        """Replaces the member's contracts of other share sizes in the round's period.

        The auto-renewal can create a contract for the coming season before the round
        creates anything, so a bid on another size would otherwise result in two
        contracts: the old one keeps its own price and only the new one is priced from
        the round. A contract that already started is not replaced; the bid is
        reported as an error instead.
        """
        conflicting = Subscription.objects.filter(
            member=bid.member,
            period=bidding_round.growing_period,
            product__type_id=bidding_round.product_type_id,
            cancellation_ts__isnull=True,
        ).exclude(product_id=bid.product_id)
        if conflicting.filter(start_date__lte=get_today(cache=cache)).exists():
            raise ValidationError(
                _(
                    "Für dieses Mitglied läuft in dieser Periode bereits ein Vertrag einer anderen Anteilsgröße. Der Wechsel muss manuell geklärt werden."
                )
            )
        cancel_or_delete_subscriptions(
            member=bid.member,
            start_date=bidding_round.growing_period.start_date,
            product_type=bidding_round.product_type,
            actor=actor,
            exclude_product_id=bid.product_id,
            cache=cache,
        )

    @classmethod
    def _get_price_per_share(
        cls, bid: Bid, bidding_round: BiddingRound, cache: dict, position
    ) -> Decimal:
        """The round's average bid per share, scaled to the bid's share size.

        Freezing it on the link makes the contract's price independent of later
        changes to the round or to ``ProductPrice``.
        """
        average_per_share = (
            BiddingRoundStatsService.get_bidder_average_per_share_per_month(
                bidding_round, position, cache=cache
            )
        )
        size = BiddingRoundStatsService.get_product_size(
            bid.product, bidding_round, cache
        )
        return (average_per_share * size).quantize(Decimal("0.0001"))

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
        position,
        bidding_round: BiddingRound,
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
        bid_monthly_total = (
            BiddingRoundStatsService.get_effective_amount(bid, position, bidding_round)
            * bid.quantity
        )
        MemberSolidarityContributionService.assign_contribution_to_member(
            member=bid.member,
            change_date=period.start_date,
            amount=bid_monthly_total - contract_monthly_total,
            cache=cache,
            actor=actor,
        )
