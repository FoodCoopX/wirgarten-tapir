import datetime
from unittest.mock import patch, MagicMock

from tapir.deliveries.services.monthly_delivery_date_counter import (
    MonthlyDeliveryDateCounter,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    MemberPickupLocationGetter,
    "get_member_pickup_location_id_from_cache",
    autospec=True,
)
class TestGetWeeksOfMonthWithPickupLocation(TapirUnitTest):
    # January 2027 starts on a Friday: its weeks start on 28.12.2026, 4., 11., 18. and 25.01.
    FIRST_OF_MONTH = datetime.date(year=2027, month=1, day=1)
    MONDAYS = [
        datetime.date(year=2026, month=12, day=28),
        datetime.date(year=2027, month=1, day=4),
        datetime.date(year=2027, month=1, day=11),
        datetime.date(year=2027, month=1, day=18),
        datetime.date(year=2027, month=1, day=25),
    ]

    @classmethod
    def _get_weeks(
        cls,
        mock_get_member_pickup_location_id_from_cache: MagicMock,
        ids_by_week: list[str | None],
    ) -> list[tuple[datetime.date, str | None]]:
        ids_by_monday = dict(zip(cls.MONDAYS, ids_by_week))
        mock_get_member_pickup_location_id_from_cache.side_effect = (
            lambda reference_date, **_: ids_by_monday[reference_date]
        )
        return MonthlyDeliveryDateCounter._get_weeks_of_month_with_pickup_location(
            member_id="test_member_id", first_of_month=cls.FIRST_OF_MONTH, cache={}
        )

    def _assert_weeks(
        self,
        expected_ids: list[str | None],
        weeks: list[tuple[datetime.date, str | None]],
    ) -> None:
        self.assertEqual(list(zip(self.MONDAYS, expected_ids)), weeks)

    def test_getWeeksOfMonthWithPickupLocation_locationKnownInEveryWeek_returnsEachMondayWithItsLocation(
        self, mock_get_member_pickup_location_id_from_cache: MagicMock
    ):
        ids_by_week = ["pl_1", "pl_1", "pl_2", "pl_2", "pl_2"]

        self._assert_weeks(
            expected_ids=ids_by_week,
            weeks=self._get_weeks(
                mock_get_member_pickup_location_id_from_cache=mock_get_member_pickup_location_id_from_cache,
                ids_by_week=ids_by_week,
            ),
        )

    def test_getWeeksOfMonthWithPickupLocation_noLocationInFirstWeeks_firstWeeksTakeFirstKnownLocation(
        self, mock_get_member_pickup_location_id_from_cache: MagicMock
    ):
        self._assert_weeks(
            expected_ids=["pl_1", "pl_1", "pl_1", "pl_1", "pl_2"],
            weeks=self._get_weeks(
                mock_get_member_pickup_location_id_from_cache=mock_get_member_pickup_location_id_from_cache,
                ids_by_week=[None, None, "pl_1", "pl_1", "pl_2"],
            ),
        )

    def test_getWeeksOfMonthWithPickupLocation_noLocationInLaterWeeks_laterWeeksTakePreviousLocation(
        self, mock_get_member_pickup_location_id_from_cache: MagicMock
    ):
        self._assert_weeks(
            expected_ids=["pl_1", "pl_1", "pl_2", "pl_2", "pl_2"],
            weeks=self._get_weeks(
                mock_get_member_pickup_location_id_from_cache=mock_get_member_pickup_location_id_from_cache,
                ids_by_week=["pl_1", None, "pl_2", None, None],
            ),
        )

    def test_getWeeksOfMonthWithPickupLocation_noLocationInAnyWeek_returnsNoneForEachWeek(
        self, mock_get_member_pickup_location_id_from_cache: MagicMock
    ):
        self._assert_weeks(
            expected_ids=[None] * 5,
            weeks=self._get_weeks(
                mock_get_member_pickup_location_id_from_cache=mock_get_member_pickup_location_id_from_cache,
                ids_by_week=[None] * 5,
            ),
        )

    def test_getWeeksOfMonthWithPickupLocation_default_looksUpLocationOnEachMonday(
        self, mock_get_member_pickup_location_id_from_cache: MagicMock
    ):
        mock_get_member_pickup_location_id_from_cache.return_value = "pl_1"
        cache = {}

        MonthlyDeliveryDateCounter._get_weeks_of_month_with_pickup_location(
            member_id="test_member_id", first_of_month=self.FIRST_OF_MONTH, cache=cache
        )

        self.assertEqual(
            [
                {
                    "member_id": "test_member_id",
                    "reference_date": monday,
                    "cache": cache,
                }
                for monday in self.MONDAYS
            ],
            [
                call.kwargs
                for call in mock_get_member_pickup_location_id_from_cache.call_args_list
            ],
        )
