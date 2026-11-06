import csv
import datetime
import io
from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositRefund,
)
from tapir.associations.services.association_deposit_details_provider import (
    AssociationDepositDetailsProvider,
)
from tapir.associations.services.association_deposit_export_column_provider import (
    AssociationDepositExportColumnProvider,
)
from tapir.associations.services.association_deposit_overview_provider import (
    AssociationDepositOverviewProvider,
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
from tapir.generic_exports.models import CsvExport
from tapir.generic_exports.services.csv_export_builder import CsvExportBuilder
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestDepositOverview(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime(2026, 11, 6, 12))
        self.today = datetime.date(2026, 11, 6)
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, False)
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_NAME, 'Kapital; "Garten"')
        self.admin = MemberFactory(is_superuser=True)
        self.client.force_login(self.admin)
        self.account = self.make_account(
            Decimal("200"), end_date=datetime.date(2026, 12, 31)
        )
        for index, date in enumerate(
            [
                datetime.date(2026, 11, 5),
                datetime.date(2026, 12, 5),
                datetime.date(2027, 1, 5),
                datetime.date(2027, 2, 5),
            ],
            1,
        ):
            PaymentFactory(
                association_deposit_account=self.account,
                mandate_ref__member=self.account.member,
                status=Payment.PaymentStatus.DUE,
                transaction=None,
                due_date=date,
                amount=50,
                instalment_number=index,
            )

    def make_account(self, amount, **membership_kwargs):
        member = MemberFactory()
        AssociationMembershipFactory(
            member=member, start_date=datetime.date(2026, 11, 1), **membership_kwargs
        )
        return AssociationDepositAccountFactory(
            member=member,
            agreed_amount=amount,
            effective_from=datetime.date(2026, 11, 1) if amount is not None else None,
            instalment_count=4,
        )

    def test_batched_values_match_member_details_without_creating_accounts(self):
        reduced = self.make_account(Decimal("100"))
        reduced.is_individual_agreement = True
        reduced.save()
        AssociationDepositReceiptFactory(
            account=reduced, received_on=self.today, amount=25
        )
        PaymentFactory(
            association_deposit_account=reduced,
            mandate_ref__member=reduced.member,
            status=Payment.PaymentStatus.DUE,
            transaction=None,
            amount=75,
        )
        waived = self.make_account(Decimal("0"))
        pending = self.make_account(None)
        pending.hardship_requested_at = datetime.datetime(
            2026, 11, 6, 10, tzinfo=datetime.timezone.utc
        )
        pending.save()
        refunded = self.make_account(Decimal("200"))
        AssociationDepositReceiptFactory(
            account=refunded, received_on=self.today, amount=200
        )
        AssociationDepositRefund.objects.create(
            account=refunded,
            reference="overview-return",
            amount=50,
            refunded_on=self.today,
            note="Prüfung",
        )
        refunded.refund_requires_agreement = True
        refunded.save()
        AssociationDepositReceiptFactory(
            account=refunded, received_on=datetime.date(2026, 12, 1), amount=100
        )
        rows = AssociationDepositOverviewProvider.get_rows({})
        keys = list(AssociationDepositOverviewProvider.COLUMNS)
        for account in [self.account, reduced, waived, pending, refunded]:
            with self.subTest(amount=account.agreed_amount, member=account.member_id):
                details = AssociationDepositDetailsProvider.get_deposit_details(
                    account.member, {}
                )
                self.assertEqual(
                    {key: details[key] for key in keys if key != "state_label"},
                    {
                        key: rows[account.member_id][key]
                        for key in keys
                        if key != "state_label"
                    },
                )
                self.assertEqual(details["state"], rows[account.member_id]["state"])
        self.assertEqual(100, rows[self.account.member_id]["pending_amount"])
        self.assertEqual(100, rows[self.account.member_id]["stopped_amount"])
        self.assertEqual("waived", rows[waived.member_id]["state"])
        self.assertEqual("pending", rows[pending.member_id]["state"])
        self.assertEqual(150, rows[refunded.member_id]["retained_amount"])
        self.assertEqual("individual", rows[reduced.member_id]["state"])
        self.assertIsNone(
            AssociationDepositOverviewProvider.get_row(self.admin, {})["agreed_amount"]
        )
        self.assertFalse(
            AssociationDepositAccount.objects.filter(member=self.admin).exists()
        )

    def test_four_rate_overview_batches_queries_and_reuses_request_cache(self):
        second = self.make_account(Decimal("100"))
        with CaptureQueriesContext(connection) as queries:
            cache = {}
            rows = AssociationDepositOverviewProvider.get_rows(cache)
            AssociationDepositOverviewProvider.get_row(self.account.member, cache)
            AssociationDepositOverviewProvider.get_row(second.member, cache)
        financial_queries = [
            q
            for q in queries
            if any(
                table in q["sql"]
                for table in ["associations_association", "wirgarten_payment"]
            )
        ]
        self.assertLessEqual(len(financial_queries), 5)
        self.assertEqual(100, rows[self.account.member_id]["stopped_amount"])

    def test_list_and_filtered_csv_have_same_status_and_preserve_feature_off_history(
        self,
    ):
        response = self.client.get(
            reverse("wirgarten:member_list"), {"deposit_status": "collection_stopped"}
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            [self.account.member_id], [m.pk for m in response.context["object_list"]]
        )
        self.assertContains(response, "Einzug gestoppt")
        self.assertContains(response, "Buchungsrest / Status")
        response = self.client.get(
            reverse("wirgarten:member_overview_export"),
            {"deposit_status": "collection_stopped"},
        )
        rows = list(
            csv.DictReader(io.StringIO(response.content.decode()), delimiter=";")
        )
        self.assertEqual(1, len(rows))
        expected = AssociationDepositExportColumnProvider.get_csv_row(
            self.account.member, {}
        )
        self.assertEqual(expected, {key: rows[0][key] for key in expected})

    def test_both_csv_routes_keep_unknown_empty_and_zero_explicit(self):
        waived = self.make_account(Decimal("0"))
        unknown = self.make_account(None)
        for route in [
            "wirgarten:member_overview_export",
            "wirgarten:member_list_coop_export",
        ]:
            with self.subTest(route=route):
                response = self.client.get(reverse(route))
                self.assertEqual(200, response.status_code)
                rows = list(
                    csv.DictReader(
                        io.StringIO(response.content.decode()), delimiter=";"
                    )
                )
                for account in [self.account, waived, unknown]:
                    row = next(
                        row
                        for row in rows
                        if (row.get("Email") or row.get("Mailadresse"))
                        == account.member.email
                    )
                    expected = AssociationDepositExportColumnProvider.get_csv_row(
                        account.member, {}
                    )
                    self.assertEqual(expected, {key: row[key] for key in expected})
        values = AssociationDepositExportColumnProvider.get_csv_row(unknown.member, {})
        self.assertEqual(
            "", next(value for key, value in values.items() if ": Vereinbart" in key)
        )
        values = AssociationDepositExportColumnProvider.get_csv_row(waived.member, {})
        self.assertEqual(
            "0,00",
            next(value for key, value in values.items() if ": Vereinbart" in key),
        )

    def test_deposit_fields_hidden_for_other_legal_statuses_and_without_financial_permission(
        self,
    ):
        for legal_status in [LEGAL_STATUS_COOPERATIVE, LEGAL_STATUS_COMPANY]:
            with self.subTest(legal_status=legal_status):
                self._set_parameter(
                    ParameterKeys.ORGANISATION_LEGAL_STATUS, legal_status
                )
                response = self.client.get(
                    reverse("wirgarten:member_list"), {"deposit_status": "pending"}
                )
                self.assertFalse(response.context["show_deposit_content"])
                self.assertNotIn(
                    "deposit_status", response.context["filter"].form.fields
                )
                self.assertFalse(AssociationDepositExportColumnProvider.get_columns({}))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        with patch.object(
            TapirUser,
            "has_perm",
            autospec=True,
            side_effect=lambda user, permission, obj=None: permission
            == Permission.Accounts.VIEW,
        ):
            response = self.client.get(
                reverse("wirgarten:member_list"), {"deposit_status": "pending"}
            )
            self.assertFalse(response.context["show_deposit_content"])
            self.assertNotIn("deposit_status", response.context["filter"].form.fields)
            response = self.client.get(reverse("wirgarten:member_overview_export"))
            self.assertNotIn("Buchungsrest", response.content.decode())
            self.assertEqual(
                302,
                self.client.get(
                    reverse("wirgarten:member_list_coop_export")
                ).status_code,
            )

    def test_generic_export_uses_same_current_values_with_explicit_current_labels(self):
        columns = AssociationDepositExportColumnProvider.get_columns({})
        available = MemberColumnProvider.get_member_columns()
        self.assertTrue(
            all(column.id in [c.id for c in available] for column in columns)
        )
        export = CsvExport(
            name="Einlage",
            export_segment_id="members.all",
            separator=";",
            locale="de_DE.UTF-8",
            column_ids=["member_email_address"] + [c.id for c in columns],
            custom_column_names=["Email"] + [c.display_name for c in columns],
        )
        text = CsvExportBuilder.build_csv_export_string(
            export, datetime.datetime(2025, 1, 1)
        )
        rows = list(csv.DictReader(io.StringIO(text), delimiter=";"))
        # Historical segment selection is separate from explicitly current deposit columns.
        self.assertEqual([], rows)
        text = CsvExportBuilder.build_csv_export_string(
            export, datetime.datetime(2026, 11, 6)
        )
        row = next(
            row
            for row in csv.DictReader(io.StringIO(text), delimiter=";")
            if row["Email"] == self.account.member.email
        )
        expected = AssociationDepositOverviewProvider.get_row(self.account.member, {})
        for key, label in AssociationDepositOverviewProvider.COLUMNS.items():
            column = next(c for c in columns if c.id == f"association_deposit_{key}")
            self.assertIn("aktueller Stand", column.display_name)
            if isinstance(expected[key], Decimal):
                self.assertEqual(expected[key], Decimal(row[column.display_name]))
            else:
                self.assertEqual(expected[key] or "", row[column.display_name])

    def test_minimum_filter_respects_regular_minimum_individual_terms_and_no_backfill(
        self,
    ):
        covered_extra = self.make_account(Decimal("250"))
        covered_old = self.make_account(Decimal("100"))
        reduced_paid = self.make_account(Decimal("100"))
        reduced_open = self.make_account(Decimal("100"))
        waived = self.make_account(Decimal("0"))
        pending = self.make_account(None)
        for account, amount in [
            (covered_extra, 200),
            (covered_old, 100),
            (reduced_paid, 100),
            (reduced_open, 25),
        ]:
            AssociationDepositReceiptFactory(
                account=account, amount=amount, received_on=self.today
            )
        for account in [reduced_paid, reduced_open, waived]:
            account.is_individual_agreement = True
            account.save()
        expected = {self.account.member_id, reduced_open.member_id}
        response = self.client.get(
            reverse("wirgarten:member_list"), {"deposit_status": "minimum_outstanding"}
        )
        self.assertEqual(
            expected, {member.pk for member in response.context["object_list"]}
        )
        response = self.client.get(
            reverse("wirgarten:member_overview_export"),
            {"deposit_status": "minimum_outstanding"},
        )
        rows = list(
            csv.DictReader(io.StringIO(response.content.decode()), delimiter=";")
        )
        self.assertEqual(
            {self.account.member.email, reduced_open.member.email},
            {row["Email"] for row in rows},
        )

    def test_filtered_csv_requires_member_list_permission_on_direct_requests(self):
        url = reverse("wirgarten:member_overview_export")
        self.client.logout()
        self.assertEqual(302, self.client.get(url).status_code)
        self.client.force_login(self.account.member)
        self.assertEqual(403, self.client.get(url).status_code)
        with patch.object(
            TapirUser,
            "has_perm",
            autospec=True,
            side_effect=lambda user, permission, obj=None: permission
            == Permission.Coop.VIEW,
        ):
            self.assertEqual(403, self.client.get(url).status_code)

    def test_returned_old_deposit_requires_consent_instead_of_minimum_followup(self):
        account = self.make_account(Decimal("200"), end_date=datetime.date(2026, 11, 5))
        AssociationDepositReceiptFactory(
            account=account, amount=200, received_on=self.today
        )
        AssociationDepositRefund.objects.create(
            account=account,
            amount=200,
            refunded_on=self.today,
            reference="completed-return",
            note="Bankseitig zurückgezahlt",
        )
        account.refund_requires_agreement = True
        account.save()
        for start in [None, datetime.date(2027, 3, 1), self.today]:
            with self.subTest(reentry=start):
                if start is not None:
                    AssociationMembershipFactory(
                        member=account.member, start_date=start
                    )
                response = self.client.get(
                    reverse("wirgarten:member_list"),
                    {"deposit_status": "minimum_outstanding"},
                )
                self.assertNotIn(
                    account.member_id, [m.pk for m in response.context["object_list"]]
                )
                row = AssociationDepositOverviewProvider.get_row(account.member, {})
                self.assertEqual(200, row["agreed_amount"])
                self.assertEqual(0, row["retained_amount"])
                self.assertEqual("agreement_required", row["state"])
                response = self.client.get(
                    reverse("wirgarten:member_overview_export"),
                    {"deposit_status": "minimum_outstanding"},
                )
                self.assertNotIn(account.member.email, response.content.decode())
        self.assertEqual(200, account.refunds.get().amount)
