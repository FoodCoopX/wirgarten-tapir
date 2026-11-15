import os
from unittest.mock import patch

from django.core.management import call_command

from tapir.accounts.models import TapirUser
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCreateAdmin(TapirIntegrationTest):
    def test_handle_noArgumentsAndEnvironmentVariablesSet_createsSuperuserWithEnvironmentValues(
        self,
    ):
        environment = {
            "TAPIR_ADMIN_FIRST_NAME": "Environment",
            "TAPIR_ADMIN_LAST_NAME": "Admin",
            "TAPIR_ADMIN_EMAIL": "environment@example.com",
            "TAPIR_ADMIN_PASSWORD": "secret",
        }

        with patch.dict(os.environ, environment):
            call_command("create_admin")

        admin = TapirUser.objects.get(email="environment@example.com")
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertEqual("Environment", admin.first_name)
        self.assertEqual("Admin", admin.last_name)
        self.assertEqual("environment@example.com", admin.email)

    def test_handle_userWithSameEmailAlreadyExists_skipsCreation(self):
        call_command("create_admin", email="existing@example.com", password="secret")
        user_count = TapirUser.objects.count()
        keycloak_create_user = self.mock_keycloak_client.create_user
        keycloak_create_user.reset_mock()

        call_command("create_admin", email="EXISTING@example.com", password="different")

        self.assertEqual(user_count, TapirUser.objects.count())
        keycloak_create_user.assert_not_called()
