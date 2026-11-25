from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from tapir.accounts.models import TapirUser
from tapir.associations.models import AssociationMembershipCreatedLogEntry
from tapir.associations.tests.factories import AssociationMembershipTypeFactory
from tapir.log.models import LogEntry
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.models import MemberImportedLogEntry
from tapir.utils.services.member_import_service import MemberImportService
from tapir.utils.services.tabular_file_reader import TabularData
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class TestMemberImportService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.admin = TapirUser.objects.create(
            username="import-admin", email="admin@example.test"
        )

    def upload(self, rows="101;mika@example.test\n"):
        return SimpleUploadedFile("members.csv", ("Nr;Mailadresse\n" + rows).encode())

    def test_preview_validMember_rollsBackWrites(self):
        token, result = MemberImportService.preview(self.upload(), self.admin.pk)

        self.assertTrue(result.can_apply)
        self.assertIsNotNone(token)
        self.assertFalse(Member.objects.exists())
        self.assertFalse(LogEntry.objects.exists())
        self.mock_keycloak_client.create_user.assert_not_called()
        self.mock_keycloak_client.update_user.assert_not_called()

    def test_apply_validPreview_createsMemberOnce(self):
        token, _ = MemberImportService.preview(self.upload(), self.admin.pk)

        result = MemberImportService.apply(self.admin.pk, token)

        self.assertTrue(result.applied)
        with self.assertRaises(TapirDataImportException):
            MemberImportService.apply(self.admin.pk, token)
        self.assertEqual(1, Member.objects.count())

    def test_apply_newAssociationMember_attributesImportLogsToAdmin(self):
        membership_type = AssociationMembershipTypeFactory.create(name="Standard")
        file = SimpleUploadedFile(
            "members.csv",
            (
                "Nr;Mailadresse;Vereinsmitgliedschafttyp;Vereinsmitgliedschaft Start_Date\n"
                f"101;mika@example.test;{membership_type.name};01.03.2024\n"
            ).encode(),
        )
        token, preview = MemberImportService.preview(file, self.admin.pk)
        self.assertTrue(preview.can_apply)
        self.assertFalse(LogEntry.objects.exists())

        result = MemberImportService.apply(self.admin.pk, token)

        self.assertTrue(result.applied)
        member = Member.objects.get(member_no=101)
        self.assertEqual(
            self.admin, MemberImportedLogEntry.objects.get(user=member).actor
        )
        self.assertEqual(
            self.admin,
            AssociationMembershipCreatedLogEntry.objects.get(user=member).actor,
        )
        self.assertFalse(
            LogEntry.objects.filter(user=member).exclude(actor=self.admin).exists()
        )

    def test_apply_otherAdmin_cannotConsumeUpload(self):
        token, _ = MemberImportService.preview(self.upload(), self.admin.pk)

        with self.assertRaises(TapirDataImportException):
            MemberImportService.apply("other-admin", token)

        self.assertTrue(MemberImportService.apply(self.admin.pk, token).applied)

    def test_run_invalidRow_rollsBackWholeFile(self):
        data = TabularData(
            ["Nr", "Mailadresse"],
            [
                {"Nr": "101", "Mailadresse": "mika@example.test"},
                {"Nr": "invalid", "Mailadresse": "other@example.test"},
            ],
        )

        result = MemberImportService.run(data, dry_run=False, actor_id=self.admin.pk)

        self.assertFalse(result.applied)
        self.assertEqual(3, result.rows[1].line)
        self.assertTrue(result.rows[1].error)
        self.assertFalse(Member.objects.exists())
        self.assertFalse(LogEntry.objects.exists())

    def test_apply_repeatedFile_preservesExistingMember(self):
        member = MemberFactory.create(member_no=101, email="original@example.test")
        historical_log = MemberImportedLogEntry().populate(
            model=member, user=member, actor=None
        )
        historical_log.save()
        token, result = MemberImportService.preview(self.upload(), self.admin.pk)
        self.assertIn("übersprungen", result.rows[0].status)

        MemberImportService.apply(self.admin.pk, token)

        member.refresh_from_db()
        self.assertEqual("original@example.test", member.email)
        historical_log.refresh_from_db()
        self.assertIsNone(historical_log.actor)
        self.assertEqual(1, Member.objects.count())
        self.mock_keycloak_client.update_user.assert_not_called()

    def test_run_existingLogin_rollsBackFileWithoutExternalChanges(self):
        user = TapirUser.objects.create(
            email="MIKA@EXAMPLE.TEST", username="mika", keycloak_id="existing-account"
        )
        log_count = LogEntry.objects.count()
        data = TabularData(
            ["Nr", "Mailadresse"],
            [
                {"Nr": "101", "Mailadresse": "another@example.test"},
                {"Nr": "102", "Mailadresse": "mika@example.test"},
            ],
        )

        result = MemberImportService.run(data, dry_run=False, actor_id=self.admin.pk)

        self.assertFalse(result.applied)
        self.assertIn("Benutzerkonto ohne Mitgliedschaft", result.rows[1].error)
        self.assertFalse(Member.objects.exists())
        self.assertEqual(log_count, LogEntry.objects.count())
        user.refresh_from_db()
        self.assertEqual("MIKA@EXAMPLE.TEST", user.email)
        self.mock_keycloak_client.create_user.assert_not_called()
        self.mock_keycloak_client.update_user.assert_not_called()

    def test_run_sharedEmailWithExistingLogin_usesImporterResolvedAddress(self):
        member = MemberFactory.create(member_no=100, email="mika@example.test")
        TapirUser.objects.create(
            email="MIKA+1@EXAMPLE.TEST",
            username="mika-other",
            keycloak_id="existing-account",
        )
        data = TabularData(
            ["Nr", "Mailadresse"],
            [
                {"Nr": "101", "Mailadresse": member.email},
            ],
        )

        result = MemberImportService.run(data, dry_run=False, actor_id=self.admin.pk)

        self.assertFalse(result.applied)
        self.assertIn("Benutzerkonto ohne Mitgliedschaft", result.rows[0].error)
        self.assertEqual(1, Member.objects.count())
        self.mock_keycloak_client.update_user.assert_not_called()

    def test_run_unknownColumn_rejectsBeforeWriting(self):
        result = MemberImportService.run(
            TabularData(["Nr", "Mailadresse", "Typo"], []),
            dry_run=False,
            actor_id=self.admin.pk,
        )

        self.assertFalse(result.can_apply)
        self.assertIn("Unbekannte Spalten", result.errors[0])
        self.assertFalse(Member.objects.exists())

    def test_template_downloadedExample_canBePreviewed(self):
        file = SimpleUploadedFile(
            "template.csv", MemberImportService.build_template().encode()
        )

        _, result = MemberImportService.preview(file, self.admin.pk)

        self.assertTrue(result.can_apply, result)
        self.assertFalse(Member.objects.exists())
