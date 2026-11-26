from django.db.models import Q

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    Bread,
    BreadDelivery,
)
from tapir.bakery.services.bread_choice_deadline_service import (
    BreadChoiceDeadlineService,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.bakery.services.direct_order_limit_service import (
    DirectOrderLimitService,
)
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)

BREAD_NOT_BAKED_THAT_DAY = "Dieses Brot ist an diesem Liefertag nicht verfügbar."


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
    def check_direct_order_limit(
        cls, delivery: BreadDelivery, new_bread_id, pickup_location_id, cache: dict
    ):
        """
        Call inside a transaction. It locks the entries that bake the bread
        and the other breads of its group that day, whose limit they share,
        so that two members cannot both take the last loaf. Switching the
        bread off or copying a week over it then waits until this choice is
        committed and clears it.

        The entries are locked in one statement in id order, as
        WeeklyPlanService.copy_week locks them, so the two cannot deadlock.
        """
        delivery_day = PickupLocationDeliveryDayService.get_delivery_day(
            pickup_location_id, cache=cache
        )
        if delivery_day is None:
            raise BreadChoiceNotAllowed(BREAD_NOT_BAKED_THAT_DAY)

        # Loaded first, so the locks are held only for the counts.
        BreadDeliveryContextService.warm_caches_for_week(
            delivery.year,
            delivery.delivery_week,
            delivery.subscription.member_id,
            cache=cache,
        )
        group_id = (
            Bread.objects.filter(pk=new_bread_id)
            .values_list("group_id", flat=True)
            .first()
        )
        sharing_the_limit = Q(bread_id=new_bread_id)
        if group_id is not None:
            sharing_the_limit |= Q(bread__group_id=group_id)
        locked_bread_ids = set(
            AvailableBreadsForDeliveryDay.objects.select_for_update(of=("self",))
            .filter(
                sharing_the_limit,
                year=delivery.year,
                delivery_week=delivery.delivery_week,
                delivery_day=delivery_day,
            )
            .order_by("id")
            .values_list("bread_id", flat=True)
        )
        if new_bread_id not in locked_bread_ids:
            raise BreadChoiceNotAllowed(BREAD_NOT_BAKED_THAT_DAY)

        limits = DirectOrderLimitService.get_limits_for_day(
            year=delivery.year,
            delivery_week=delivery.delivery_week,
            delivery_day=delivery_day,
            cache=cache,
            exclude_delivery_ids=[delivery.pk],
        )
        # An inactive bread is left out of the limits.
        if new_bread_id not in limits.breads:
            raise BreadChoiceNotAllowed(BREAD_NOT_BAKED_THAT_DAY)

        remaining = limits.remaining(new_bread_id)
        if remaining is not None and remaining <= 0:
            raise BreadChoiceNotAllowed(
                "Keine Kapazität mehr für dieses Brot verfügbar."
            )
