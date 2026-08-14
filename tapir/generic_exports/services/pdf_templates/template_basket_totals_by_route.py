import datetime

from tapir.configuration.parameter import get_parameter_value
from tapir.generic_exports.exceptions import TemplateAlreadyExistsException
from tapir.generic_exports.models import PdfExport, AutomatedExportCycle
from tapir.pickup_locations.services.pickup_location_segment_provider import (
    PickupLocationSegmentProvider,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class TemplateBasketTotalsByRoute:
    ID = "basket_totals_by_route"
    NAME = "Kistenzahl pro Ausfahrrunde"
    DESCRIPTION = (
        "Erzeugt ein PDF mit den Kisten- bzw. Anteilssummen je Ausfahrrunde "
        "(Tour), optional aufgeschlüsselt nach Verteilstation."
    )

    @classmethod
    def create_exports(cls):
        export_name = cls.NAME
        if PdfExport.objects.filter(name=export_name).exists():
            raise TemplateAlreadyExistsException(
                f'Ein PDF-Export mit dem Namen "{export_name}"  existiert bereits. '
                "Falls dieser neu erzeugt werden soll, bitte zuerst den alten "
                "Export-Eintrag aus der Liste löschen."
            )

        admin_email = get_parameter_value(ParameterKeys.SITE_ADMIN_EMAIL, cache={})
        email_recipients = [admin_email] if admin_email else []

        with open(
            "tapir/generic_exports/services/pdf_templates/basket_totals_by_route.html",
            "r",
        ) as file:
            PdfExport.objects.create(
                name=export_name,
                export_segment_id=PickupLocationSegmentProvider.SEGMENT_ID_ALL_LOCATION_ROUTES,
                file_name="Kistenzahl_Ausfahrrunden.pdf",
                email_recipients=email_recipients,
                automated_export_cycle=AutomatedExportCycle.AFTER_PICKUP_LOCATION_CHANGE_DEADLINE,
                automated_export_day=1,
                automated_export_hour=datetime.time(hour=0),
                generate_one_file_for_every_segment_entry=False,
                template=file.read(),
            )
