from unittest.mock import MagicMock, patch

from django.core.management import call_command

from tapir.accounts.models import TapirUser
from tapir.accounts.services.keycloak_user_manager import KeycloakUserManager
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCreateAdmin(TapirIntegrationTest):
    @patch.object(
        KeycloakUserManager, "create_keycloak_user_if_necessary", autospec=True
    )
    def test_handle_mixedCaseAddress_createsAdminWithTheNormalisedAddress(
        self, _: MagicMock
    ):
        call_command(
            "create_admin",
            first_name="Admin",
            last_name="Test",
            email=" Admin@Example.com",
            password="password",
        )

        admin = TapirUser.objects.get()
        self.assertEqual("admin@example.com", admin.email)
        self.assertEqual("admin@example.com", admin.username)
