import datetime

from django.db.models import QuerySet


class ModelDateRangeOverlapChecker:
    @classmethod
    def filter_objects_that_overlap_with_range[T](
        cls,
        queryset: QuerySet[T],
        range_start: datetime.date,
        range_end: datetime.date,
        field_name_start="start_date",
        field_name_end="end_date",
    ) -> QuerySet[T]:
        return queryset.filter(
            **{
                f"{field_name_start}__lte": range_end,
                f"{field_name_end}__gte": range_start,
            }
        )
