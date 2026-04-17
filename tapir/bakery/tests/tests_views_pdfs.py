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

    def test_baking_list_unauthenticated_redirects(self):
        self.client.logout()
        url = reverse(
            "bakery:baking_list_pdf", kwargs={"year": YEAR, "week": WEEK, "day": DAY}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    @patch("tapir.bakery.views_pdfs.weasyprint.HTML")
    @patch("tapir.bakery.views_pdfs.BakingListService.get_baking_list")
    def test_baking_list_returns_pdf(self, mock_service, mock_html):
        mock_service.return_value = {"sessions": [], "bread_quantities": []}
        mock_html.return_value.write_pdf.return_value = b"%PDF-fake"

        url = reverse(
            "bakery:baking_list_pdf", kwargs={"year": YEAR, "week": WEEK, "day": DAY}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("Backliste", response["Content-Disposition"])

    def test_pickup_list_invalidPickupLocation_returns404(self):
        url = reverse(
            "bakery:pickup_list_pdf",
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
    def test_pickup_lists_all_noData_returns404(self, mock_html):
        url = reverse(
            "bakery:pdf_pickup_lists_all",
            kwargs={"year": YEAR, "week": WEEK, "day": DAY},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
