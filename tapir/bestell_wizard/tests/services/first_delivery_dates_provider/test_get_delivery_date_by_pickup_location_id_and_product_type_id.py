import datetime

from tapir.bestell_wizard.services.first_delivery_dates_provider import (
    FirstDeliveryDatesProvider,
)
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    GrowingPeriodFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetDeliveryDateByPickupLocationIdAndProductTypeId(TapirIntegrationTest):
    maxDiff = 2000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

        cls.product_weekly = ProductFactory.create(type__delivery_cycle=WEEKLY[0])
        cls.product_even_weeks = ProductFactory.create(
            type__delivery_cycle=EVEN_WEEKS[0]
        )

        GrowingPeriodFactory.create(start_date=datetime.date(year=2024, month=1, day=1))
        GrowingPeriodFactory.create(start_date=datetime.date(year=2025, month=1, day=1))

        cls.pickup_location_1 = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=cls.pickup_location_1,
            day_of_week=3,
            open_time=datetime.time(8, 0),
            close_time=datetime.time(9, 0),
        )  # delivery on Thursday

        cls.pickup_location_2 = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=cls.pickup_location_2,
            day_of_week=4,
            open_time=datetime.time(8, 0),
            close_time=datetime.time(9, 0),
        )  # delivery on Friday

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, now=datetime.datetime(year=2024, month=6, day=8))

    def test_getDeliveryDate_contractStartInCurrentPeriod_returnsFirstDeliveriesAfterContractStart(
        self,
    ):
        result = self._get_delivery_dates(
            contract_start_date=datetime.date(year=2024, month=7, day=1)
        )

        self.assertEqual(
            {
                self.pickup_location_1.id: {
                    self.product_weekly.type.id: datetime.date(2024, 7, 4),
                    self.product_even_weeks.type.id: datetime.date(2024, 7, 11),
                },
                self.pickup_location_2.id: {
                    self.product_weekly.type.id: datetime.date(2024, 7, 5),
                    self.product_even_weeks.type.id: datetime.date(2024, 7, 12),
                },
            },
            result,
        )

    def test_getDeliveryDate_contractStartInNextPeriod_returnsFirstDeliveriesAfterContractStart(
        self,
    ):
        result = self._get_delivery_dates(
            contract_start_date=datetime.date(year=2025, month=1, day=6)
        )

        self.assertEqual(
            {
                self.pickup_location_1.id: {
                    self.product_weekly.type.id: datetime.date(2025, 1, 9),
                    self.product_even_weeks.type.id: datetime.date(2025, 1, 9),
                },
                self.pickup_location_2.id: {
                    self.product_weekly.type.id: datetime.date(2025, 1, 10),
                    self.product_even_weeks.type.id: datetime.date(2025, 1, 10),
                },
            },
            result,
        )

    def test_getDeliveryDate_pickupLocationWithFutureStartDate_excluded(self):
        PickupLocationFactory.create(
            start_date=datetime.date(year=2024, month=8, day=5)
        )

        result = self._get_delivery_dates(
            contract_start_date=datetime.date(year=2024, month=7, day=1)
        )

        self.assertEqual(
            {self.pickup_location_1.id, self.pickup_location_2.id}, set(result.keys())
        )

    def test_getDeliveryDate_pickupLocationWithPastEndDate_excluded(self):
        PickupLocationFactory.create(end_date=datetime.date(year=2024, month=6, day=30))

        result = self._get_delivery_dates(
            contract_start_date=datetime.date(year=2024, month=7, day=1)
        )

        self.assertEqual(
            {self.pickup_location_1.id, self.pickup_location_2.id}, set(result.keys())
        )

    def _get_delivery_dates(
        self, contract_start_date: datetime.date
    ) -> dict[str, dict[str, datetime.date]]:
        return FirstDeliveryDatesProvider.get_delivery_date_by_pickup_location_id_and_product_type_id(
            order={self.product_weekly: 1, self.product_even_weeks: 2},
            contract_start_date=contract_start_date,
            cache={},
        )
