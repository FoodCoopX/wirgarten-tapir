import datetime
from io import StringIO

from django.core.management.base import OutputWrapper
from django.utils import timezone

from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.member_importer import MemberImporter
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberImporter(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def import_row(self, row):
        return MemberImporter.import_member(
            row=row,
            update_existing=True,
            dry_run=False,
            stdout=OutputWrapper(StringIO()),
        )

    def test_importMember_blankEmail_rejectsBeforeChangingMember(self):
        member = MemberFactory.create(member_no=101, first_name="Mika")

        with self.assertRaisesMessage(TapirDataImportException, "E-Mail-Adresse fehlt"):
            self.import_row({"Nr": "101", "Vorname": "Changed", "Mailadresse": " "})

        member.refresh_from_db()
        self.assertEqual("Mika", member.first_name)
        self.mock_keycloak_client.update_user.assert_not_called()

    def test_importMember_invalidEmail_createsNoMember(self):
        with self.assertRaisesMessage(
            TapirDataImportException, "Ungültige E-Mail-Adresse"
        ):
            self.import_row({"Nr": "101", "Mailadresse": "invalid-address"})

        self.assertFalse(Member.objects.exists())

    def test_importMember_validEmail_normalisesAddress(self):
        self.import_row({"Nr": "101", "Mailadresse": " MIKA@EXAMPLE.TEST "})

        self.assertEqual("mika@example.test", Member.objects.get().email)

    def test_importMember_missingConsent_preservesRecordedDates(self):
        recorded = timezone.make_aware(datetime.datetime(2024, 3, 1, 12))
        member = MemberFactory.create(
            member_no=101, sepa_consent=recorded, privacy_consent=recorded
        )

        self.import_row(
            {
                "Nr": "101",
                "Mailadresse": member.email,
                "consent_sepa": "",
                "privacy_consent": "",
            }
        )

        member.refresh_from_db()
        self.assertEqual(recorded, member.sepa_consent)
        self.assertEqual(recorded, member.privacy_consent)

    def test_importMember_missingConsent_leavesNewDatesUnknown(self):
        self.import_row(
            {
                "Nr": "101",
                "Mailadresse": "mika@example.test",
                "IBAN": "DE89370400440532013000",
            }
        )

        member = Member.objects.get()
        self.assertIsNone(member.sepa_consent)
        self.assertIsNone(member.privacy_consent)

    def test_importMember_explicitConsent_usesProvidedDates(self):
        self.import_row(
            {
                "Nr": "101",
                "Mailadresse": "mika@example.test",
                "consent_sepa": "01.03.2024",
                "privacy_consent": "02.03.2024",
            }
        )

        member = Member.objects.get()
        self.assertEqual(
            datetime.date(2024, 3, 1), timezone.localdate(member.sepa_consent)
        )
        self.assertEqual(
            datetime.date(2024, 3, 2), timezone.localdate(member.privacy_consent)
        )

    def test_importMember_invalidConsent_rejectsBeforeChangingMember(self):
        member = MemberFactory.create(member_no=101, first_name="Mika")

        for column in ("consent_sepa", "privacy_consent"):
            with self.subTest(column=column):
                with self.assertRaisesMessage(
                    TapirDataImportException, f"{column}: Ungültiges Datum"
                ):
                    self.import_row(
                        {
                            "Nr": "101",
                            "Mailadresse": member.email,
                            "Vorname": "Changed",
                            column: "invalid",
                        }
                    )

                member.refresh_from_db()
                self.assertEqual("Mika", member.first_name)
