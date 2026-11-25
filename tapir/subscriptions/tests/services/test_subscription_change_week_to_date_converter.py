import datetime
from django.core.exceptions import ValidationError

from tapir.subscriptions.services.subscription_change_week_to_date_converter import (
    SubscriptionChangeWeekToDateConverter,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetDateFromCalendarWeek(TapirUnitTest):
    def test_getDateFromCalendarWeek_boundaryIsStart_returnsMondayOfWeek(self):
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=10,
            growing_period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2026, month=1, day=1)
            ),
            boundary="start",
        )
        self.assertEqual(datetime.date(year=2026, month=3, day=2), result)

    def test_getDateFromCalendarWeek_boundaryIsEnd_returnsSundayOfWeek(self):
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=10,
            growing_period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2026, month=1, day=1)
            ),
            boundary="end",
        )
        self.assertEqual(datetime.date(year=2026, month=3, day=8), result)

    def test_getDateFromCalendarWeek_weekIsInFollowingYearOfGrowingPeriod_returnsDateInFollowingYear(
        self,
    ):
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2026, month=11, day=1)
        )
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=2, growing_period=growing_period, boundary="start"
        )
        self.assertEqual(datetime.date(year=2027, month=1, day=11), result)

    def test_getDateFromCalendarWeek_mondayOfWeekIsBeforeGrowingPeriod_raisesValidationError(
        self,
    ):
        with self.assertRaisesMessage(
            ValidationError, "Der Montag der KW 1 liegt nicht in der Vertragsperiode"
        ):
            SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
                week=1,
                growing_period=GrowingPeriodFactory.build(
                    start_date=datetime.date(year=2026, month=1, day=1)
                ),
                boundary="start",
            )

    def test_getDateFromCalendarWeek_sundayOfWeekIsAfterGrowingPeriod_raisesValidationError(
        self,
    ):
        with self.assertRaisesMessage(
            ValidationError, "Der Sonntag der KW 53 liegt nicht in der Vertragsperiode"
        ):
            SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
                week=53,
                growing_period=GrowingPeriodFactory.build(
                    start_date=datetime.date(year=2026, month=1, day=1)
                ),
                boundary="end",
            )

    def test_getDateFromCalendarWeek_weekMatchesTwiceInGrowingPeriodAndBoundaryIsStart_returnsFirstMatch(
        self,
    ):
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=1,
            growing_period=GrowingPeriodFactory.build(
                start_date=datetime.date(year=2024, month=1, day=1)
            ),
            boundary="start",
        )
        self.assertEqual(datetime.date(year=2024, month=1, day=1), result)

    def test_getDateFromCalendarWeek_weekMatchesTwiceInGrowingPeriodAndBoundaryIsEnd_returnsLastMatch(
        self,
    ):
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2023, month=12, day=31),
            end_date=datetime.date(year=2024, month=12, day=31),
        )
        result = SubscriptionChangeWeekToDateConverter.get_date_from_calendar_week(
            week=52, growing_period=growing_period, boundary="end"
        )
        self.assertEqual(datetime.date(year=2024, month=12, day=29), result)
