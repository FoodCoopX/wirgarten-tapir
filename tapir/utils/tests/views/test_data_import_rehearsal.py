import csv
import io
from datetime import date, datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from openpyxl import Workbook

from tapir.associations.models import AssociationMembership
from tapir.associations.tests.factories import AssociationMembershipTypeFactory
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.utils.services.data_import_service import STATUS_ERROR
from tapir.wirgarten.constants import ODD_WEEKS, WEEKLY
from tapir.wirgarten.models import Member, MemberPickupLocation, Payment, Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone

MEMBER_HEADERS = ["Nr", "Vorname", "Nachname", "Mailadresse", "consent_sepa"]
CONTRACT_HEADERS = [
    "Mitgliedernummer",
    "product_type",
    "product",
    "Quantity",
    "Vertragsbeginn",
    "Vertragsende",
    "Probezeit",
]


class TestDataImportRehearsal(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._login_as_admin()

    def _preview(self, import_type, upload, update=False):
        response = self.client.post(
            reverse("utils:data_import"),
            {"import_type": import_type, "file": upload, "update_existing": update},
        )
        self.assertStatusCode(response, 200)
        return response.context["result"], response.context["token"]

    def _preview_csv(self, headers, rows, update=False):
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(headers)
        writer.writerows(rows)
        return self._preview(
            "members",
            SimpleUploadedFile("Mitglieder.csv", output.getvalue().encode()),
            update,
        )

    def _preview_contracts(self, rows):
        workbook = Workbook()
        workbook.active.append(CONTRACT_HEADERS)
        for row in rows:
            workbook.active.append(row)
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        return self._preview(
            "subscriptions", SimpleUploadedFile("Vertraege.xlsx", output.getvalue())
        )

    def _apply(self, token):
        response = self.client.post(
            reverse("utils:data_import_apply"), {"token": token}
        )
        self.assertRedirects(response, reverse("utils:data_import"))

    def test_rehearse_two_seasons_and_apply_depot_only_correction(self):
        mock_timezone(self, datetime(2026, 11, 7, 12))
        season_start, season_end = date(2026, 3, 1), date(2027, 2, 28)
        next_start, next_end = date(2027, 3, 1), date(2028, 2, 29)
        summer_join = date(2026, 7, 1)
        GrowingPeriodFactory.create(start_date=season_start, end_date=season_end)
        GrowingPeriodFactory.create(start_date=next_start, end_date=next_end)
        AssociationMembershipTypeFactory.create(name="Erntemitglied")
        AssociationMembershipTypeFactory.create(name="Fördermitglied")
        north = PickupLocationFactory.create(name="Testdepot Nord")
        south = PickupLocationFactory.create(name="Testdepot Süd")
        vegetables = ProductTypeFactory.create(name="Gemüse", delivery_cycle=WEEKLY[0])
        fruit = ProductTypeFactory.create(name="Obst", delivery_cycle=ODD_WEEKS[0])
        ProductFactory.create(name="klein", type=vegetables)
        ProductFactory.create(name="groß", type=vegetables)
        ProductFactory.create(name="klein", type=fruit)

        first = [101, "Erika", "Muster", "erika@example.test", season_start]
        result, token = self._preview_csv(
            MEMBER_HEADERS
            + [
                "Ort",
                "PLZ",
                "Abholort",
                "AO_gueltig_ab",
                "Zahlungsintervall",
                "Vereinsmitgliedschafttyp",
                "Vereinsmitgliedschaft Start_Date",
                "Solidarpreis in EUR",
                "Solidarpreis Start_Date",
                "Solidarpreis End_Date",
            ],
            [
                first
                + [
                    "Köln",
                    "50667",
                    north.name,
                    season_start,
                    "Jährlich",
                    "Erntemitglied",
                    season_start,
                    "-12.50",
                    season_start,
                    season_end,
                ],
                [
                    102,
                    "Max",
                    "Beispiel",
                    "max@example.test",
                    summer_join,
                    "",
                    "",
                    south.name,
                    summer_join,
                    "Monatlich",
                    "Erntemitglied",
                    summer_join,
                    "",
                    "",
                    "",
                ],
                [
                    103,
                    "Ali",
                    "Beispiel",
                    "ali@example.test",
                    season_start,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "Fördermitglied",
                    season_start,
                    "",
                    "",
                    "",
                ],
            ],
        )
        self.assertTrue(result.can_be_applied, result.rows)
        self.assertEqual(3, result.counts["created"])
        self.assertFalse(Member.objects.filter(member_no=101).exists())
        self._apply(token)
        member = Member.objects.get(member_no=101)
        membership = AssociationMembership.objects.get(member=member)
        contribution = SolidarityContribution.objects.get(member=member)
        self.assertEqual(
            "Fördermitglied",
            AssociationMembership.objects.get(member__member_no=103).type.name,
        )

        current_rows = [
            [101, "Gemüse", "klein", 1, season_start, season_end, "nein"],
            [102, "Gemüse", "klein", 2, summer_join, season_end, "nein"],
        ]
        next_rows = [
            [101, "Gemüse", "groß", 1, next_start, next_end, "nein"],
            [101, "Obst", "klein", 1, next_start, next_end, "nein"],
        ]
        result, token = self._preview_contracts(current_rows)
        self.assertTrue(result.can_be_applied, result.rows)
        self.assertFalse(Subscription.objects.exists())
        self._apply(token)
        self.assertFalse(
            Subscription.objects.filter(period__start_date=next_start).exists()
        )

        result, token = self._preview_contracts(next_rows)
        self.assertTrue(result.can_be_applied, result.rows)
        self._apply(token)
        result, token = self._preview_contracts(current_rows + next_rows)
        self.assertTrue(result.can_be_applied, result.rows)
        self.assertEqual(4, result.counts["skipped"])
        self._apply(token)
        self.assertEqual(4, Subscription.objects.count())
        self.assertEqual(4, Subscription.objects.filter(trial_disabled=True).count())
        self.assertFalse(Subscription.objects.filter(member__member_no=103).exists())
        self.assertFalse(Payment.objects.exists())

        member.keycloak_id = "example-id"
        member.save(update_fields=["keycloak_id"])
        result, token = self._preview_csv(
            MEMBER_HEADERS + ["Abholort", "AO_gueltig_ab"],
            [first + [south.name, season_start]],
            update=True,
        )
        self.assertTrue(result.can_be_applied, result.rows)
        self.assertEqual(1, result.counts["updated"])
        self._apply(token)
        member.refresh_from_db()
        self.assertEqual(("Köln", "50667"), (member.city, member.postcode))
        self.assertEqual(
            south, MemberPickupLocation.objects.get(member=member).pickup_location
        )
        self.assertTrue(AssociationMembership.objects.filter(pk=membership.pk).exists())
        self.assertTrue(
            SolidarityContribution.objects.filter(pk=contribution.pk).exists()
        )
        self.assertEqual(
            MemberPaymentRhythm.Rhythm.YEARLY,
            MemberPaymentRhythmService.get_member_payment_rhythm(
                member, season_start, cache={}
            ),
        )

        self.mock_keycloak_client.update_user.assert_not_called()

    def test_linked_email_change_is_rejected_in_preview(self):
        MemberFactory.create(
            member_no=101, email="old@example.test", keycloak_id="example-id"
        )
        result, _ = self._preview_csv(
            MEMBER_HEADERS,
            [[101, "Erika", "Muster", "new@example.test", "2026-03-01"]],
            update=True,
        )
        self.assertFalse(result.can_be_applied)
        self.assertEqual(STATUS_ERROR, result.rows[0].status)
        self.assertIn("verknüpften Kontos", result.rows[0].message)
        self.mock_keycloak_client.update_user.assert_not_called()

    def test_apply_rolls_back_if_an_account_was_linked_after_preview(self):
        member = MemberFactory.create(member_no=101, email="old@example.test")
        result, token = self._preview_csv(
            MEMBER_HEADERS,
            [
                [102, "Max", "Beispiel", "max@example.test", "2026-03-01"],
                [101, "Erika", "Muster", "new@example.test", "2026-03-01"],
            ],
            update=True,
        )
        self.assertTrue(result.can_be_applied, result.rows)
        member.keycloak_id = "example-id"
        member.save(update_fields=["keycloak_id"])
        self._apply(token)
        member.refresh_from_db()
        self.assertEqual("old@example.test", member.email)
        self.assertFalse(Member.objects.filter(member_no=102).exists())
        self.mock_keycloak_client.update_user.assert_not_called()
