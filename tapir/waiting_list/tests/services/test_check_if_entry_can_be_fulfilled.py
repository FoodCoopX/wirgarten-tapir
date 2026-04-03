import datetime

from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.waiting_list.views import WaitingListApiView
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.models import (
    WaitingListProductWish,
    WaitingListPickupLocationWish,
    ProductCapacity,
)
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    PickupLocationFactory,
    GrowingPeriodFactory,
    ProductPriceFactory,
    ProductCapacityFactory,
    PickupLocationCapabilityFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCheckIfEntryCanBeFulfilled(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.product = ProductFactory.create(type__delivery_cycle=WEEKLY[0])
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
        mock_timezone(self, datetime.datetime(year=2025, month=1, day=15))

    def test_checkIfEntryCanBeFulfilled_noPickupLocationWishes_returnsFalse(self):
        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )

        result = WaitingListApiView.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_noProductWishes_returnsFalse(self):
        entry = WaitingListEntryFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry,
            pickup_location=self.pickup_location,
            priority=1,
        )

        result = WaitingListApiView.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_withWishesButInsufficientGlobalCapacity_returnsFalse(
        self,
    ):
        ProductCapacity.objects.filter(
            product_type=self.product.type, period=self.growing_period
        ).update(capacity=0)

        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry,
            pickup_location=self.pickup_location,
            priority=1,
        )

        result = WaitingListApiView.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_withWishesAndSufficientCapacity_returnsTrue(
        self,
    ):
        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry,
            pickup_location=self.pickup_location,
            priority=1,
        )

        result = WaitingListApiView.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertTrue(result)

    def test_checkIfEntryCanBeFulfilled_multiplePickupLocationWishesNoneWithCapacity_returnsFalse(
        self,
    ):
        from tapir.wirgarten.models import PickupLocationCapability

        PickupLocationCapability.objects.filter(
            pickup_location=self.pickup_location
        ).update(max_capacity=0)

        pickup_location_2 = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location_2,
            product_type=self.product.type,
            max_capacity=0,
        )

        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry,
            pickup_location=self.pickup_location,
            priority=1,
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry,
            pickup_location=pickup_location_2,
            priority=2,
        )

        result = WaitingListApiView.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertFalse(result)

    def test_checkIfEntryCanBeFulfilled_multiplePickupLocationWishesOneWithCapacity_returnsTrue(
        self,
    ):
        pickup_location_2 = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=pickup_location_2,
            product_type=self.product.type,
            max_capacity=0,
        )

        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=self.product, quantity=1
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry,
            pickup_location=pickup_location_2,
            priority=1,
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry,
            pickup_location=self.pickup_location,
            priority=2,
        )

        result = WaitingListApiView.check_if_entry_can_be_fulfilled(entry, cache={})

        self.assertTrue(result)
