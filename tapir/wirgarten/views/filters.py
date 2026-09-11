from django_filters import OrderingFilter


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
