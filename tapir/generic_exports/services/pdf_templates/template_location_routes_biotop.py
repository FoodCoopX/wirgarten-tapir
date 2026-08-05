import datetime

from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import PdfExport, AutomatedExportCycle
from tapir.pickup_locations.services.pickup_location_segment_provider import (
    PickupLocationSegmentProvider,
)


class TemplateLocationRoutesBiotop:
    ID = "location_routes_biotop"
    NAME = "Abhakzettel"
    DESCRIPTION = "Erzeugt ein einziges PDF mit alle Ausfahrrunden drin (Biotop Oberland-Variante)"

    @classmethod
    def create_exports(cls):
        export_name = cls.NAME
        if PdfExport.objects.filter(name=export_name).exists():
            raise TemplateAlreadyExistsException(
                f'Ein PDF-Export mit dem Namen "{export_name}"  existiert bereits. Falls dieser neu erzeugt werden soll, bitte zuerst den alten Export-Eintrag aus der Liste löschen.'
            )

        with open(
            "tapir/generic_exports/services/pdf_templates/location_routes_biotop.html",
            "r",
        ) as file:
            PdfExport.objects.create(
                name=export_name,
                export_segment_id=PickupLocationSegmentProvider.SEGMENT_ID_ALL_LOCATION_ROUTES,
                file_name="Ausfahrrunden.pdf",
                automated_export_cycle=AutomatedExportCycle.WEEKLY,
                automated_export_day=1,
                automated_export_hour=datetime.time(hour=7),
                generate_one_file_for_every_segment_entry=False,
                template=file.read(),
            )
