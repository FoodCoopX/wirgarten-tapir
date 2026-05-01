import datetime

from django.db.models import QuerySet


class ModelDateRangeOverlapChecker:
    @classmethod
    def filter_objects_that_overlap_with_range(
        cls,
        queryset: QuerySet,
        range_start: datetime.date,
        range_end: datetime.date,
        field_name_start="start_date",
        field_name_end="end_date",
    ):
        return queryset.filter(
            **{
                f"{field_name_start}__lte": range_end,
                f"{field_name_end}__gte": range_start,
            }
        )
