from tapir_mail.models import StaticSegmentRecipient

from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.user_utils import UserUtils
from tapir.wirgarten.constants import OPTIONS_WEEKDAYS
from tapir.wirgarten.models import Member, PickupLocationOpeningTime
from tapir.wirgarten.utils import get_today


class PickupLocationMailTokenService:
    NOT_APPLICABLE = "Keine Angabe"

    @classmethod
    def get_pickup_location_if_available(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        if not isinstance(recipient, Member):
            return None

        pickup_location_id = (
            MemberPickupLocationService.get_member_pickup_location_id_from_cache(
                member_id=recipient.id,
                reference_date=get_today(cache=cache),
                cache=cache,
            )
        )
        if pickup_location_id is None:
            return None

        return TapirCache.get_pickup_location_by_id(
            cache=cache, pickup_location_id=pickup_location_id
        )

    @classmethod
    def pickup_location_name(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        pickup_location = cls.get_pickup_location_if_available(recipient, cache)
        if pickup_location is None:
            return cls.NOT_APPLICABLE

        return pickup_location.name

    @classmethod
    def pickup_location_address(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        pickup_location = cls.get_pickup_location_if_available(recipient, cache)
        if pickup_location is None:
            return cls.NOT_APPLICABLE

        return UserUtils.build_display_address(
            street=pickup_location.street,
            street_2=pickup_location.street_2,
            postcode=pickup_location.postcode,
            city=pickup_location.city,
        )

    @classmethod
    def pickup_location_access_code(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        pickup_location = cls.get_pickup_location_if_available(recipient, cache)
        if pickup_location is None:
            return cls.NOT_APPLICABLE

        return pickup_location.access_code

    @classmethod
    def pickup_location_messenger_group_link(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        pickup_location = cls.get_pickup_location_if_available(recipient, cache)
        if pickup_location is None:
            return cls.NOT_APPLICABLE

        return pickup_location.messenger_group_link

    @classmethod
    def pickup_location_contact_name(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        pickup_location = cls.get_pickup_location_if_available(recipient, cache)
        if pickup_location is None:
            return cls.NOT_APPLICABLE

        return pickup_location.contact_name

    @classmethod
    def pickup_location_photo_link(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        pickup_location = cls.get_pickup_location_if_available(recipient, cache)
        if pickup_location is None:
            return cls.NOT_APPLICABLE

        return pickup_location.photo_link

    @classmethod
    def pickup_location_info(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        pickup_location = cls.get_pickup_location_if_available(recipient, cache)
        if pickup_location is None:
            return cls.NOT_APPLICABLE

        return pickup_location.info

    @classmethod
    def pickup_location_opening_times(
        cls, recipient: Member | StaticSegmentRecipient, cache: dict
    ):
        pickup_location = cls.get_pickup_location_if_available(recipient, cache)
        if pickup_location is None:
            return cls.NOT_APPLICABLE

        formatted_times = []
        for opening_time in PickupLocationOpeningTime.objects.filter(
            pickup_location_id=pickup_location.id
        ).order_by("day_of_week"):
            open_time = opening_time.open_time.strftime("%H:%M")
            close_time = opening_time.close_time.strftime("%H:%M")

            formatted_times.append(
                f"{OPTIONS_WEEKDAYS[opening_time.day_of_week][1]}: {open_time}-{close_time}"
            )
        return ", ".join(formatted_times)
