from django.apps import AppConfig

from tapir.generic_exports.services.export_segment_manager import (
    ExportSegmentManager,
)


class GenericExportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tapir.generic_exports"

    def ready(self) -> None:
        from tapir.generic_exports.services.member_segment_provider import (
            MemberSegmentProvider,
        )

        for segment in MemberSegmentProvider.get_member_segments():
            ExportSegmentManager.register_segment(segment)

        from tapir.pickup_locations.services.pickup_location_segment_provider import (
            PickupLocationSegmentProvider,
        )

        for segment in PickupLocationSegmentProvider.get_pickup_location_segments():
            ExportSegmentManager.register_segment(segment)
