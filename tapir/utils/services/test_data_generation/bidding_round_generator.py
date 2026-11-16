import datetime
import random
from decimal import Decimal

from tapir.bidding_round.config import (
    BIDDING_ROUND_PROCEDURE_BID_RANGE,
    BIDDING_ROUND_PROCEDURE_SIMPLE,
)
from tapir.bidding_round.services.bid_input import BidInput
from tapir.bidding_round.services.bidding_round_service import (
    BiddingRoundService,
    RoundPriceInput,
)
from tapir.bidding_round.services.bidding_round_stats_service import (
    BiddingRoundStatsService,
)
from tapir.bidding_round.services.product_size_service import ProductSizeService
from tapir.configuration.models import TapirParameter
from tapir.configuration.parameter import get_parameter_value
from tapir.utils.services.test_data_generation.constants import (
    HARVEST_SHARE_PRODUCT_TYPE_NAME,
)
from tapir.wirgarten.models import (
    GrowingPeriod,
    Product,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.utils.config import Organization
from tapir.utils.services.test_data_generation.vierlande_generator import (
    VierlandeGenerator,
)
from tapir.wirgarten.utils import get_now, get_today

REFERENCE_VALUE_PER_SIZE = Decimal("80.00")
MIN_AMOUNT_PER_SIZE = Decimal("40.00")
TARGET_AMOUNT_PER_YEAR = VierlandeGenerator.BIDDING_ROUND_TARGET_AMOUNT_PER_YEAR
TARGET_COVERAGE_RATIO = Decimal("0.91")
BID_RANGE_TARGET_RATIOS = {
    1: Decimal("0.81"),
    2: Decimal("1.01"),
}
SIMPLE_LEVEL_TARGET_RATIOS = {
    1: Decimal("0.81"),
    2: Decimal("0.91"),
    3: Decimal("1.09"),
}
BIDDER_RATIO = 0.6
BIDDER_RATIO_WITHOUT_RENEWAL = 0.9
AUTO_RENEW_RATIO = 0.3
BID_FACTOR_RANGE = (0.85, 1.15)
RANDOM_SEED = "bidding_round"


class BiddingRoundGenerator:
    """Creates the demo rounds for the next growing period.

    The member split follows the automatic renewal setting. With automatic renewal
    60 % of the members bid, 30 % keep renewing automatically and the remaining
    members are cancelled so their shares stay free. Without automatic renewal 90 %
    bid and 10 % are cancelled. Every bidder bids on the product, size and quantity
    of their existing subscription; the pickup location is derived from the member's
    existing depot by the bid service.

    One active BIDDING_ROUND_PROCEDURE_SIMPLE round shows the calibrated middle
    amount. A closed BIDDING_ROUND_PROCEDURE_BID_RANGE round and a closed
    BIDDING_ROUND_PROCEDURE_SIMPLE round with three levels reuse the same bidders and
    amounts. The level amounts are calibrated so that bids plus auto-renewed
    contributions plus the delivery charges and membership fees of the round reach
    81/91/109 % of the target. The bid range reaches 81 % (green) and 101 % (red), so
    its middle position is 91 % as well. Vierlande keeps the configured target
    amount; every other organization derives the target from the reference bids plus
    the fixed contributions so the amounts stay close to the reference value.

    If the fixed contributions still exceed the target, the amounts fall back to the
    reference value scaled by the ratios.
    """

    @classmethod
    def generate_bidding_round(cls, cache=None, organization=None):
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

        subscriptions = list(
            Subscription.objects.filter(
                period=current_period,
                product__type=product_type,
                product__deleted=False,
                cancellation_ts__isnull=True,
            )
            .select_related("product", "member")
            .order_by("member_id", "id")
        )
        if not subscriptions:
            return None

        subscriptions_by_member_id = {}
        for subscription in subscriptions:
            subscriptions_by_member_id.setdefault(subscription.member_id, subscription)

        member_ids = sorted(subscriptions_by_member_id)
        random_generator = random.Random(RANDOM_SEED)
        random_generator.shuffle(member_ids)

        automatic_renewal_enabled = cls._is_automatic_renewal_enabled(cache)
        bidder_ratio = (
            BIDDER_RATIO if automatic_renewal_enabled else BIDDER_RATIO_WITHOUT_RENEWAL
        )
        auto_renew_ratio = (
            AUTO_RENEW_RATIO if automatic_renewal_enabled else Decimal("0")
        )
        bidder_count = int(len(member_ids) * bidder_ratio)
        auto_renew_count = int(len(member_ids) * auto_renew_ratio)
        bidder_ids = set(member_ids[:bidder_count])
        free_ids = set(member_ids[bidder_count + auto_renew_count :])

        if free_ids:
            Subscription.objects.filter(
                member_id__in=free_ids,
                period=current_period,
                product__type=product_type,
                cancellation_ts__isnull=True,
            ).update(cancellation_ts=now)

        assignments = []
        for member_id in member_ids:
            if member_id not in bidder_ids:
                continue
            subscription = subscriptions_by_member_id[member_id]
            assignments.append(
                {
                    "member": subscription.member,
                    "product": subscription.product,
                    "size": cls._get_size_or_one(
                        subscription.product, growing_period, cache
                    ),
                    "quantity": subscription.quantity,
                    "factor": Decimal(
                        str(round(random_generator.uniform(*BID_FACTOR_RANGE), 3))
                    ),
                }
            )
        if not assignments:
            return None

        prices = [
            RoundPriceInput(
                product_id=product.id,
                reference_value=(
                    REFERENCE_VALUE_PER_SIZE
                    * cls._get_size_or_one(product, growing_period, cache)
                ).quantize(Decimal("0.01")),
                min_amount=(
                    MIN_AMOUNT_PER_SIZE
                    * cls._get_size_or_one(product, growing_period, cache)
                ).quantize(Decimal("0.01")),
                size=cls._get_size_or_one(product, growing_period, cache),
            )
            for product in products
        ]

        year = growing_period.start_date.year
        start_at = now - datetime.timedelta(days=1)
        end_at = now + datetime.timedelta(days=30)

        bid_range_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name=f"Beitragsrunde {year} - Gebotsspanne",
            start_at=start_at,
            end_at=end_at,
            product_type_id=product_type.id,
            target_amount_per_year=TARGET_AMOUNT_PER_YEAR,
            prices=prices,
            bidding_procedure=BIDDING_ROUND_PROCEDURE_BID_RANGE,
            bid_levels=2,
            include_auto_renewed=True,
            cache=cache,
        )
        BiddingRoundService.start_round(bid_range_round, cache=cache)

        cls._save_bids(
            bid_range_round,
            assignments,
            cls._provisional_amounts(assignments),
            cache=cache,
        )

        projection = BiddingRoundStatsService.build_financing_projection(
            bid_range_round, cache={}, include_auto_renewed=True
        )
        fixed_per_year = (
            projection["auto_renew_per_year"]
            + projection["delivery_charge_per_year"]
            + projection["membership_per_year"]
        )
        target_amount_per_year = cls._get_target_amount_per_year(
            organization=organization,
            assignments=assignments,
            fixed_per_year=fixed_per_year,
        )
        if target_amount_per_year != TARGET_AMOUNT_PER_YEAR:
            bid_range_round.target_amount_per_year = target_amount_per_year
            bid_range_round.save(update_fields=["target_amount_per_year"])

        bid_range_amounts = cls._calibrate_amounts(
            assignments,
            fixed_per_year,
            target_amount_per_year,
            BID_RANGE_TARGET_RATIOS,
        )
        simple_amounts = cls._calibrate_amounts(
            assignments,
            fixed_per_year,
            target_amount_per_year,
            SIMPLE_LEVEL_TARGET_RATIOS,
        )

        cls._save_bids(bid_range_round, assignments, bid_range_amounts, cache=cache)
        BiddingRoundService.close_round(bid_range_round, cache=cache)

        levels_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name=f"Beitragsrunde {year} - Stufen",
            start_at=start_at,
            end_at=end_at,
            product_type_id=product_type.id,
            target_amount_per_year=target_amount_per_year,
            prices=prices,
            bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE,
            bid_levels=3,
            include_auto_renewed=True,
            cache=cache,
        )
        BiddingRoundService.start_round(levels_round, cache=cache)
        cls._save_bids(levels_round, assignments, simple_amounts, cache=cache)
        BiddingRoundService.close_round(levels_round, cache=cache)

        bidding_round = BiddingRoundService.create_round(
            growing_period=growing_period,
            name=f"Beitragsrunde {year}",
            start_at=start_at,
            end_at=end_at,
            product_type_id=product_type.id,
            target_amount_per_year=target_amount_per_year,
            prices=prices,
            bidding_procedure=BIDDING_ROUND_PROCEDURE_SIMPLE,
            bid_levels=1,
            include_auto_renewed=True,
            cache=cache,
        )
        BiddingRoundService.start_round(bidding_round, cache=cache)
        cls._save_bids(bidding_round, assignments, simple_amounts, cache=cache)

        return bidding_round

    @classmethod
    def _get_size_or_one(cls, product, growing_period, cache) -> Decimal:
        size = ProductSizeService.get_size(product, growing_period, cache)
        return size if size is not None else Decimal("1")

    @classmethod
    def _is_automatic_renewal_enabled(cls, cache) -> bool:
        try:
            return bool(
                get_parameter_value(
                    ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=cache
                )
            )
        except KeyError:
            return False

    @classmethod
    def _get_target_amount_per_year(
        cls, organization, assignments, fixed_per_year
    ) -> Decimal:
        if organization is Organization.VIERLANDE:
            return VierlandeGenerator.get_bidding_round_target_amount_per_year()
        reference_per_year = sum(
            (
                REFERENCE_VALUE_PER_SIZE
                * assignment["size"]
                * assignment["quantity"]
                * Decimal("12")
                for assignment in assignments
            ),
            Decimal("0"),
        )
        return ((reference_per_year + fixed_per_year) / TARGET_COVERAGE_RATIO).quantize(
            Decimal("0.01")
        )

    @classmethod
    def _provisional_amounts(cls, assignments) -> list:
        amounts = []
        for assignment in assignments:
            amount = (
                REFERENCE_VALUE_PER_SIZE * assignment["size"] * assignment["factor"]
            ).quantize(Decimal("0.01"))
            amounts.append((amount, amount, amount))
        return amounts

    @classmethod
    def _calibrate_amounts(
        cls, assignments, fixed_per_year, target_amount_per_year, ratios
    ) -> list:
        weighted_shares = sum(
            (
                assignment["size"] * assignment["quantity"] * assignment["factor"]
                for assignment in assignments
            ),
            Decimal("0"),
        )
        if weighted_shares == 0:
            raise ValueError("Die Beitragsrunde braucht mindestens einen Anteil.")

        per_share_by_level = {
            level: (target_amount_per_year * ratio - fixed_per_year)
            / (weighted_shares * Decimal("12"))
            for level, ratio in ratios.items()
        }
        if any(amount <= 0 for amount in per_share_by_level.values()):
            return cls._fallback_amounts(assignments, ratios)

        return [
            tuple(
                (
                    per_share_by_level[level]
                    * assignment["size"]
                    * assignment["factor"]
                ).quantize(Decimal("0.01"))
                for level in ratios
            )
            for assignment in assignments
        ]

    @classmethod
    def _fallback_amounts(cls, assignments, ratios) -> list:
        """Use the reference value scaled by the target ratios when the target is
        too small for the fixed contributions (e.g. large demo data sets). The
        rounds then show plausible amounts instead of an exact coverage."""
        amounts = []
        for assignment in assignments:
            base = (
                REFERENCE_VALUE_PER_SIZE * assignment["size"] * assignment["factor"]
            ).quantize(Decimal("0.01"))
            amounts.append(
                tuple(
                    (base * ratio / TARGET_COVERAGE_RATIO).quantize(Decimal("0.01"))
                    for ratio in ratios.values()
                )
            )
        return amounts

    @classmethod
    def _save_bids(cls, bidding_round, assignments, amounts, cache):
        for assignment, level_amounts in zip(assignments, amounts):
            bid_input = BidInput(
                product_id=assignment["product"].id,
                quantity=assignment["quantity"],
                amount_1=(
                    level_amounts[1]
                    if bidding_round.bid_levels == 1 and len(level_amounts) > 1
                    else level_amounts[0]
                ),
            )
            if bidding_round.bid_levels > 1:
                bid_input = BidInput(
                    product_id=assignment["product"].id,
                    quantity=assignment["quantity"],
                    amount_1=level_amounts[0],
                    amount_2=level_amounts[1],
                    amount_3=(
                        level_amounts[2] if bidding_round.bid_levels > 2 else None
                    ),
                )
            BiddingRoundService.save_bid(
                assignment["member"],
                bidding_round,
                bid_input,
                cache=cache,
            )
