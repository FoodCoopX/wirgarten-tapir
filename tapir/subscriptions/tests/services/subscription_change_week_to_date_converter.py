import datetime
from unittest.mock import Mock

from django.core.exceptions import ImproperlyConfigured
from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions.services.subscription_change_week_to_date_converter import (
    SubscriptionChangeWeekToDateConverter,
)


class TestGetDateFromCalendarWeek(TapirUnitTest):
    @staticmethod
    def create_growing_period(start_date, end_date):
        growing_period = Mock()
        growing_period.start_date = start_date
        growing_period.end_date = end_date
        return growing_period

    def test_getDateFromCalendarWeek_givenWeekIsWithinGrowingPeriodAndBoundaryIsStart_returnsCorrectMonday(
        self,
    ):
        growing_period = self.create_growing_period(
            datetime.date(year=2026, month=1, day=1),
            datetime.date(year=2026, month=12, day=31),
        )
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=10, growing_period=growing_period, boundary="start"
        )
        self.assertEqual(result, datetime.date(year=2026, month=3, day=2))

    def test_getDateFromCalendarWeek_givenWeekOverlapsTheGrowingPeriodStartAndBoundaryIsStart_returnsFirstDayOfGrowingPeriod(
        self,
    ):
        growing_period = self.create_growing_period(
            datetime.date(year=2026, month=1, day=1),
            datetime.date(year=2026, month=12, day=31),
        )
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=1, growing_period=growing_period, boundary="start"
        )
        self.assertEqual(result, datetime.date(year=2026, month=1, day=1))

    def test_getDateFromCalendarWeek_givenWeekIsWithinGrowingPeriodAndBoundaryIsEnd_returnsCorrectSunday(
        self,
    ):
        growing_period = self.create_growing_period(
            datetime.date(year=2026, month=1, day=1),
            datetime.date(year=2026, month=12, day=31),
        )
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=10, growing_period=growing_period, boundary="end"
        )
        self.assertEqual(result, datetime.date(year=2026, month=3, day=8))

    def test_getDateFromCalendarWeek_givenWeekOverlapsTheGrowingPeriodEndAndBoundaryIsEnd_returnsLastDayOfGrowingPeriod(
        self,
    ):
        growing_period = self.create_growing_period(
            datetime.date(year=2026, month=1, day=1),
            datetime.date(year=2026, month=12, day=31),
        )
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=53, growing_period=growing_period, boundary="end"
        )
        self.assertEqual(result, datetime.date(year=2026, month=12, day=31))

    def test_getDateFromCalendarWeek_givenWeekIsWithinGrowingPeriodButInFollowingYear_returnsDateOnNextYear(
        self,
    ):
        # Growing period starts in November 2026, week 2 is in January, so the result should be in January 2027
        growing_period = self.create_growing_period(
            datetime.date(year=2026, month=11, day=1),
            datetime.date(year=2027, month=10, day=31),
        )
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=2, growing_period=growing_period, boundary="start"
        )
        expected = datetime.date.fromisocalendar(year=2027, week=2, day=1)
        self.assertEqual(result, expected)

    def test_getDateFromCalendarWeek_invalidBoundary_raisesImproperlyConfigured(self):
        growing_period = self.create_growing_period(
            datetime.date(year=2026, month=1, day=1),
            datetime.date(year=2026, month=12, day=31),
        )
        with self.assertRaises(ImproperlyConfigured):
            SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
                week=10, growing_period=growing_period, boundary="invalid"
            )
