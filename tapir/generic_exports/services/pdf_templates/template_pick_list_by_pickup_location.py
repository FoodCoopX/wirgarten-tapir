import datetime

from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import PdfExport, AutomatedExportCycle
from tapir.pickup_locations.services.pickup_location_segment_provider import (
    PickupLocationSegmentProvider,
)
from tapir.wirgarten.models import PickupLocation


class TemplatePickListByPickupLocation:
    ID = "pick_list_by_pickup_location"
    NAME = "Kommissionierliste pro Abholort"
    DESCRIPTION = "Erzeugt ein PDF-Export pro Abholort. Im PDF ist die Liste alle Mitglieder die in der Woche eine Lieferung bekommen, mit Kontakt- und Vertrag-Daten"

    @classmethod
    def create_exports(cls):
        for pickup_location in PickupLocation.objects.order_by("name"):
            cls._create_export(pickup_location)

    @classmethod
    def _create_export(cls, pickup_location: PickupLocation):
        export_name = f"Kommissionierungsliste {pickup_location.name}"
        if PdfExport.objects.filter(name=export_name).exists():
            raise TemplateAlreadyExistsException(
                f'Ein PDF-Export mit name "{export_name}" existiert bereits, wenn du den neu erzeugen willst muss du die alte löschen.'
            )

        with open(
            "tapir/generic_exports/services/pdf_templates/pick_list_by_pickup_location.html",
            "r",
        ) as file:
            PdfExport.objects.create(
                name=export_name,
                export_segment_id=PickupLocationSegmentProvider.SEGMENT_ID_ALL_PICKUP_LOCATIONS,
                file_name=f"Kommissionierungsliste {pickup_location.name}.pdf",
                automated_export_cycle=AutomatedExportCycle.WEEKLY,
                automated_export_day=1,
                automated_export_hour=datetime.time(hour=7),
                generate_one_file_for_every_segment_entry=False,
                template=file.read().replace(
                    "PICKUP_LOCATION_NAME", pickup_location.name
                ),
            )
