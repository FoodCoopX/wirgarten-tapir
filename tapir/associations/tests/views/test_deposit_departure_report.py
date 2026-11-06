import csv
import datetime
import io
from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tapir.accounts.models import TapirUser
from tapir.associations.deposit_report_views import DepositDepartureReportView
from tapir.associations.models import AssociationDepositRefund
from tapir.associations.services.association_deposit_departure_report_provider import (
    AssociationDepositDepartureReportProvider,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.tests.factories import (
    AssociationDepositAccountFactory,
    AssociationDepositReceiptFactory,
    AssociationMembershipFactory,
)
from tapir.core.config import (
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_COMPANY,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestDepositDepartureReport(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.today = datetime.date(2026, 11, 6)
        mock_timezone(self, datetime.datetime(2026, 11, 6, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        self.admin = MemberFactory(is_superuser=True)
        self.client.force_login(self.admin)
        self.url = reverse("associations:deposit_departure_report")

    def account(
        self,
        start=datetime.date(2025, 1, 1),
        end=datetime.date(2025, 12, 31),
        amount=Decimal("200"),
        received=Decimal("200"),
        refunded=Decimal("0"),
    ):
        member = MemberFactory(iban="NL88ABNA2011060885", account_owner='Test; "Bank"')
        AssociationMembershipFactory(member=member, start_date=start, end_date=end)
        account = AssociationDepositAccountFactory(
            member=member,
            agreed_amount=amount,
            effective_from=start if amount is not None else None,
        )
        if received:
            AssociationDepositReceiptFactory(
                account=account,
                amount=received,
                received_on=datetime.date(2025, 12, 31),
            )
        if refunded:
            AssociationDepositRefund.objects.create(
                account=account,
                amount=refunded,
                refunded_on=self.today,
                reference=f"return-{member.pk}",
                note="Extern bestätigt",
            )
            account.refund_requires_agreement = True
            account.save()
        return account

    def test_true_latest_departure_excludes_type_changes_and_current_or_future_return(
        self,
    ):
        departed = self.account(refunded=Decimal("50"))
        complete = self.account(refunded=Decimal("200"))
        latest = self.account()
        AssociationMembershipFactory(
            member=latest.member,
            start_date=datetime.date(2023, 1, 1),
            end_date=datetime.date(2024, 6, 30),
        )
        for start in [
            datetime.date(2025, 12, 31),
            datetime.date(2026, 1, 1),
            datetime.date(2026, 3, 1),
            datetime.date(2027, 3, 1),
        ]:
            account = self.account()
            AssociationMembershipFactory(member=account.member, start_date=start)
        future_end = self.account(end=self.today)
        future_end2 = self.account(end=datetime.date(2026, 12, 31))
        no_coverage = AssociationDepositAccountFactory()
        no_account = MemberFactory()
        AssociationMembershipFactory(
            member=no_account,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
        )
        report = AssociationDepositDepartureReportProvider.get_report(2025, {})
        self.assertEqual(
            {departed.member_id, complete.member_id, latest.member_id},
            {row["member"].pk for row in report["rows"]},
        )
        self.assertEqual(350, report["retained_amount"])
        self.assertEqual(3, report["member_count"])
        self.assertEqual(self.today, report["as_of"])
        self.assertEqual(
            [], AssociationDepositDepartureReportProvider.get_report(2024, {})["rows"]
        )
        self.assertEqual(
            0,
            next(
                row for row in report["rows"] if row["member"].pk == complete.member_id
            )["retained_amount"],
        )

    def test_report_matches_current_member_balance_with_booked_stopped_unknown_and_waived(
        self,
    ):
        booked = self.account(received=Decimal("0"))
        paid = PaymentFactory(
            association_deposit_account=booked,
            mandate_ref__member=booked.member,
            amount=50,
        )
        stopped = PaymentFactory(
            association_deposit_account=booked,
            mandate_ref__member=booked.member,
            status=Payment.PaymentStatus.DUE,
            transaction=None,
            amount=150,
            due_date=datetime.date(2026, 1, 5),
        )
        waived = self.account(amount=Decimal("0"), received=Decimal("25"))
        unknown = self.account(amount=None, received=Decimal("25"))
        report = AssociationDepositDepartureReportProvider.get_report(2025, {})
        for row in report["rows"]:
            with self.subTest(member=row["member"].pk):
                details = AssociationDepositDetailsProvider.get_deposit_details(
                    row["member"], {}
                )
                for key in [
                    "agreed_amount",
                    "received_amount",
                    "committed_amount",
                    "pending_amount",
                    "stopped_amount",
                    "refunded_amount",
                    "retained_amount",
                    "overpayment_credit",
                ]:
                    self.assertEqual(details[key], row[key])
        self.assertEqual(100, report["retained_amount"])
        paid.refresh_from_db()
        stopped.refresh_from_db()
        self.assertEqual(50, paid.amount)
        self.assertIsNotNone(paid.transaction_id)
        self.assertEqual(150, stopped.amount)
        self.assertEqual(Payment.PaymentStatus.DUE, stopped.status)

    def test_actual_report_and_csv_default_to_previous_year_and_escape_bank_data(self):
        account = self.account(refunded=Decimal("50"))
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(2025, response.context_data["report"]["year"])
        self.assertContains(response, "150,00")
        self.assertContains(response, "mit den tatsächlichen Bankeingängen abgleichen")
        response = self.client.get(self.url, {"year": 2025, "format": "csv"})
        rows = list(
            csv.DictReader(io.StringIO(response.content.decode()), delimiter=";")
        )
        self.assertEqual(1, len(rows))
        self.assertEqual(account.member.account_owner, rows[0]["Kontoinhaber"])
        self.assertEqual(account.member.iban, rows[0]["IBAN"])
        self.assertEqual("31.12.2025", rows[0]["Letzter wirksamer Austritt"])
        self.assertEqual("06.11.2026", rows[0]["Buchungsstand vom"])
        self.assertEqual(
            "150,00",
            next(value for key, value in rows[0].items() if "Buchungsrest" in key),
        )

    def test_invalid_year_never_produces_bank_csv(self):
        account = self.account()
        for year in ["invalid", "1899", "2027", "999999999"]:
            with self.subTest(year=year):
                response = self.client.get(self.url, {"year": year, "format": "csv"})
                self.assertEqual(200, response.status_code)
                self.assertTrue(response.context_data["form"].errors)
                self.assertIsNone(response.context_data["report"])
                self.assertNotIn("Content-Disposition", response)
                self.assertNotContains(response, account.member.iban)

    def test_financial_permission_and_association_status_guard_html_and_csv(self):
        self.account()
        self.client.logout()
        self.assertEqual(302, self.client.get(self.url).status_code)
        self.client.force_login(MemberFactory())
        for data in [{}, {"year": 2025, "format": "csv"}]:
            with self.subTest(data=data):
                self.assertEqual(403, self.client.get(self.url, data).status_code)
                with patch.object(
                    TapirUser,
                    "has_perm",
                    autospec=True,
                    side_effect=lambda user, permission, obj=None: permission
                    == Permission.Coop.MANAGE,
                ):
                    self.assertEqual(200, self.client.get(self.url, data).status_code)
                with patch.object(
                    TapirUser,
                    "has_perm",
                    autospec=True,
                    side_effect=lambda user, permission, obj=None: permission
                    == Permission.Coop.VIEW,
                ):
                    self.assertEqual(403, self.client.get(self.url, data).status_code)
        self.client.force_login(self.admin)
        for legal_status in [LEGAL_STATUS_COOPERATIVE, LEGAL_STATUS_COMPANY]:
            self._set_parameter(ParameterKeys.ORGANISATION_LEGAL_STATUS, legal_status)
            self.assertEqual(404, self.client.get(self.url).status_code)
            self.assertEqual(
                404, self.client.get(self.url, {"format": "csv"}).status_code
            )

    def test_csv_exports_full_year_not_only_current_page(self):
        accounts = [self.account() for _ in range(3)]
        with patch.object(DepositDepartureReportView, "paginate_by", 2):
            response = self.client.get(self.url, {"year": 2025, "page": 2})
            self.assertEqual(1, len(response.context_data["page"].object_list))
            self.assertContains(response, "year=2025&amp;page=1")
            response = self.client.get(
                self.url, {"year": 2025, "page": 2, "format": "csv"}
            )
            rows = list(
                csv.DictReader(io.StringIO(response.content.decode()), delimiter=";")
            )
        self.assertEqual(3, len(rows))
        self.assertEqual(
            {account.member.email for account in accounts},
            {row["Email"] for row in rows},
        )

    def test_dashboard_uses_same_cohorts_even_without_harvest_configuration(self):
        self.account(refunded=Decimal("50"))
        response = self.client.get(reverse("wirgarten:admin_dashboard"))
        self.assertEqual(200, response.status_code)
        self.assertContains(response, "Einlagenstand nach Austrittsjahr")
        self.assertContains(response, "150,00")
        self.assertEqual(
            150,
            response.context_data["deposit_departure_data"]["cohorts"][0][
                "retained_amount"
            ],
        )
        with patch.object(
            TapirUser,
            "has_perm",
            autospec=True,
            side_effect=lambda user, permission, obj=None: permission
            == Permission.Coop.VIEW,
        ):
            response = self.client.get(reverse("wirgarten:admin_dashboard"))
            self.assertNotContains(response, "Einlagenstand nach Austrittsjahr")

    def test_dashboard_reuses_bounded_report_queries_without_writes(self):
        self.account(refunded=Decimal("50"))
        self.account(start=datetime.date(2024, 1, 1), end=datetime.date(2024, 12, 31))
        self.account(end=None)
        with CaptureQueriesContext(connection) as queries:
            cache = {}
            data = AssociationDepositDepartureReportProvider.get_dashboard_data(cache)
            report = AssociationDepositDepartureReportProvider.get_report(2025, cache)
        financial_reads = [
            q
            for q in queries
            if any(
                table in q["sql"]
                for table in ["associations_association", "wirgarten_payment"]
            )
        ]
        self.assertLessEqual(len(financial_reads), 6)
        self.assertEqual([2025, 2024], [cohort["year"] for cohort in data["cohorts"]])
        self.assertEqual(150, report["retained_amount"])
        self.assertEqual(550, data["overall_retained_amount"])
        self.assertFalse(
            any(
                q["sql"].lstrip().startswith(("UPDATE", "INSERT", "DELETE"))
                for q in queries
            )
        )

    def test_missing_bank_details_have_placeholders_but_csv_stays_empty(self):
        account = self.account()
        for missing in [None, ""]:
            with self.subTest(missing=missing):
                account.member.iban = missing
                account.member.account_owner = missing
                account.member.save(update_fields=["iban", "account_owner"])
                response = self.client.get(self.url)
                self.assertContains(response, "Fehlt", count=2)
                self.assertNotContains(response, "<td>None<br/>None</td>")
                response = self.client.get(self.url, {"year": 2025, "format": "csv"})
                row = next(
                    csv.DictReader(
                        io.StringIO(response.content.decode()), delimiter=";"
                    )
                )
                self.assertEqual("", row["Kontoinhaber"])
                self.assertEqual("", row["IBAN"])

    def test_completed_refund_describes_conditional_collection_hold_without_open_task(
        self,
    ):
        account = self.account(refunded=Decimal("200"))
        response = self.client.get(self.url)
        label = "Einzug bis zu neuer Vereinbarung gesperrt"
        self.assertContains(response, label)
        self.assertNotContains(response, "Neue Vereinbarung erforderlich")
        response = self.client.get(self.url, {"year": 2025, "format": "csv"})
        row = next(
            csv.DictReader(io.StringIO(response.content.decode()), delimiter=";")
        )
        self.assertEqual(
            label, next(value for key, value in row.items() if ": Status" in key)
        )
        self.assertEqual(
            "0,00", next(value for key, value in row.items() if "Buchungsrest" in key)
        )
        account.refresh_from_db()
        self.assertTrue(account.refund_requires_agreement)
        self.assertEqual(Decimal("200"), account.agreed_amount)
        self.assertEqual(0, account.agreement_revision)
