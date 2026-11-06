from tempfile import NamedTemporaryFile
from unittest.mock import patch

from django.core.management import CommandError, call_command

from tapir.accounts.services.keycloak_user_delete_service import (
    KeycloakUserDeleteService,
)
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositReceipt,
)
from tapir.associations.services.association_deposit_import_deletion_validator import (
    AssociationDepositImportDeletionValidator,
)
from tapir.associations.tests.factories import AssociationDepositReceiptFactory
from tapir.log.models import LogEntry
from tapir.wirgarten.models import (
    Member,
    Payment,
    PaymentTransaction,
    MandateReference,
    ExportedFile,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import PaymentFactory, MandateReferenceFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDepositImportDeletionPreflight(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def create_existing_history(self):
        receipt = AssociationDepositReceiptFactory()
        PaymentFactory(
            mandate_ref=MandateReferenceFactory(member=receipt.account.member)
        )

    def snapshot_history(self):
        return {
            model._meta.label: list(model.objects.order_by("pk").values())
            for model in [
                Member,
                AssociationDepositAccount,
                AssociationDepositReceipt,
                Payment,
                PaymentTransaction,
                MandateReference,
                LogEntry,
                ExportedFile,
            ]
        }

    def assert_deletion_is_rejected_before_side_effects(self, *arguments):
        self.create_existing_history()
        before = self.snapshot_history()
        with patch.object(
            KeycloakUserDeleteService, "delete_user_if_exists"
        ) as delete_keycloak, patch(
            "django.db.models.query.QuerySet.delete"
        ) as delete_rows, patch(
            "builtins.input"
        ) as confirm:
            with self.assertRaisesMessage(CommandError, "Einlagenkonten"):
                call_command("import-data", *arguments)
            delete_keycloak.assert_not_called()
            delete_rows.assert_not_called()
            confirm.assert_not_called()
        self.mock_keycloak_client.delete_user.assert_not_called()
        self.assertEqual(before, self.snapshot_history())

    def test_reset_all_is_rejected_before_confirmation_database_and_keycloak_deletion(
        self,
    ):
        self.assert_deletion_is_rejected_before_side_effects("--reset-all")

    def test_member_delete_all_is_rejected_before_database_and_keycloak_deletion(self):
        with NamedTemporaryFile(mode="w", suffix=".csv") as csv_file:
            csv_file.write("Mitgliedernummer\n")
            csv_file.flush()
            self.assert_deletion_is_rejected_before_side_effects(
                "--type", "members", "--file", csv_file.name, "--delete-all"
            )

    def test_non_destructive_imports_remain_available_with_existing_account(self):
        self.create_existing_history()
        before = self.snapshot_history()
        with NamedTemporaryFile(mode="w", suffix=".csv") as csv_file:
            csv_file.write("Mitgliedernummer\n")
            csv_file.flush()
            with patch.object(
                KeycloakUserDeleteService, "delete_user_if_exists"
            ) as delete_keycloak:
                for kind in ["members", "shares", "subscriptions"]:
                    with self.subTest(kind=kind):
                        call_command(
                            "import-data", "--type", kind, "--file", csv_file.name
                        )
                delete_keycloak.assert_not_called()
        self.assertEqual(before, self.snapshot_history())

    def test_preflight_allows_database_without_deposit_accounts(self):
        self.assertFalse(AssociationDepositAccount.objects.exists())
        AssociationDepositImportDeletionValidator.validate_member_reset_is_safe(
            cache={}
        )
