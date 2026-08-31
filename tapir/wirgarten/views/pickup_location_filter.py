from django.db.models import Q
from django_filters import CharFilter, FilterSet, ModelChoiceFilter

from tapir.wirgarten.models import GrowingPeriod, PickupLocation


class PickupLocationFilter(FilterSet):
    search = CharFilter(method="filter_search", label="Suche")
    growing_period = ModelChoiceFilter(
        label="Vertragsperiode",
        queryset=GrowingPeriod.objects.all().order_by("start_date"),
        method="filter_growing_period",
    )

    def __init__(self, *args, **kwargs):
        self.cache = kwargs.pop("cache", {})
        super().__init__(*args, **kwargs)

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(name__icontains=value)
            | Q(street__icontains=value)
            | Q(postcode__icontains=value)
            | Q(city__icontains=value)
        )

    def filter_growing_period(self, queryset, name, value):
        if value:
            return queryset.filter(
                growing_period_links__growing_period_id=value
            ).distinct()
        return queryset

    class Meta:
        model = PickupLocation
        fields = ["search", "growing_period"]
