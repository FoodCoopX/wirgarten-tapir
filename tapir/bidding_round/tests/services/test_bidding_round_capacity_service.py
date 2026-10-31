import datetime
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from tapir.bidding_round.models import BiddingRoundCreatedSubscription
from tapir.bidding_round.services.bidding_round_capacity_service import (
    BiddingRoundCapacityService,
)
from tapir.bidding_round.tests.factories import BidFactory, BidItemFactory
from tapir.bidding_round.tests.helpers import (
    build_item,
    create_open_round,
    create_round_product_with_product,
)
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationCapabilityFactory,
    PickupLocationFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBiddingRoundCapacityService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _build_setup(self, capacity, quantity, max_pickup_capacity=None):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(
            round_, capacity=capacity
        )
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=round_.growing_period.start_date,
        )
        pickup_location = None
        if max_pickup_capacity is not None:
            round_product.product_type.delivery_cycle = WEEKLY[0]
            round_product.product_type.save()
            pickup_location = PickupLocationFactory.create()
            PickupLocationCapabilityFactory.create(
                pickup_location=pickup_location,
                product_type=round_product.product_type,
                max_capacity=max_pickup_capacity,
            )
        return round_, round_product, product, pickup_location, quantity

    def test_getInsufficientCapacityReasons_enoughCapacity_returnsEmpty(self):
        round_, round_product, product, _, quantity = self._build_setup(
            capacity=100, quantity=1
        )

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=round_,
            items=[build_item(round_product, product, quantity=quantity)],
            pickup_location_id=None,
            member=None,
            cache={},
            subscription_start_date=round_.growing_period.start_date,
        )

        self.assertEqual([], reasons)

    def test_getInsufficientCapacityReasons_globalCapacityExceeded_returnsProductTypeReason(
        self,
    ):
        round_, round_product, product, _, quantity = self._build_setup(
            capacity=1, quantity=2
        )

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=round_,
            items=[build_item(round_product, product, quantity=quantity)],
            pickup_location_id=None,
            member=None,
            cache={},
            subscription_start_date=round_.growing_period.start_date,
        )

        self.assertEqual(1, len(reasons))
        self.assertEqual("product_type", reasons[0]["type"])
        self.assertEqual(round_product.product_type.name, reasons[0]["name"])

    def test_getInsufficientCapacityReasons_pickupLocationFull_returnsPickupLocationReason(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        (
            round_,
            round_product,
            product,
            pickup_location,
            quantity,
        ) = self._build_setup(capacity=100, quantity=2, max_pickup_capacity=1)

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=round_,
            items=[build_item(round_product, product, quantity=quantity)],
            pickup_location_id=pickup_location.id,
            member=None,
            cache={},
            subscription_start_date=round_.growing_period.start_date,
        )

        self.assertEqual(1, len(reasons))
        self.assertEqual("pickup_location", reasons[0]["type"])
        self.assertEqual(pickup_location.name, reasons[0]["name"])

    def _create_bid(self, round_, round_product, product, member, pickup_location=None):
        bid = BidFactory.create(
            round=round_,
            member=member,
            pickup_location=pickup_location,
        )
        BidItemFactory.create(
            bid=bid, round_product=round_product, product=product, quantity=1
        )
        return bid

    def test_getInsufficientCapacityReasons_otherMembersBidCountsGlobally_returnsProductTypeReason(
        self,
    ):
        round_, round_product, product, _, _ = self._build_setup(capacity=1, quantity=1)
        self._create_bid(round_, round_product, product, MemberFactory.create())

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=round_,
            items=[build_item(round_product, product, quantity=1)],
            pickup_location_id=None,
            member=None,
            cache={},
            subscription_start_date=round_.growing_period.start_date,
        )

        self.assertEqual(1, len(reasons))
        self.assertEqual("product_type", reasons[0]["type"])

    def test_getInsufficientCapacityReasons_otherMembersBidCountsAtPickupLocation_returnsPickupLocationReason(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")
        (
            round_,
            round_product,
            product,
            pickup_location,
            _,
        ) = self._build_setup(capacity=100, quantity=1, max_pickup_capacity=1)
        self._create_bid(
            round_,
            round_product,
            product,
            MemberFactory.create(),
            pickup_location=pickup_location,
        )

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=round_,
            items=[build_item(round_product, product, quantity=1)],
            pickup_location_id=pickup_location.id,
            member=None,
            cache={},
            subscription_start_date=round_.growing_period.start_date,
        )

        self.assertEqual(1, len(reasons))
        self.assertEqual("pickup_location", reasons[0]["type"])

    def test_getInsufficientCapacityReasons_bidReplacingRenewalNotCountedTwice_allowsOrder(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value="true")
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_, capacity=2)
        previous_period = GrowingPeriodFactory.create(
            start_date=round_.growing_period.start_date - relativedelta(years=1),
            end_date=round_.growing_period.start_date - datetime.timedelta(days=1),
        )
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=previous_period.start_date,
        )
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=previous_period,
            product=product,
            quantity=1,
            start_date=previous_period.start_date,
            end_date=previous_period.end_date,
        )
        self._create_bid(round_, round_product, product, member)

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=round_,
            items=[build_item(round_product, product, quantity=1)],
            pickup_location_id=None,
            member=None,
            cache={},
            subscription_start_date=round_.growing_period.start_date,
        )

        self.assertEqual([], reasons)

    def _enable_pickup_location_change(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BIDDING_ROUND_PICKUP_LOCATION_CHANGE_ENABLED
        ).update(value="true")

    def test_getInsufficientCapacityReasons_ownFullPickupLocation_allowsOrder(self):
        self._enable_pickup_location_change()
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value="true")
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_, capacity=2)
        round_product.product_type.delivery_cycle = WEEKLY[0]
        round_product.product_type.save()
        pickup_location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location,
            product_type=round_product.product_type,
            max_capacity=1,
        )
        previous_period = GrowingPeriodFactory.create(
            start_date=round_.growing_period.start_date - relativedelta(years=1),
            end_date=round_.growing_period.start_date - datetime.timedelta(days=1),
        )
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=previous_period.start_date,
        )
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=previous_period,
            product=product,
            quantity=1,
            start_date=previous_period.start_date,
            end_date=previous_period.end_date,
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=previous_period.start_date,
        )

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=round_,
            items=[build_item(round_product, product, quantity=1)],
            pickup_location_id=pickup_location.id,
            member=member,
            cache={},
            subscription_start_date=round_.growing_period.start_date,
        )

        self.assertEqual([], reasons)

    def test_getInsufficientCapacityReasons_otherFullPickupLocation_rejects(self):
        self._enable_pickup_location_change()
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_, capacity=100)
        round_product.product_type.delivery_cycle = WEEKLY[0]
        round_product.product_type.save()
        own_location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=own_location,
            product_type=round_product.product_type,
            max_capacity=10,
        )
        other_location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=other_location,
            product_type=round_product.product_type,
            max_capacity=1,
        )
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=round_.growing_period.start_date,
        )
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=own_location,
            valid_from=round_.growing_period.start_date,
        )
        self._create_bid(
            round_,
            round_product,
            product,
            MemberFactory.create(),
            pickup_location=other_location,
        )

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=round_,
            items=[build_item(round_product, product, quantity=1)],
            pickup_location_id=other_location.id,
            member=member,
            cache={},
            subscription_start_date=round_.growing_period.start_date,
        )

        self.assertEqual(1, len(reasons))
        self.assertEqual("pickup_location", reasons[0]["type"])

    def test_getInsufficientCapacityReasons_materializedBidNotCountedTwice_allowsOrder(
        self,
    ):
        round_ = create_open_round()
        round_product, product = create_round_product_with_product(round_, capacity=2)
        ProductPriceFactory.create(
            product=product,
            price=Decimal("50.00"),
            size=1,
            valid_from=round_.growing_period.start_date,
        )
        member = MemberFactory.create()
        self._create_bid(round_, round_product, product, member)
        subscription = SubscriptionFactory.create(
            member=member,
            product=product,
            period=round_.growing_period,
            quantity=1,
            start_date=round_.growing_period.start_date,
            end_date=round_.growing_period.end_date,
        )
        BiddingRoundCreatedSubscription.objects.create(
            round=round_, subscription=subscription
        )

        reasons = BiddingRoundCapacityService.get_insufficient_capacity_reasons(
            bidding_round=round_,
            items=[build_item(round_product, product, quantity=1)],
            pickup_location_id=None,
            member=None,
            cache={},
            subscription_start_date=round_.growing_period.start_date,
        )

        self.assertEqual([], reasons)
