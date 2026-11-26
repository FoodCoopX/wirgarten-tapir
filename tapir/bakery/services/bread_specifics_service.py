from django.db import transaction

from tapir.bakery.models import BreadSpecificsPerDeliveryDay


class BreadSpecificsService:
    FIELDS = [
        "min_pieces",
        "max_pieces",
        "min_remaining_pieces",
        "fixed_pieces",
        "max_direct_order_percent",
    ]

    @classmethod
    def apply_updates(
        cls,
        year: int,
        delivery_week: int,
        delivery_day: int,
        updates: list[dict],
        cache: dict,
    ):
        """
        Each update holds a bread and any of FIELDS. A field left out keeps its
        value: the day settings and the direct-order limits are edited in
        different dialogs, each sending only its own fields. A row left without
        any value is deleted.
        """
        with transaction.atomic():
            for update in updates:
                keys = {
                    "year": year,
                    "delivery_week": delivery_week,
                    "delivery_day": delivery_day,
                    "bread_id": update["bread"].pk,
                }
                specifics, _ = BreadSpecificsPerDeliveryDay.objects.update_or_create(
                    **keys,
                    defaults={
                        field: update[field] for field in cls.FIELDS if field in update
                    },
                )
                if all(getattr(specifics, field) is None for field in cls.FIELDS):
                    specifics.delete()
