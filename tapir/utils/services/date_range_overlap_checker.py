import datetime


class DateRangeOverlapChecker:
    @classmethod
    def do_ranges_overlap(
        cls,
        range_1_start: datetime.date,
        range_1_end: datetime.date,
        range_2_start: datetime.date,
        range_2_end: datetime.date,
    ) -> bool:
        latest_start = max(range_1_start, range_2_start)
        earliest_end = min(range_1_end, range_2_end)
        delta = (earliest_end - latest_start).days + 1
        return delta > 0
