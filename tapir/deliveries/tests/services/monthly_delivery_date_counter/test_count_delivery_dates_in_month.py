import datetime
from unittest.mock import patch, MagicMock, call

from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.deliveries.services.monthly_delivery_date_counter import (
    MonthlyDeliveryDateCounter,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.tests.factories import ProductTypeFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    MemberPickupLocationGetter,
    "get_member_pickup_location_id_from_cache",
    autospec=True,
    return_value="pl_id",
)
@patch.object(
    DeliveryDateCalculator, "get_next_delivery_date_for_product_type", autospec=True
)
class TestCountDeliveryDatesInMonth(TapirUnitTest):
    FIRST_OF_MONTH = datetime.date(year=2025, month=8, day=1)

    @classmethod
    def _deliver_every(
        cls, mock_get_next_delivery_date: MagicMock, interval_in_days: int
    ) -> None:
        def get_next_delivery_date(reference_date: datetime.date, **_) -> datetime.date:
            friday = reference_date + datetime.timedelta(days=5)
            while (friday - cls.FIRST_OF_MONTH).days % interval_in_days != 0:
                friday += datetime.timedelta(days=7)
            return friday

        mock_get_next_delivery_date.side_effect = get_next_delivery_date

    @classmethod
    def _count(
        cls,
        contract_start: datetime.date | None,
        contract_end: datetime.date | None,
        cache: dict | None = None,
    ) -> int:
        return MonthlyDeliveryDateCounter.count_delivery_dates_in_month(
            member_id="test_member_id",
            product_type=ProductTypeFactory.build(id="test_product_type_id"),
            first_of_month=cls.FIRST_OF_MONTH,
            contract_start=contract_start,
            contract_end=contract_end,
            cache={} if cache is None else cache,
        )

    def test_countDeliveryDatesInMonth_noContractRange_returnsAllDeliveriesOfMonth(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        self._deliver_every(
            mock_get_next_delivery_date=mock_get_next_delivery_date, interval_in_days=7
        )

        self.assertEqual(
            5,
            self._count(contract_start=None, contract_end=None),
            "There should be a delivery on each Friday of the month (1, 8, 15, 22, 29)",
        )

    def test_countDeliveryDatesInMonth_contractFullyIncludesMonth_returnsAllDeliveriesOfMonth(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        self._deliver_every(
            mock_get_next_delivery_date=mock_get_next_delivery_date, interval_in_days=7
        )

        self.assertEqual(
            5,
            self._count(
                contract_start=datetime.date(year=2025, month=1, day=1),
                contract_end=datetime.date(year=2025, month=12, day=31),
            ),
        )

    def test_countDeliveryDatesInMonth_contractStartsInMonth_returnsDeliveriesAfterStartOnly(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        self._deliver_every(
            mock_get_next_delivery_date=mock_get_next_delivery_date, interval_in_days=7
        )

        self.assertEqual(
            3,
            self._count(
                contract_start=datetime.date(year=2025, month=8, day=10),
                contract_end=datetime.date(year=2025, month=12, day=31),
            ),
            "There should be a delivery on the 15th, 22nd, 29th",
        )

    def test_countDeliveryDatesInMonth_contractEndsInMonth_returnsDeliveriesBeforeEndOnly(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        self._deliver_every(
            mock_get_next_delivery_date=mock_get_next_delivery_date, interval_in_days=7
        )

        self.assertEqual(
            4,
            self._count(
                contract_start=datetime.date(year=2025, month=1, day=1),
                contract_end=datetime.date(year=2025, month=8, day=23),
            ),
            "There should be a delivery on the 1st, 8th, 15th, 22nd",
        )

    def test_countDeliveryDatesInMonth_contractStartsAndEndsInMonth_returnsDeliveriesInsideContractOnly(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        self._deliver_every(
            mock_get_next_delivery_date=mock_get_next_delivery_date, interval_in_days=7
        )

        self.assertEqual(
            3,
            self._count(
                contract_start=datetime.date(year=2025, month=8, day=4),
                contract_end=datetime.date(year=2025, month=8, day=24),
            ),
            "There should be a delivery on the 8th, 15th, 22nd",
        )

    def test_countDeliveryDatesInMonth_differentCycles_countsDeliveriesOfCycle(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        for interval_in_days, expected in [(7, 5), (14, 3), (28, 2)]:
            with self.subTest(interval_in_days=interval_in_days):
                self._deliver_every(
                    mock_get_next_delivery_date=mock_get_next_delivery_date,
                    interval_in_days=interval_in_days,
                )

                self.assertEqual(
                    expected, self._count(contract_start=None, contract_end=None)
                )

    def test_countDeliveryDatesInMonth_noDeliveryInMonth_returnsZero(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        mock_get_next_delivery_date.return_value = None

        self.assertEqual(0, self._count(contract_start=None, contract_end=None))

    def test_countDeliveryDatesInMonth_nextDeliveryAfterMonth_returnsZero(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        mock_get_next_delivery_date.return_value = datetime.date(
            year=2025, month=9, day=5
        )

        self.assertEqual(0, self._count(contract_start=None, contract_end=None))

    def test_countDeliveryDatesInMonth_deliveryOfFirstWeekBeforeMonth_notCounted(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        mock_get_next_delivery_date.side_effect = (
            lambda reference_date, **__: reference_date + datetime.timedelta(days=1)
        )

        self.assertEqual(
            4,
            self._count(contract_start=None, contract_end=None),
            "There should be a delivery on the Mondays 4, 11, 18, 25 but not on 28.07.",
        )

    def test_countDeliveryDatesInMonth_pickupLocationChangesWithinMonth_usesLocationValidOnMondayOfEachWeek(
        self,
        mock_get_next_delivery_date: MagicMock,
        mock_get_member_pickup_location_id_from_cache: MagicMock,
    ):
        self._deliver_every(
            mock_get_next_delivery_date=mock_get_next_delivery_date, interval_in_days=7
        )
        mock_get_member_pickup_location_id_from_cache.side_effect = (
            lambda reference_date, **_: (
                "pl_id_1"
                if reference_date < datetime.date(year=2025, month=8, day=16)
                else "pl_id_2"
            )
        )
        cache = {}

        self._count(contract_start=None, contract_end=None, cache=cache)

        product_type = mock_get_next_delivery_date.call_args.kwargs["product_type"]
        mock_get_next_delivery_date.assert_has_calls(
            [
                call(
                    reference_date=reference_date,
                    pickup_location_id=pickup_location_id,
                    product_type=product_type,
                    check_for_weeks_without_delivery=False,
                    cache=cache,
                )
                for reference_date, pickup_location_id in [
                    (datetime.date(year=2025, month=7, day=27), "pl_id_1"),
                    (datetime.date(year=2025, month=8, day=3), "pl_id_1"),
                    (datetime.date(year=2025, month=8, day=10), "pl_id_1"),
                    (datetime.date(year=2025, month=8, day=17), "pl_id_2"),
                    (datetime.date(year=2025, month=8, day=24), "pl_id_2"),
                ]
            ]
        )
        mock_get_member_pickup_location_id_from_cache.assert_has_calls(
            [
                call(
                    member_id="test_member_id",
                    reference_date=reference_date,
                    cache=cache,
                )
                for reference_date in [
                    datetime.date(year=2025, month=7, day=28),
                    datetime.date(year=2025, month=8, day=4),
                    datetime.date(year=2025, month=8, day=11),
                    datetime.date(year=2025, month=8, day=18),
                    datetime.date(year=2025, month=8, day=25),
                ]
            ]
        )

    def test_countDeliveryDatesInMonth_calledTwiceWithSameCache_computesOnce(
        self,
        mock_get_next_delivery_date: MagicMock,
        _: MagicMock,
    ):
        self._deliver_every(
            mock_get_next_delivery_date=mock_get_next_delivery_date, interval_in_days=7
        )
        cache = {}

        self._count(contract_start=None, contract_end=None, cache=cache)
        call_count_after_first_count = mock_get_next_delivery_date.call_count
        result = self._count(contract_start=None, contract_end=None, cache=cache)

        self.assertEqual(5, result)
        self.assertEqual(
            call_count_after_first_count, mock_get_next_delivery_date.call_count
        )
