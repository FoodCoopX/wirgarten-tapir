import datetime

from django.db.models import Q, QuerySet


class PickupLocationActiveFilter:
    @staticmethod
    def get_active_at_date(
        queryset: QuerySet, reference_date: datetime.date
    ) -> QuerySet:
        return queryset.filter(
            (Q(start_date__isnull=True) | Q(start_date__lte=reference_date))
            & (Q(end_date__isnull=True) | Q(end_date__gte=reference_date))
        )
