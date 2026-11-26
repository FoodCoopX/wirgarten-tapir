from django.test import TestCase

from tapir.bakery.utils import is_valid_iso_week


class TestIsValidIsoWeek(TestCase):
    def test_isValidIsoWeek_week53_isValidOnlyInYearsThatHaveIt(self):
        self.assertTrue(is_valid_iso_week(2026, 53))
        self.assertFalse(is_valid_iso_week(2027, 53))

    def test_isValidIsoWeek_outOfRange_returnsFalse(self):
        for year, week in ((2026, 0), (2026, 54), (0, 1), (10**20, 1)):
            with self.subTest(year=year, week=week):
                self.assertFalse(is_valid_iso_week(year, week))

    def test_isValidIsoWeek_sundayBeyondTheLastDate_returnsFalse(self):
        # Its Monday is 27.12.9999; its Sunday would be in the year 10000.
        self.assertFalse(is_valid_iso_week(9999, 52))
        self.assertTrue(is_valid_iso_week(9999, 51))
