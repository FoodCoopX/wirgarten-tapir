import datetime

from django.test import SimpleTestCase

from tapir.utils.services.date_range_overlap_checker import DateRangeOverlapChecker


class TestsDateRangeOverlapChecker(SimpleTestCase):
    def test_doRangesOverlap_range1IsCompletelyBeforeRange2_returnsFalse(self):
        self.assertFalse(
            DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=datetime.date(year=2024, month=4, day=5),
                range_1_end=datetime.date(year=2024, month=5, day=16),
                range_2_start=datetime.date(year=2024, month=5, day=17),
                range_2_end=datetime.date(year=2024, month=5, day=22),
            )
        )

    def test_doRangesOverlap_range2IsCompletelyBeforeRange1_returnsFalse(self):
        self.assertFalse(
            DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=datetime.date(year=2024, month=5, day=23),
                range_1_end=datetime.date(year=2025, month=1, day=3),
                range_2_start=datetime.date(year=2024, month=5, day=17),
                range_2_end=datetime.date(year=2024, month=5, day=22),
            )
        )

    def test_doRangesOverlap_range1OverlapsBeginningOfRange2_returnsTrue(self):
        self.assertTrue(
            DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=datetime.date(year=2024, month=5, day=23),
                range_1_end=datetime.date(year=2025, month=1, day=3),
                range_2_start=datetime.date(year=2025, month=1, day=1),
                range_2_end=datetime.date(year=2025, month=3, day=22),
            )
        )

    def test_doRangesOverlap_range1OverlapsEndOfRange2_returnsTrue(self):
        self.assertTrue(
            DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=datetime.date(year=2025, month=1, day=1),
                range_1_end=datetime.date(year=2025, month=3, day=22),
                range_2_start=datetime.date(year=2024, month=5, day=23),
                range_2_end=datetime.date(year=2025, month=1, day=3),
            )
        )

    def test_doRangesOverlap_range1IsInsideRange2_returnsTrue(self):
        self.assertTrue(
            DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=datetime.date(year=2025, month=3, day=4),
                range_1_end=datetime.date(year=2025, month=4, day=16),
                range_2_start=datetime.date(year=2025, month=3, day=1),
                range_2_end=datetime.date(year=2025, month=4, day=20),
            )
        )

    def test_doRangesOverlap_range2IsInsideRange1_returnsTrue(self):
        self.assertTrue(
            DateRangeOverlapChecker.do_ranges_overlap(
                range_1_start=datetime.date(year=2025, month=3, day=1),
                range_1_end=datetime.date(year=2025, month=4, day=20),
                range_2_start=datetime.date(year=2025, month=3, day=4),
                range_2_end=datetime.date(year=2025, month=4, day=16),
            )
        )
