from dataclasses import dataclass

from django.db import transaction

from tapir.bakery.models import BreadSpecificsPerDeliveryDay


@dataclass
class BreadSpecificsUpdate:
    bread_id: str
    # Only the fields sent, among BreadSpecificsService.FIELDS. A field left
    # out keeps its value; None clears it.
    values: dict[str, int | None]


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
        updates: list[BreadSpecificsUpdate],
        cache: dict,
    ):
        """
        The day settings and the direct-order limits are edited in different
        dialogs, each sending only its own fields. A row left without any
        value is deleted.
        """
        with transaction.atomic():
            for update in updates:
                specifics, _ = BreadSpecificsPerDeliveryDay.objects.update_or_create(
                    year=year,
                    delivery_week=delivery_week,
                    delivery_day=delivery_day,
                    bread_id=update.bread_id,
                    defaults=update.values,
                )
                if all(getattr(specifics, field) is None for field in cls.FIELDS):
                    specifics.delete()
