import datetime

from django.test import SimpleTestCase

from tapir.utils.shortcuts import get_next_sunday


class TestGetNextSunday(SimpleTestCase):
    def test_getNextSunday_givenDayIsNotSunday_returnsFollowingSunday(self):
        self.assertEqual(
            datetime.date(year=2026, month=4, day=5),
            get_next_sunday(date=datetime.date(year=2026, month=3, day=31)),
        )

    def test_getNextSunday_givenDayIsSunday_returnsSameDay(self):
        self.assertEqual(
            datetime.date(year=2026, month=4, day=5),
            get_next_sunday(date=datetime.date(year=2026, month=4, day=5)),
        )
