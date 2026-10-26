import datetime
import math
import random
from decimal import Decimal

from tapir.bidding_round.config import SIMPLE, TRAFFIC_LIGHT
from tapir.bidding_round.models import (
    Bid,
    BidItem,
    BiddingRoundProduct,
    BiddingRoundProductPrice,
)
from tapir.bidding_round.services.bidding_round_service import BiddingRoundService
from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.models import (
    GrowingPeriod,
    PickupLocation,
    Product,
    ProductCapacity,
    ProductType,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
    get_product_price,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.utils import get_now, get_today

HARVEST_SHARE_PRODUCT_TYPE_NAME = "Ernteanteile"

REFERENCE_VALUE = Decimal("80.00")
MIN_AMOUNT = Decimal("60.00")
TARGET_AMOUNT_PER_YEAR = Decimal("220800.00")
GREEN_TARGET_RATIO = Decimal("0.81")
YELLOW_TARGET_RATIO = Decimal("0.91")
RED_TARGET_RATIO = Decimal("1.09")
SHARES_TARGET_RATIO = Decimal("0.90")
AUTO_RENEW_SHARES_RATIO = Decimal("0.20")


class BiddingRoundGenerator:
    @classmethod
    def generate_bidding_round(cls, cache=None):
        cache = cache or {}

        TapirParameter.objects.filter(key=ParameterKeys.BIDDING_ROUND_ENABLED).update(
            value="true"
        )
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_URL_ENABLED
        ).update(value="true")
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")

        today = get_today(cache=cache)
        now = get_now(cache=cache)
        next_period = (
            GrowingPeriod.objects.filter(start_date__gt=today)
            .order_by("start_date")
            .first()
        )
        if next_period is None:
            next_period = GrowingPeriod.objects.order_by("start_date").last()

        harvest_share_product_type = ProductType.objects.filter(
            name=HARVEST_SHARE_PRODUCT_TYPE_NAME
        ).first()
        if harvest_share_product_type is None:
            return None

        capacities = list(
            ProductCapacity.objects.filter(
                period=next_period, product_type=harvest_share_product_type
            )
        )
        if not capacities:
            return None

        end_at = now + datetime.timedelta(days=30)
        year = next_period.start_date.year

        # Three demo rounds for the same season, all sharing the same bidders and
        # calibration (so only one may be active):
        #  - "Ampel": traffic light round, evaluated (closed) after the fact.
        #  - "einfach": the active public round with a single bid.
        #  - "einfach - 3 Gebote": simple round with three bid levels.
        traffic_light_round = BiddingRoundService.create_round(
            growing_period=next_period,
            name=f"Beitragsrunde {year} - Ampel",
            bidding_procedure=TRAFFIC_LIGHT,
            end_at=end_at,
            start_at=now,
            product_type_id=harvest_share_product_type.id,
            cache=cache,
        )
        simple_round = BiddingRoundService.create_round(
            growing_period=next_period,
            name=f"Beitragsrunde {year} - einfach",
            bidding_procedure=SIMPLE,
            end_at=end_at,
            start_at=now,
            product_type_id=harvest_share_product_type.id,
            bid_levels=1,
            cache=cache,
        )
        simple_levels_round = BiddingRoundService.create_round(
            growing_period=next_period,
            name=f"Beitragsrunde {year} - einfach - 3 Gebote",
            bidding_procedure=SIMPLE,
            end_at=end_at,
            start_at=now,
            product_type_id=harvest_share_product_type.id,
            bid_levels=3,
            cache=cache,
        )

        products = list(
            Product.objects.filter(type=harvest_share_product_type, deleted=False)
        )
        for bidding_round in (
            traffic_light_round,
            simple_round,
            simple_levels_round,
        ):
            round_product = BiddingRoundProduct.objects.get(round=bidding_round)
            round_product.target_amount_per_year = TARGET_AMOUNT_PER_YEAR
            round_product.save()
            for product in products:
                BiddingRoundProductPrice.objects.update_or_create(
                    round_product=round_product,
                    product=product,
                    defaults={
                        "reference_value": REFERENCE_VALUE,
                        "min_amount": MIN_AMOUNT,
                    },
                )

        active_subscriptions = get_active_subscriptions(cache=cache).filter(
            product__type=harvest_share_product_type
        )
        existing_members = sorted(
            {subscription.member for subscription in active_subscriptions},
            key=lambda member: member.id,
        )

        number_of_existing_members = len(existing_members)
        number_of_bidders = int(math.floor(number_of_existing_members * 0.6))
        bidders = existing_members[:number_of_bidders]

        renewal_subscriptions = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=next_period.start_date, cache={}
            )
        )
        shares_by_member_id = {}
        for subscription in renewal_subscriptions:
            if subscription.product.type_id != harvest_share_product_type.id:
                continue
            shares_by_member_id[subscription.member_id] = (
                shares_by_member_id.get(subscription.member_id, Decimal("0"))
                + subscription.quantity
            )

        auto_renew_share_budget = Decimal(capacities[0].capacity or 0) * (
            AUTO_RENEW_SHARES_RATIO
        )
        auto_renew_shares = Decimal("0")
        auto_renew_members = []
        cancelled_members = []
        for member in existing_members[number_of_bidders:]:
            member_shares = shares_by_member_id.get(member.id, Decimal("0"))
            if (
                not auto_renew_members
                or auto_renew_shares + member_shares <= auto_renew_share_budget
            ):
                auto_renew_members.append(member)
                auto_renew_shares += member_shares
            else:
                cancelled_members.append(member)

        for member in cancelled_members:
            Subscription.objects.filter(
                member=member, cancellation_ts__isnull=True
            ).update(cancellation_ts=now)

        # New members join via the order wizard, not via the round; they only make
        # the member list more realistic.
        number_of_new_members = int(round(number_of_existing_members * 0.1))
        for _ in range(number_of_new_members):
            MemberFactory.create()

        pickup_locations = list(PickupLocation.objects.all())
        pickup_location_by_index = (
            {
                index: pickup_locations[index % len(pickup_locations)]
                for index in range(len(bidders))
            }
            if pickup_locations
            else {}
        )

        # Calibrate the per-share amounts so that the total reaches 81/91/109 % of
        # the season target for green/yellow/red.
        number_of_shares = max(len(bidders), 1)
        green_per_share = (TARGET_AMOUNT_PER_YEAR * GREEN_TARGET_RATIO) / (
            Decimal(number_of_shares) * 12
        )
        yellow_per_share = (TARGET_AMOUNT_PER_YEAR * YELLOW_TARGET_RATIO) / (
            Decimal(number_of_shares) * 12
        )
        red_per_share = (TARGET_AMOUNT_PER_YEAR * RED_TARGET_RATIO) / (
            Decimal(number_of_shares) * 12
        )

        bid_rows = []
        for index, member in enumerate(bidders):
            factor = Decimal(str(round(random.uniform(0.85, 1.15), 3)))
            bid_rows.append(
                {
                    "member": member,
                    "product": products[index % len(products)] if products else None,
                    "green": (green_per_share * factor).quantize(Decimal("0.01")),
                    "yellow": (yellow_per_share * factor).quantize(Decimal("0.01")),
                    "red": (red_per_share * factor).quantize(Decimal("0.01")),
                    "pickup_location": pickup_location_by_index.get(index),
                }
            )

        cls._create_bids(
            traffic_light_round, bid_rows, level_keys=["green", "yellow", "red"]
        )
        cls._create_bids(
            simple_levels_round, bid_rows, level_keys=["green", "yellow", "red"]
        )
        cls._create_bids(simple_round, bid_rows, level_keys=["yellow"])

        BiddingRoundService.start_round(traffic_light_round, cache=cache)
        BiddingRoundService.close_round(traffic_light_round, cache=cache)
        BiddingRoundService.start_round(simple_levels_round, cache=cache)
        BiddingRoundService.close_round(simple_levels_round, cache=cache)
        BiddingRoundService.start_round(simple_round, cache=cache)

        return simple_round

    @staticmethod
    def _create_bids(bidding_round, bid_rows, level_keys):
        for row in bid_rows:
            if row["product"] is None:
                continue
            round_product = BiddingRoundProduct.objects.get(round=bidding_round)
            bid = Bid.objects.create(
                round=bidding_round,
                member=row["member"],
                pickup_location=row["pickup_location"],
            )
            amounts = [row[key] for key in level_keys]
            BidItem.objects.create(
                bid=bid,
                round_product=round_product,
                product=row["product"],
                quantity=1,
                amount_1=amounts[0] if len(amounts) > 0 else None,
                amount_2=amounts[1] if len(amounts) > 1 else None,
                amount_3=amounts[2] if len(amounts) > 2 else None,
            )
