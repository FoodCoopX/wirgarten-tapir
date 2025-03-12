import datetime

from tapir.deliveries.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.generic_exports.services.export_segment_manager import ExportSegmentColumn
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
        ]

    @classmethod
    def get_value_pickup_location_name(cls, location: PickupLocation, _):
        return location.name

    @classmethod
    def get_value_pickup_location_number_of_member(
        cls, location: PickupLocation, reference_datetime: datetime.datetime
    ):

        members_annotated_with_pickup_location = MemberPickupLocationService.annotate_member_queryset_with_pickup_location_at_date(
            Member.objects.all(), reference_datetime.date()
        )

        return str(
            members_annotated_with_pickup_location.filter(
                current_pickup_location_id=location.id
            ).count()
        )

    @classmethod
    def get_value_pickup_location_member_ids(
        cls, location: PickupLocation, reference_datetime: datetime.datetime
    ):

        members_annotated_with_pickup_location = MemberPickupLocationService.annotate_member_queryset_with_pickup_location_at_date(
            Member.objects.all(), reference_datetime.date()
        )

        return "-".join(
            [
                member.member_no or "Nicht mitglied"
                for member in members_annotated_with_pickup_location.filter(
                    current_pickup_location_id=location.id
                )
            ]
        )
