import datetime

from django.utils.html import escape
from tapir_mail.models import StaticSegmentRecipient

from tapir.bakery.models import Bread
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import week_to_monday
from tapir.wirgarten.constants import OPTIONS_WEEKDAYS
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import format_date, get_today


class BreadMailTokenService:
    NOT_APPLICABLE = "Keine Angabe"
    BREADS_NOT_SET_YET = "Brote noch nicht festgelegt"
    JOKER_TAKEN = "Joker genommen, keine Brotlieferung"

    @classmethod
    def breads_this_week(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ) -> str:
        return cls._build_token(recipient=recipient, weeks_from_now=0, cache=cache)

    @classmethod
    def breads_next_week(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ) -> str:
        return cls._build_token(recipient=recipient, weeks_from_now=1, cache=cache)

    @classmethod
    def _build_token(
        cls,
        recipient: Member | StaticSegmentRecipient,
        weeks_from_now: int,
        cache: dict,
    ) -> str:
        if not isinstance(recipient, Member):
            return cls.NOT_APPLICABLE

        year, delivery_week, _ = (
            get_today(cache=cache) + datetime.timedelta(weeks=weeks_from_now)
        ).isocalendar()

        if recipient.id not in TapirCache.get_member_ids_with_bread_delivery_in_week(
            cache=cache, year=year, delivery_week=delivery_week
        ):
            return cls.NOT_APPLICABLE

        reference_date = BreadDeliveryContextService.get_reference_date(
            year, delivery_week, cache=cache
        )
        if JokerManagementService.does_member_have_a_joker_in_week(
            member_id=recipient.id, reference_date=reference_date, cache=cache
        ):
            return cls.JOKER_TAKEN

        pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=recipient.id, reference_date=reference_date, cache=cache
            )
        )
        delivery_day = PickupLocationDeliveryDayService.get_delivery_day(
            pickup_location_id=pickup_location_id, cache=cache
        )
        if delivery_day is None:
            return cls.NOT_APPLICABLE

        breads = TapirCache.get_breads_with_capacity_by_pickup_location_id(
            cache=cache, year=year, delivery_week=delivery_week
        ).get(pickup_location_id, [])
        if not breads:
            return cls.BREADS_NOT_SET_YET

        delivery_date = week_to_monday(year, delivery_week) + datetime.timedelta(
            days=delivery_day
        )
        return cls._format(delivery_date=delivery_date, breads=breads)

    @classmethod
    def _format(cls, delivery_date: datetime.date, breads: list[Bread]) -> str:
        day = f"{OPTIONS_WEEKDAYS[delivery_date.weekday()][1]}, {format_date(delivery_date)}"
        return (
            day
            + "<br>"
            + "<br><br>".join(cls._format_bread(bread=bread) for bread in breads)
        )

    @staticmethod
    def _format_bread(bread: Bread) -> str:
        lines = [bread.name, bread.description]
        ingredients = [content.ingredient.name for content in bread.contents.all()]
        if ingredients:
            lines.append("Zutaten: " + ", ".join(ingredients))
        return "<br>".join(escape(line) for line in lines if line)
