from functools import reduce
from django_filters import OrderingFilter, Filter
import operator
from django.db.models import (
    Q,
)


class SecondaryOrderingFilter(OrderingFilter):
    """
    Allows to order by a secondary field if the primary field is equal.
    """

    def __init__(self, *args, secondary_ordering="id", **kwargs):
        self.secondary_ordering = secondary_ordering
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value:
            ordering_fields = [self.get_ordering_value(v) for v in value] + [
                f"{'-' if value[0][0] == '-' else ''}{self.secondary_ordering}"
            ]
        else:
            ordering_fields = ["-created_at", f"-{self.secondary_ordering}"]

        return qs.order_by(*ordering_fields)


class MultiFieldFilter(Filter):
    """
    Allows filtering on multiple fields using the same value.
    The implementation is far from perfect, e.g. if you search for firstname + lastname, you will never get a result.
    """

    # FIXME: tokenize search value and search for each token in each field

    def __init__(self, fields=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields = fields or []

    def filter(self, qs, value):
        if value:
            lookups = [Q(**{f"{field}__icontains": value}) for field in self.fields]
            qs = qs.filter(reduce(operator.or_, lookups))
        return qs
