from decimal import Decimal

from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.wirgarten.models import GrowingPeriod, Subscription


class BiddingRoundPreviousAmountService:
    @classmethod
    def get_previous_period(cls, bidding_round, cache: dict):
        cache_key = ("bidding_round_previous_period", bidding_round.id)
        if cache_key not in cache:
            cache[cache_key] = (
                GrowingPeriod.objects.filter(
                    end_date__lt=bidding_round.growing_period.start_date
                )
                .order_by("-end_date")
                .first()
            )
        return cache[cache_key]

    @classmethod
    def get_previous_contract_amount(
        cls, member_id, bidding_round, product_type_ids, cache
    ) -> Decimal:
        previous_period = cls.get_previous_period(bidding_round, cache)
        if previous_period is None:
            return Decimal("0")
        subscriptions = Subscription.objects.filter(
            member_id=member_id,
            period=previous_period,
            product__type_id__in=product_type_ids,
            cancellation_ts__isnull=True,
        ).select_related("product")
        return sum(
            (
                SubscriptionPriceCalculator.get_monthly_price(
                    subscription,
                    reference_date=previous_period.start_date,
                    cache=cache,
                )
                for subscription in subscriptions
            ),
            Decimal("0"),
        )

    @classmethod
    def get_previous_contribution(cls, member_id, bidding_round, cache) -> Decimal:
        previous_period = cls.get_previous_period(bidding_round, cache)
        if previous_period is None:
            return Decimal("0")
        return MemberSolidarityContributionService.get_member_contribution(
            member_id=member_id,
            reference_date=previous_period.start_date,
            cache=cache,
        ) or Decimal("0")

    @classmethod
    def get_previous_amount(
        cls, member_id, bidding_round, product_type_ids, cache
    ) -> Decimal | None:
        cache_key = (
            "bidding_round_previous_amount",
            bidding_round.id,
            member_id,
            tuple(sorted(product_type_ids)),
        )
        if cache_key in cache:
            return cache[cache_key]
        previous_period = cls.get_previous_period(bidding_round, cache)
        if previous_period is None:
            return None
        cache[cache_key] = cls.get_previous_contract_amount(
            member_id, bidding_round, product_type_ids, cache
        ) + cls.get_previous_contribution(member_id, bidding_round, cache)
        return cache[cache_key]
