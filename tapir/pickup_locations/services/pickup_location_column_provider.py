import datetime

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.subscription_with_deliveries_provider import (
    SubscriptionsWithDeliveriesProvider,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import PickupLocation, Member


class PickupLocationColumnProvider:
    @classmethod
    def get_pickup_location_columns(cls):
        return [
            ExportSegmentColumn(
                id="pickup_location_name",
                display_name="Name",
                description="",
                get_value=cls.get_value_pickup_location_name,
            ),
            ExportSegmentColumn(
                id="pickup_location_number_of_member",
                display_name="Anzahl an Mitglieder",
                description="Anzahl an Mitglieder die an diese Abholstation abholen",
                get_value=cls.get_value_pickup_location_number_of_member,
            ),
            ExportSegmentColumn(
                id="pickup_location_member_ids",
                display_name="Nummer der Mitglieder die an diese Abholstation abholen",
                description="Nummer der Mitglieder die an diese Abholstation abholen",
                get_value=cls.get_value_pickup_location_member_ids,
            ),
            ExportSegmentColumn(
                id="pickup_location_deliveries_current_week",
                display_name="Kommissionierliste",
                description="Alle Verträge die diese Woche geliefert werden",
                get_value=cls.get_value_pickup_location_deliveries_current_week,
            ),
        ]

    @classmethod
    def get_value_pickup_location_name(cls, location: PickupLocation, _, __):
        return location.name

    @classmethod
    def get_value_pickup_location_deliveries_current_week(
        cls,
        location: PickupLocation,
        reference_datetime: datetime.datetime,
        cache: dict,
    ):
        subscriptions = SubscriptionsWithDeliveriesProvider.get_subscriptions_delivered_at_location_and_week(
            pickup_location=location, reference_datetime=reference_datetime, cache=cache
        )

        return [
            {
                "member_no": subscription.member.member_no,
                "last_name": subscription.member.last_name,
                "first_name": subscription.member.first_name,
                "phone_number": subscription.member.phone_number,
                "email": subscription.member.email,
                "product_type_name": subscription.product.type.name,
                "product_name": subscription.product.name,
                "quantity": subscription.quantity,
                "usual_pickup_location": TapirCache.get_pickup_location_by_id(
                    cache=cache,
                    pickup_location_id=MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                        member_id=subscription.member_id,
                        cache=cache,
                        reference_date=reference_datetime.date(),
                    ),
                ),
            }
            for subscription in subscriptions
        ]

    @classmethod
    def get_value_pickup_location_number_of_member(
        cls, location: PickupLocation, reference_datetime: datetime.datetime, _
    ):

        members_annotated_with_pickup_location = MemberPickupLocationGetter.annotate_member_queryset_with_pickup_location_id_at_date(
            Member.objects.all(), reference_datetime.date()
        )

        return str(
            members_annotated_with_pickup_location.filter(
                current_pickup_location_id=location.id
            ).count()
        )

    @classmethod
    def get_value_pickup_location_member_ids(
        cls, location: PickupLocation, reference_datetime: datetime.datetime, cache
    ):

        members_annotated_with_pickup_location = MemberPickupLocationGetter.annotate_member_queryset_with_pickup_location_id_at_date(
            Member.objects.all(), reference_datetime.date()
        )

        return "-".join(
            [
                MemberNumberService.format_member_number(member.member_no, cache=cache)
                or "Nicht Mitglied"
                for member in members_annotated_with_pickup_location.filter(
                    current_pickup_location_id=location.id
                )
            ]
        )
