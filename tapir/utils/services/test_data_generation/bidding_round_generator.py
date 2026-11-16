import datetime
import random
from decimal import Decimal

from tapir.bidding_round.config import BIDDING_ROUND_PROCEDURE_BID_RANGE
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.bidding_round.services.product_size_service import ProductSizeService
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    Product,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_now, get_today

HARVEST_SHARE_PRODUCT_TYPE_NAME = "Ernteanteile"
REFERENCE_VALUE_PER_SIZE = Decimal("80.00")
MIN_AMOUNT_PER_SIZE = Decimal("60.00")
TARGET_COVERAGE_RATIO = Decimal("0.91")
BID_RANGE_TARGET_RATIOS = {
    1: Decimal("0.81"),
    2: Decimal("1.01"),
}
BIDDER_RATIO = 0.6
BID_FACTOR_RANGE = (0.85, 1.15)


class BiddingRoundGenerator:
    """Creates the demo rounds for the next growing period.

    An active BIDDING_ROUND_PROCEDURE_SIMPLE round shows the reference value scaled by
    the share size; about 60 % of the members with an active harvest share
    subscription bid, with a small random factor, and the target is derived so the
    evaluation shows about 91 % coverage. A closed
    BIDDING_ROUND_PROCEDURE_BID_RANGE round reuses the same bidders with two amounts
    calibrated to 81 % (green) and 101 % (red), so the middle position stays at
    91 %.
    """

    @classmethod
    def generate_bidding_round(cls, cache=None):
        cache = cache or {}

        for key in (
            ParameterKeys.BIDDING_ROUND_ENABLED,
            ParameterKeys.BIDDING_ROUND_URL_ENABLED,
        ):
            TapirParameter.objects.filter(key=key).update(value=True)

        today = get_today(cache=cache)
        now = get_now(cache=cache)
        growing_period = (
            GrowingPeriod.objects.filter(start_date__gt=today)
            .order_by("start_date")
            .first()
            or GrowingPeriod.objects.order_by("start_date").last()
        )
        current_period = (
            GrowingPeriod.objects.filter(start_date__lte=today, end_date__gte=today)
            .order_by("start_date")
            .first()
        )
        product_type = ProductType.objects.filter(
            name=HARVEST_SHARE_PRODUCT_TYPE_NAME
        ).first()
        if growing_period is None or current_period is None or product_type is None:
            return None

        products = list(Product.objects.filter(type=product_type, deleted=False))
        if not products:
            return None

        subscriptions_by_member_id = {}
        for subscription in Subscription.objects.filter(
            period=current_period,
            product__type=product_type,
            cancellation_ts__isnull=True,
        ).select_related("product"):
            subscriptions_by_member_id.setdefault(subscription.member_id, subscription)
        if not subscriptions_by_member_id:
            return None

        random.seed("bidding_round")
        bidders = [
            Member.objects.get(id=member_id)
            for member_id in subscriptions_by_member_id
            if random.random() < BIDDER_RATIO
        ]

        assignments = []
        for member in bidders:
            subscription = subscriptions_by_member_id[member.id]
            product = subscription.product
            size = cls._get_size_or_one(product, growing_period, cache)
            factor = Decimal(str(round(random.uniform(*BID_FACTOR_RANGE), 3)))
            amount = (REFERENCE_VALUE_PER_SIZE * size * factor).quantize(
                Decimal("0.01")
            )
            assignments.append((member, product, subscription.quantity, amount))

        reached_per_year = sum(
            (amount * quantity * 12 for _, _, quantity, amount in assignments),
            Decimal("0"),
        )
        target_amount_per_year = (reached_per_year / TARGET_COVERAGE_RATIO).quantize(
            Decimal("0.01")
        )

        prices = [
            {
                "product_id": product.id,
                "reference_value": str(
                    REFERENCE_VALUE_PER_SIZE
                    * cls._get_size_or_one(product, growing_period, cache)
                ),
                "min_amount": str(
                    MIN_AMOUNT_PER_SIZE
                    * cls._get_size_or_one(product, growing_period, cache)
                ),
                "size": str(cls._get_size_or_one(product, growing_period, cache)),
            }
            for product in products
        ]

        cls._create_closed_bid_range_round(
            growing_period=growing_period,
            name=f"Beitragsrunde {growing_period.start_date.year} - Gebotsspanne",
            start_at=now - datetime.timedelta(days=1),
            end_at=now + datetime.timedelta(days=30),
            product_type_id=product_type.id,
            target_amount_per_year=target_amount_per_year,
            prices=prices,
            assignments=assignments,
            cache=cache,
        )

        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name=f"Beitragsrunde {growing_period.start_date.year}",
            start_at=now - datetime.timedelta(days=1),
            end_at=now + datetime.timedelta(days=30),
            product_type_id=product_type.id,
            target_amount_per_year=target_amount_per_year,
            prices=prices,
            cache=cache,
        )
        BiddingRoundService.start_round(bidding_round, cache=cache)

        round_product_type = bidding_round.product_types.first()
        for member, product, quantity, amount in assignments:
            BiddingRoundService.save_bid(
                member,
                bidding_round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "quantity": quantity,
                        "amount_1": str(amount),
                    }
                ],
                cache=cache,
            )

        return bidding_round

    @classmethod
    def _get_size_or_one(cls, product, growing_period, cache) -> Decimal:
        size = ProductSizeService.get_size(product, growing_period, cache)
        return size if size is not None else Decimal("1")

    @classmethod
    def _create_closed_bid_range_round(
        cls,
        *,
        growing_period,
        name,
        start_at,
        end_at,
        product_type_id,
        target_amount_per_year,
        prices,
        assignments,
        cache,
    ):
        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name=name,
            start_at=start_at,
            end_at=end_at,
            product_type_id=product_type_id,
            target_amount_per_year=target_amount_per_year,
            prices=prices,
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE,
            bid_levels=2,
            cache=cache,
        )
        BiddingRoundService.start_round(bidding_round, cache=cache)

        round_product_type = bidding_round.product_types.first()
        middle_ratio = TARGET_COVERAGE_RATIO
        for member, product, quantity, amount in assignments:
            green = (amount * BID_RANGE_TARGET_RATIOS[1] / middle_ratio).quantize(
                Decimal("0.01")
            )
            red = (amount * BID_RANGE_TARGET_RATIOS[2] / middle_ratio).quantize(
                Decimal("0.01")
            )
            BiddingRoundService.save_bid(
                member,
                bidding_round,
                [
                    {
                        "round_product_type_id": round_product_type.id,
                        "product_id": product.id,
                        "quantity": quantity,
                        "amount_1": str(green),
                        "amount_2": str(red),
                    }
                ],
                cache=cache,
            )

        BiddingRoundService.close_round(bidding_round, cache=cache)
        return bidding_round
