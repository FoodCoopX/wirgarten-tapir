from unittest.mock import patch

from django.urls import reverse

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

YEAR = 2026
WEEK = 11
DAY = 3


class TestPdfViews(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create(is_superuser=True)
        self.client.force_login(self.member)

    def test_backliste_unauthenticated_redirects(self):
        self.client.logout()
        url = reverse(
            "bakery:backliste_pdf", kwargs={"year": YEAR, "week": WEEK, "day": DAY}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    @patch("tapir.bakery.views_pdfs.weasyprint.HTML")
    @patch("tapir.bakery.views_pdfs.BacklisteService.get_backliste")
    def test_backliste_returns_pdf(self, mock_service, mock_html):
        mock_service.return_value = {"sessions": [], "bread_quantities": []}
        mock_html.return_value.write_pdf.return_value = b"%PDF-fake"

        url = reverse(
            "bakery:backliste_pdf", kwargs={"year": YEAR, "week": WEEK, "day": DAY}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("Backliste", response["Content-Disposition"])

    def test_abholliste_invalidPickupLocation_returns404(self):
        url = reverse(
            "bakery:abholliste_pdf",
            kwargs={
                "year": YEAR,
                "week": WEEK,
                "day": DAY,
                "pickup_location_id": "nonexistent",
            },
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    @patch("tapir.bakery.views_pdfs.weasyprint.HTML")
    def test_abhollisten_all_noData_returns404(self, mock_html):
        url = reverse(
            "bakery:pdf_abhollisten_all",
            kwargs={"year": YEAR, "week": WEEK, "day": DAY},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
