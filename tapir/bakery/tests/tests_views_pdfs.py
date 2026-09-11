from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import SimpleTestCase
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


class TestPickupListTemplate(SimpleTestCase):
    """
    Renders the Abhol-Liste templates straight from a context, because the view
    tests mock the renderer away and never look at the markup the baker prints.
    """

    def _context(self, **overrides):
        context = {
            "report_title": "Abhol-Liste",
            "week": WEEK,
            "day_label": "Donnerstag",
            "date_string": "12.03.2026",
            "today": "10.03.2026",
            "pickup_location_name": "Hofladen",
            "bread_names": ["Dinkelkruste", "Roggenbrot"],
            "bread_totals": {"Dinkelkruste": 3, "Roggenbrot": 5},
            "grand_total": 8,
            "entries": [
                {
                    "member_name": "Anna Bauer",
                    "total": 8,
                    "total_assigned": 8,
                    "bread_counts": {"Dinkelkruste": 3, "Roggenbrot": 5},
                    "bread_preferred": {"Dinkelkruste": True, "Roggenbrot": False},
                    "breads": [],
                }
            ],
        }
        context.update(overrides)
        return context

    def test_totalRow_showsATotalPerBread(self):
        # The per-bread cells of the total row were rendered empty, so checking
        # a variety against the Backliste meant adding the column up by hand.
        html = render_to_string("bakery/pdfs/pickup_list.html", self._context())

        total_row = html.split('class="total-row"')[1]
        self.assertIn(">3<", total_row)
        self.assertIn(">5<", total_row)

    def test_allStations_printsTheCreationDateOnce(self):
        # The partial carried its own footer on top of the one in base_pdf,
        # so the all-stations PDF repeated it once per station.
        context = self._context(
            all_pickup_lists=[
                {
                    "pickup_location_name": name,
                    "bread_names": ["Roggenbrot"],
                    "bread_totals": {"Roggenbrot": 1},
                    "grand_total": 1,
                    "entries": [
                        {
                            "member_name": "Anna Bauer",
                            "total": 1,
                            "total_assigned": 1,
                            "bread_counts": {"Roggenbrot": 1},
                            "bread_preferred": {"Roggenbrot": False},
                            "breads": [],
                        }
                    ],
                }
                for name in ("Hofladen", "Marktstand", "Hofpunkt")
            ]
        )

        html = render_to_string("bakery/pdfs/pickup_lists_all.html", context)

        self.assertEqual(html.count("erstellt am"), 1)


class TestPdfPermissionsAndValidation(TapirIntegrationTest):
    """
    The PDFs carry every member's name, station and bread choices, so they need
    the same gate the API and template views have. Only the logged-out case was
    pinned before.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def _pdf_urls(self):
        return {
            "baking_list": reverse("bakery:baking_list_pdf", args=[YEAR, WEEK, DAY]),
            "distribution_list": reverse(
                "bakery:distribution_list_pdf", args=[YEAR, WEEK, DAY]
            ),
            "pickup_list": reverse(
                "bakery:pickup_list_pdf", args=[YEAR, WEEK, DAY, "somelocid"]
            ),
            "pickup_lists_all": reverse(
                "bakery:pdf_pickup_lists_all", args=[YEAR, WEEK, DAY]
            ),
        }

    def test_allPdfs_plainMember_isForbidden(self):
        self.client.force_login(MemberFactory.create())

        for name, url in self._pdf_urls().items():
            with self.subTest(pdf=name):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_allPdfs_impossibleWeek_returns400(self):
        # 2027 has 52 ISO weeks, and delivery_week is a plain integer
        # everywhere, so week 53 reaches the renderer unless it is caught.
        self.client.force_login(MemberFactory.create(is_superuser=True))

        for name, args in (
            ("bakery:baking_list_pdf", [2027, 53, DAY]),
            ("bakery:distribution_list_pdf", [2027, 53, DAY]),
            ("bakery:pickup_list_pdf", [2027, 53, DAY, "somelocid"]),
            ("bakery:pdf_pickup_lists_all", [2027, 53, DAY]),
        ):
            with self.subTest(pdf=name):
                response = self.client.get(reverse(name, args=args))
                self.assertEqual(response.status_code, 400)

    @patch("tapir.bakery.views_pdfs.weasyprint.HTML")
    def test_distributionList_returnsPdf(self, mock_html):
        mock_html.return_value.write_pdf.return_value = b"%PDF-1.4 fake"
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self.client.get(
            reverse("bakery:distribution_list_pdf", args=[YEAR, WEEK, DAY])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
