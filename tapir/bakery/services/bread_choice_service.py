from tapir.bakery.models import BreadCapacityPickupLocation
from tapir.bakery.models import BreadDelivery
from tapir.bakery.services.bread_choice_deadline_service import (
    BreadChoiceDeadlineService,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)


class BreadChoiceNotAllowed(Exception):
    """The message is written for the member and is handed back by the API."""


class BreadChoiceService:
    @classmethod
    def check_member_may_change(
        cls, delivery: BreadDelivery, pickup_location_id, cache: dict
    ):
        if not BreadChoiceDeadlineService.may_member_choose_breads(cache=cache):
            raise BreadChoiceNotAllowed(
                "Die Brotauswahl ist derzeit nicht freigegeben."
            )

        if BreadChoiceDeadlineService.can_still_choose(
            year=delivery.year,
            delivery_week=delivery.delivery_week,
            pickup_location_id=pickup_location_id,
            cache=cache,
        ):
            return

        deadline = BreadChoiceDeadlineService.get_deadline(
            year=delivery.year,
            delivery_week=delivery.delivery_week,
            pickup_location_id=pickup_location_id,
            cache=cache,
        )
        raise BreadChoiceNotAllowed(
            "Die Frist zur Brotauswahl für diese Woche ist am "
            f"{deadline.strftime('%d.%m.%Y')} abgelaufen."
        )

    @classmethod
    def check_capacity_available(
        cls, delivery: BreadDelivery, new_bread_id, pickup_location_id, cache: dict
    ):
        """Call inside a transaction: this takes a row lock on the capacity entry."""
        capacity_entry = (
            BreadCapacityPickupLocation.objects.select_for_update()
            .filter(
                bread_id=new_bread_id,
                pickup_location_id=pickup_location_id,
                year=delivery.year,
                delivery_week=delivery.delivery_week,
            )
            .first()
        )
        if not capacity_entry:
            raise BreadChoiceNotAllowed(
                "Dieses Brot ist für diese Station/Woche nicht verfügbar."
            )

        taken = sum(
            1
            for other in BreadDeliveryContextService.get_deliveries_for_location_for_week(
                year=delivery.year,
                delivery_week=delivery.delivery_week,
                pickup_location_id=pickup_location_id,
                cache=cache,
                queryset=BreadDelivery.objects.filter(bread_id=new_bread_id),
            )
            if other.pk != delivery.pk
        )

        if capacity_entry.capacity - taken <= 0:
            raise BreadChoiceNotAllowed(
                "Keine Kapazität mehr für dieses Brot verfügbar."
            )
