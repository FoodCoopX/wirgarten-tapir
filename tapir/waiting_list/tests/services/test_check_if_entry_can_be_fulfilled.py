import datetime

from tapir.waiting_list.services.can_be_fulfilled_checker import CanBeFulFilledChecker
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.constants import WEEKLY, NO_DELIVERY
from tapir.wirgarten.models import (
    WaitingListProductWish,
    WaitingListPickupLocationWish,
    ProductType,
    PickupLocationCapability,
    ProductCapacity,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    PickupLocationFactory,
    GrowingPeriodFactory,
    ProductPriceFactory,
    ProductCapacityFactory,
    PickupLocationCapabilityFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCheckIfEntryCanBeFulfilled(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

        cls.product = ProductFactory.create(
            type__delivery_cycle=WEEKLY[0], capacity=100
        )
        ProductPriceFactory.create(product=cls.product, size=1)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
        )
        ProductCapacityFactory.create(
            product_type=cls.product.type,
            period=cls.growing_period,
            capacity=100,
        )

        cls.pickup_location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=cls.pickup_location,
            product_type=cls.product.type,
            max_capacity=100,
        )

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime(year=2025, month=1, day=15))

    def test_checkIfEntryCanBeFulfilled_noWishes_returnsFalse(self):
        entry = WaitingListEntryFactory.create()

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_productWishesOnlyAndAllCapacitiesEnough_returnsTrue(
        self,
    ):
        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=self.pickup_location, priority=1
        )

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertTrue(result)

    def test_checkIfEntryCanBeFulfilled_orderNeedsDeliveryButNoLocationWish_returnsFalse(
        self,
    ):
        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_orderDoesntNeedsDeliveryAndNoLocationWish_returnsTrue(
        self,
    ):
        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )
        ProductType.objects.update(delivery_cycle=NO_DELIVERY[0])

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertTrue(result)

    def test_checkIfEntryCanBeFulfilled_currentPickupLocationDoesntHaveEnoughCapacity_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        entry = WaitingListEntryFactory.create(member=member)
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        PickupLocationCapability.objects.update(max_capacity=0)
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_productDoesntHaveEnoughCapacity_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        entry = WaitingListEntryFactory.create(member=member)
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        self.product.capacity = 0
        self.product.save()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_productTypeDoesntHaveEnoughCapacity_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        entry = WaitingListEntryFactory.create(member=member)
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        ProductCapacity.objects.update(capacity=0)
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_wishedPickupLocationDoesntHaveEnoughCapacity_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        entry = WaitingListEntryFactory.create(member=member)
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        PickupLocationCapability.objects.filter(
            pickup_location=self.pickup_location
        ).update(max_capacity=100)

        wished_pickup_location = PickupLocationFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=wished_pickup_location, priority=1
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=wished_pickup_location,
            max_capacity=0,
            product_type=self.product.type,
        )

        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_noWishedProductAndProductCapacitiesAreFullButWishedLocationHasEnoughCapacity_returnsTrue(
        self,
    ):
        member = MemberFactory.create()
        entry = WaitingListEntryFactory.create(member=member)
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        SubscriptionFactory.create(
            member=member, period=self.growing_period, product=self.product, quantity=1
        )
        wished_pickup_location = PickupLocationFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=wished_pickup_location, priority=1
        )
        self.product.capacity = 0
        self.product.save()
        PickupLocationCapabilityFactory.create(
            pickup_location=wished_pickup_location,
            max_capacity=100,
            product_type=self.product.type,
        )

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertTrue(result)

    def test_checkIfEntryCanBeFulfilled_noWishedProductButWishedLocationDoesntEnoughCapacityForCurrentSubscriptions_returnsFalse(
        self,
    ):
        member = MemberFactory.create()
        entry = WaitingListEntryFactory.create(member=member)
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location,
            valid_from=self.growing_period.start_date,
        )
        wished_pickup_location = PickupLocationFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=wished_pickup_location, priority=1
        )
        SubscriptionFactory.create(
            member=member, period=self.growing_period, product=self.product, quantity=2
        )
        PickupLocationCapabilityFactory.create(
            pickup_location=wished_pickup_location,
            max_capacity=1,
            product_type=self.product.type,
        )

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_noGrowingPeriodCoveringToday_stillReturnsTrue(
        self,
    ):
        # Regression test for #1150 https://github.com/FoodCoopX/wirgarten-tapir/issues/1150
        mock_timezone(self, datetime.datetime(year=2024, month=12, day=15))

        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry,
            pickup_location=self.pickup_location,
            priority=1,
        )

        result = CanBeFulFilledChecker.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertTrue(result)
