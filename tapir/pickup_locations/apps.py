import typing
from functools import partial

from django.apps import AppConfig
from tapir_mail.registries import mail_segment_providers

if typing.TYPE_CHECKING:
    from tapir.wirgarten.models import PickupLocation


class PickupLocationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.pickup_locations"

    def ready(self):
        mail_segment_providers.add(self.provide_pickup_location_segments)

    @classmethod
    def provide_pickup_location_segments(cls):
        from tapir.wirgarten.models import PickupLocation

        cache = {}

        return {
            "Abholort: "
            + pickup_location.name: partial(
                cls.get_queryset_for_pickup_location, pickup_location, cache
            )
            for pickup_location in PickupLocation.objects.all()
        }

    @staticmethod
    def get_queryset_for_pickup_location(pickup_location: PickupLocation, cache: dict):
        from tapir.wirgarten.models import Member
        from tapir.pickup_locations.services.member_pickup_location_getter import (
            MemberPickupLocationGetter,
        )
        from tapir.wirgarten.utils import get_today

        queryset = MemberPickupLocationGetter.annotate_member_queryset_with_pickup_location_id_at_date(
            queryset=Member.objects.all(), reference_date=get_today(cache)
        )

        return queryset.filter(
            **{
                MemberPickupLocationGetter.ANNOTATION_CURRENT_PICKUP_LOCATION_ID: pickup_location.id
            }
        )
