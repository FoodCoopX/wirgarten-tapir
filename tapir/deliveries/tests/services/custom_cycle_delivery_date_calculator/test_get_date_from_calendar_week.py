import datetime

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.deliveries.exceptions import TapirCustomCycleException
from tapir.deliveries.services.custom_cycle_delivery_date_calculator import (
    CustomCycleDeliveryDateCalculator,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestGetDateFromWeekObject(TapirUnitTest):
    def test_getDateFromCalendarWeek_givenWeekIsAfterGrowingPeriodStartDateAndInSameYear_returnsCorrectDateOnSameYear(
        self,
    ):
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2024, month=4, day=1)
        )
        week = 16

        result = CustomCycleDeliveryDateCalculator.get_date_from_calendar_week(
            week=week, growing_period=growing_period
        )

        self.assertEqual(datetime.date(year=2024, month=4, day=15), result)

    def test_getDateFromCalendarWeek_givenWeekIsAfterGrowingPeriodStartDateAndInDifferentYear_returnsCorrectDateOnFollowingYear(
        self,
    ):
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2024, month=4, day=1)
        )
        week = 2

        result = CustomCycleDeliveryDateCalculator.get_date_from_calendar_week(
            week=week, growing_period=growing_period
        )

        self.assertEqual(datetime.date(year=2025, month=1, day=6), result)

    def test_getDateFromCalendarWeek_firstDayOfGrowingPeriodIsNotCalendarWeek1_returnsCorrectDateOnSameYear(
        self,
    ):
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2027, month=1, day=1)
        )  # This is a Friday, meaning calendar week 1 in 2027 starts on the following Monday 04.01.2027
        week = 1

        result = CustomCycleDeliveryDateCalculator.get_date_from_calendar_week(
            week=week, growing_period=growing_period
        )

        self.assertEqual(datetime.date(year=2027, month=1, day=4), result)

    def test_getDateFromCalendarWeek_invalidWeekGiven_raisesException(
        self,
    ):
        # Making sure that giving a week too big raises an exception:
        # we don't want a date outside the growing period to be returned
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2025, month=4, day=1)
        )
        week = 53

        with self.assertRaises(ValueError) as error:
            CustomCycleDeliveryDateCalculator.get_date_from_calendar_week(
                week=week, growing_period=growing_period
            )

        self.assertEqual("Invalid week: 53", str(error.exception))

    def test_getDateFromCalendarWeek_givenWeekOverlapsWithGrowingPeriodBoundaries_raisesException(
        self,
    ):
        # Weeks that overlap with the start or end of the growing period lead to undefined scenarios. For example:
        # GrowingPeriod starts on 01.10.2026 (KW40) with deliveries on Wednesdays and Thursdays depending on the PickupLocation
        # Wednesday in KW40 is outside the growing period, Thursday is inside.
        growing_period = GrowingPeriodFactory.build(
            start_date=datetime.date(year=2026, month=10, day=1)
        )
        week = 40

        with self.assertRaises(TapirCustomCycleException) as error:
            CustomCycleDeliveryDateCalculator.get_date_from_calendar_week(
                week=week, growing_period=growing_period
            )

        self.assertEqual(
            "Die ganze Woche muss innerhalb der Vertragsperiode liegen. KW40 geht vom 28.09.2026 bis zum 04.10.2026",
            str(error.exception),
        )
