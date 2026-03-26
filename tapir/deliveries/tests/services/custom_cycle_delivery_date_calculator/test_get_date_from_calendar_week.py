import datetime

from django.test import SimpleTestCase

from tapir.deliveries.services.custom_cycle_delivery_date_calculator import (
    CustomCycleDeliveryDateCalculator,
)
from tapir.wirgarten.tests.factories import GrowingPeriodFactory


class TestGetDateFromWeekObject(SimpleTestCase):
    def test_getDateFromCalendarWeek_givenWeekIsAfterGrowingPeriodStartDateAndInSameYear_returnsCorrectDate(
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

    def test_getDateFromCalendarWeek_givenWeekIsAfterGrowingPeriodStartDateAndInDifferentYear_returnsCorrectDate(
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

    def test_getDateFromCalendarWeek_firstDayOfGrowingPeriodIsNotCalendarWeek1_returnsDateNextYear(
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
        )  # This is a Friday, meaning calendar week 1 in 2027 starts on the following Monday 04.01.2027
        week = 53

        with self.assertRaises(ValueError) as error:
            CustomCycleDeliveryDateCalculator.get_date_from_calendar_week(
                week=week, growing_period=growing_period
            )

        self.assertEqual("Invalid week: 53", str(error.exception))
