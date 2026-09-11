import datetime


class DateRangeOverlapChecker:
    @classmethod
    def do_ranges_overlap(
        cls,
        range_1_start: datetime.date,
        range_1_end: datetime.date | None,
        range_2_start: datetime.date,
        range_2_end: datetime.date,
    ) -> bool:
        return (
            cls.get_number_of_days_of_overlap(
                range_1_start=range_1_start,
                range_1_end=range_1_end,
                range_2_start=range_2_start,
                range_2_end=range_2_end,
            )
            > 0
        )

    @classmethod
    def get_number_of_days_of_overlap(
        cls,
        range_1_start: datetime.date,
        range_1_end: datetime.date | None,
        range_2_start: datetime.date,
        range_2_end: datetime.date,
    ):
        latest_start = max(range_1_start, range_2_start)

        if range_1_end is None:
            earliest_end = range_2_end
        else:
            earliest_end = min(range_1_end, range_2_end)

        delta = (earliest_end - latest_start).days + 1
        return max(delta, 0)
