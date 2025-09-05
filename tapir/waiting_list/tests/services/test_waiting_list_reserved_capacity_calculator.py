from tapir.waiting_list.services.waiting_list_reserved_capacity_calculator import (
    WaitingListReservedCapacityCalculator,
)
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.models import WaitingListPickupLocationWish, WaitingListProductWish
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    PickupLocationFactory,
    ProductPriceFactory,
    TODAY,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestWaitingListReservedCapacityCalculator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        cls.product_a = ProductFactory.create()
        cls.product_b = ProductFactory.create()
        cls.pickup_location_a = PickupLocationFactory.create()
        cls.pickup_location_b = PickupLocationFactory.create()
        ProductPriceFactory.create(product=cls.product_a, size=1.25)
        ProductPriceFactory.create(product=cls.product_b, size=2.33)

        entry = WaitingListEntryFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=cls.pickup_location_a, priority=1
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=cls.pickup_location_b, priority=2
        )
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=cls.product_a, quantity=1
        )

        entry = WaitingListEntryFactory.create()
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=cls.product_a, quantity=2
        )

        entry = WaitingListEntryFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=cls.pickup_location_a, priority=1
        )
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=cls.product_a, quantity=3
        )

        entry = WaitingListEntryFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=cls.pickup_location_b, priority=1
        )
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=cls.product_a, quantity=4
        )

        entry = WaitingListEntryFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry, pickup_location=cls.pickup_location_a, priority=1
        )
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=cls.product_b, quantity=5
        )

    def test_calculateCapacityReservedByTheWaitingListEntries_filterByProductTypeOnly_returnsCorrectValue(
        self,
    ):
        result = WaitingListReservedCapacityCalculator.calculate_capacity_reserved_by_the_waiting_list_entries(
            product_type=self.product_a.type,
            pickup_location=None,
            reference_date=TODAY,
            cache={},
        )

        self.assertEqual(
            (1 + 2 + 3 + 4) * 1.25,
            result,
            "The capacity reserved should be the sum of all entries with a wish for product A",
        )

    def test_calculateCapacityReservedByTheWaitingListEntries_filterByProductTypeAndPickupLocation_returnsCorrectValue(
        self,
    ):
        result = WaitingListReservedCapacityCalculator.calculate_capacity_reserved_by_the_waiting_list_entries(
            product_type=self.product_a.type,
            pickup_location=self.pickup_location_a,
            reference_date=TODAY,
            cache={},
        )

        self.assertEqual(
            (1 + 3) * 1.25,
            result,
            "The capacity reserved should be the sum of all entries with a wish for product A and a wish for pickup location A",
        )
