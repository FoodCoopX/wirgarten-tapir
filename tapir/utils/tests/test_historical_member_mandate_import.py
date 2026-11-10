import csv
import datetime
import io
import tempfile
from unittest.mock import patch
from xml.etree import ElementTree

from django.core import mail
from django.core.management import call_command, CommandError

from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.pain_008_xml_string_generator import (
    Pain008XmlStringGenerator,
)
from tapir.payments.services.payment_export_builder import PaymentExportBuilder
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.models import MandateReference, Member, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestHistoricalMemberMandateImport(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def import_row(self, *options, **changes):
        row = {
            "Nr": "9001",
            "Vorname": "Erika",
            "Nachname": "Muster",
            "Mailadresse": "erika@example.test",
            "IBAN": "NL88ABNA2011060885",
            "Kontoinhaber": "Erika Muster",
            "consent_sepa": "2021-07-08",
            "Mandatsreferenz": "Alt-9001",
            **changes,
        }
        stdout, stderr = io.StringIO(), io.StringIO()
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline=""
        ) as file:
            writer = csv.DictWriter(file, fieldnames=list(row), delimiter=";")
            writer.writeheader()
            writer.writerow(row)
            file.flush()
            call_command(
                "import-data",
                "--type",
                "members",
                "--file",
                file.name,
                "--update",
                "yes",
                *options,
                stdout=stdout,
                stderr=stderr,
            )
        return stdout.getvalue(), stderr.getvalue()

    def test_dry_run_then_import_and_retry_preserve_date_reference_and_account(self):
        with patch.object(KeycloakUserManager, "get_keycloak_client") as keycloak:
            self.assertEqual("", self.import_row("--dry-run")[1])
            self.assertFalse(Member.objects.filter(member_no=9001).exists())
            self.assertFalse(MandateReference.objects.filter(pk="Alt-9001").exists())

            self.assertEqual("", self.import_row()[1])
            member = Member.objects.get(member_no=9001)
            member.keycloak_id = "synthetic-keycloak-id"
            member.save(update_fields=["keycloak_id"])
            self.assertEqual(
                "",
                self.import_row(Mailadresse="ERIKA@example.test", Vorname="Erika M.")[
                    1
                ],
            )
            self.assertIn("Skipped: 1", self.import_row(Vorname="Erika M.")[0])
            keycloak.assert_not_called()

        member.refresh_from_db()
        mandate = MandateReferenceProvider.get_or_create_mandate_reference(member, {})
        self.assertEqual("Alt-9001", mandate.ref)
        self.assertEqual(datetime.date(2021, 7, 8), mandate.start_ts.date())
        self.assertEqual(mandate.start_ts, member.sepa_consent)
        self.assertEqual("Erika M.", member.first_name)
        self.assertEqual("synthetic-keycloak-id", member.keycloak_id)
        self.assertEqual(1, MandateReference.objects.filter(member=member).count())
        self.assertFalse(Payment.objects.filter(mandate_ref=mandate).exists())
        self.assertEqual([], mail.outbox)

    def test_imported_date_and_reference_are_used_in_both_payment_formats(self):
        self.assertEqual("", self.import_row()[1])
        member = Member.objects.get(member_no=9001)
        cache = {}
        for key, value in {
            ParameterKeys.SITE_NAME: "Test-Verein",
            ParameterKeys.PAYMENT_ORGANISATION_IBAN: "DE60500105172436256838",
            ParameterKeys.PAYMENT_ORGANISATION_BIC: "",
            ParameterKeys.PAYMENT_CREDITOR_IDENTIFIER: "Test-creditor-id",
            ParameterKeys.PAYMENT_INTENDED_USE_ENABLE_CUSTOM: False,
            ParameterKeys.PAYMENT_DUE_DAY: 15,
        }.items():
            mock_parameter_value(cache=cache, key=key, value=value)
        payment = PaymentFactory.build(
            mandate_ref=MandateReferenceProvider.get_or_create_mandate_reference(
                member, cache
            )
        )
        csv_text = PaymentExportBuilder.build_csv_string([payment], True, cache)
        row = next(
            csv.DictReader(
                io.StringIO("\n".join(csv_text.splitlines()[2:])), delimiter=";"
            )
        )
        self.assertEqual("Alt-9001", row[PaymentExportBuilder.KEY_MANDATE_REF])
        self.assertEqual("08.07.2021", row[PaymentExportBuilder.KEY_MANDATE_DATE])

        xml = ElementTree.fromstring(
            Pain008XmlStringGenerator.build_xml_string(
                [payment], cache, collection_date=datetime.date(2026, 11, 15)
            )
        )
        self.assertEqual("Alt-9001", xml.findtext(".//{*}MndtId"))
        self.assertEqual("2021-07-08", xml.findtext(".//{*}DtOfSgntr"))
        self.assertFalse(Payment.objects.filter(mandate_ref__member=member).exists())
        self.assertEqual([], mail.outbox)

    def test_email_and_member_number_conflicts_do_not_create_or_change_accounts(self):
        existing = MemberFactory(member_no=9001, email="existing@example.test")
        other = MemberFactory(member_no=9002, email="erika@example.test")
        for changes in ({}, {"Nr": "9003"}, {"Mailadresse": "new@example.test"}):
            with self.subTest(changes=changes):
                self.assertIn("nicht eindeutig", self.import_row(**changes)[1])
        existing.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual("existing@example.test", existing.email)
        self.assertEqual("erika@example.test", other.email)
        self.assertFalse(Member.objects.filter(member_no=9003).exists())
        self.assertFalse(MandateReference.objects.filter(pk="Alt-9001").exists())

    def test_existing_reference_is_never_reassigned_or_redated(self):
        self.assertEqual("", self.import_row()[1])
        self.assertIn(
            "bereits für ein anderes Konto oder Datum",
            self.import_row(consent_sepa="2021-07-09")[1],
        )
        self.assertIn(
            "bereits für ein anderes Konto oder Datum",
            self.import_row(Nr="9002", Mailadresse="other@example.test")[1],
        )
        self.assertIn(
            "bereits eine andere Mandatsreferenz",
            self.import_row(Mandatsreferenz="Different-9001")[1],
        )
        member = Member.objects.get(member_no=9001)
        mandate = MandateReference.objects.get(pk="Alt-9001")
        self.assertEqual(member.pk, mandate.member_id)
        self.assertEqual(datetime.date(2021, 7, 8), mandate.start_ts.date())
        self.assertEqual(mandate.start_ts, member.sepa_consent)
        self.assertFalse(Member.objects.filter(member_no=9002).exists())

    def test_incomplete_mandate_and_destructive_import_are_rejected(self):
        self.assertIn("gemeinsam angeben", self.import_row(consent_sepa="")[1])
        with self.assertRaisesMessage(CommandError, "kein --delete-all"):
            self.import_row("--delete-all")
        self.assertFalse(Member.objects.filter(member_no=9001).exists())
