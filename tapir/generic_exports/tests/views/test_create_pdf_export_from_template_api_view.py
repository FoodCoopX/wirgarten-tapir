from django.urls import reverse
from rest_framework import status

from tapir.generic_exports.models import PdfExport
from tapir.generic_exports.services.pdf_templates.template_pick_list_by_pickup_location import (
    TemplatePickListByPickupLocation,
)
from tapir.generic_exports.tests.factories import PdfExportFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCreatePdfExportFromTemplateApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_normalUserTriesToGetList_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        url = reverse(
            "generic_exports:create_pdf_export_from_templates",
        )
        url = f"{url}?template_id={TemplatePickListByPickupLocation.ID}"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_default_createsExports(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        PickupLocationFactory.create_batch(size=3)

        url = reverse(
            "generic_exports:create_pdf_export_from_templates",
        )
        url = f"{url}?template_id={TemplatePickListByPickupLocation.ID}"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(3, PdfExport.objects.count())

        self.assert_order_confirmed(response.json())

    def test_post_exportAlreadyExists_returnsCorrectError(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        pickup_locations = PickupLocationFactory.create_batch(size=3)

        PdfExportFactory.create(
            name=f"Kommissionierungsliste {pickup_locations[0].name}"
        )

        url = reverse(
            "generic_exports:create_pdf_export_from_templates",
        )
        url = f"{url}?template_id={TemplatePickListByPickupLocation.ID}"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual(
            f'Ein PDF-Export mit name "Kommissionierungsliste {pickup_locations[0].name}" existiert bereits, wenn du den neu erzeugen willst muss du die alte löschen.',
            response_content["error"],
        )
