import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import override_settings

from tapir.accounts.services.keycloak_desired_state import build_desired_state
from tapir.accounts.tests.services.keycloak_fake import FakeKeycloakAdmin
from tapir.wirgarten.tests.test_utils import TapirUnitTest

ADMIN_CONFIG = {
    "SERVER_URL": "http://keycloak:8080",
    "PUBLIC_URL": "http://localhost:8080",
    "CLIENT_ID": "tapir-backend",
    "FRONTEND_CLIENT_ID": "tapir-frontend",
    "REALM_NAME": "tapir",
    "CLIENT_SECRET_KEY": "backend-secret",
}
PROVISIONER_CONFIG = {
    "CLIENT_ID": "tapir-provisioner",
    "CLIENT_SECRET_KEY": "provisioner-secret",
}
SETTINGS = dict(
    DEBUG=False,
    SITE_URL="https://tapir.example.org",
    KEYCLOAK_ADMIN_CONFIG=ADMIN_CONFIG,
    KEYCLOAK_PROVISIONER_CONFIG=PROVISIONER_CONFIG,
)

MUTATING_CALL_PREFIXES = ("create_", "update_", "assign_", "delete_")


def _mutating_calls(fake: FakeKeycloakAdmin) -> list:
    return [call for call in fake.calls if call[0].startswith(MUTATING_CALL_PREFIXES)]


@override_settings(**SETTINGS)
@patch(
    "tapir.accounts.services.keycloak_reconciler.can_authenticate",
    return_value=(True, None),
)
class TestKeycloakCommand(TapirUnitTest):
    def _run(self, *args, fake):
        out = StringIO()
        err = StringIO()
        with patch(
            "tapir.accounts.management.commands.keycloak.get_provisioner_client",
            return_value=fake,
        ):
            call_command("keycloak", *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def _run_expecting_exit(self, *args, fake, code):
        out = StringIO()
        err = StringIO()
        with patch(
            "tapir.accounts.management.commands.keycloak.get_provisioner_client",
            return_value=fake,
        ):
            with self.assertRaises(SystemExit) as context:
                call_command("keycloak", *args, stdout=out, stderr=err)
        self.assertEqual(code, context.exception.code)
        return out.getvalue(), err.getvalue()

    def test_check_converged_exits0(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        output, _ = self._run("check", fake=fake)

        self.assertIn("roles: 9/9 present", output)
        self.assertIn("superuser: 9/9 roles", output)

    def test_check_drift_exits1_andJsonReportsMissingRoles(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}
        fake.groups = []

        output, _ = self._run_expecting_exit("check", "--json", fake=fake, code=1)
        payload = json.loads(output)

        self.assertFalse(payload["ok"])
        self.assertEqual(0, payload["roles"]["present"])
        self.assertEqual(9, payload["roles"]["total"])
        messages = " ".join(
            change["message"]
            for change in payload["changes"]
            if change["section"] == "roles"
        )
        self.assertIn("coop.manage", messages)
        self.assertFalse(_mutating_calls(fake))

    def test_sync_dryRun_exits1_andDoesNotMutate(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}
        fake.groups = []

        output, _ = self._run_expecting_exit("sync", "--dry-run", fake=fake, code=1)

        self.assertIn("dry run", output)
        self.assertFalse(_mutating_calls(fake))

    def test_sync_missingRolesAndGroup_createsThem_exits0(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}
        fake.groups = []

        output, _ = self._run("sync", fake=fake)

        self.assertIn("created roles:", output)
        self.assertEqual({role.name for role in desired.realm_roles}, set(fake.roles))
        self.assertEqual(1, len(fake.calls_of("create_group")))

    def test_sync_twice_secondRunIsNoop(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}
        fake.groups = []

        self._run("sync", fake=fake)
        fake.calls.clear()

        output, _ = self._run("sync", fake=fake)

        self.assertFalse(_mutating_calls(fake))
        self.assertIn("Keycloak is in sync.", output)

    def test_check_setupError_exits2(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin(realm_error_code=404)

        _, err = self._run_expecting_exit("check", fake=fake, code=2)

        self.assertIn("realm does not exist", err)

    def test_check_jsonSetupError_exits2AndPrintsJson(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin(realm_error_code=401)

        output, _ = self._run_expecting_exit("check", "--json", fake=fake, code=2)
        payload = json.loads(output)

        self.assertFalse(payload["ok"])
        self.assertIn("could not authenticate", payload["error"])

    def test_sync_json_doesNotContainSecrets(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        output, _ = self._run("sync", "--json", fake=fake)
        payload = json.loads(output)

        self.assertTrue(payload["ok"])
        self.assertNotIn("backend-secret", output)
        self.assertNotIn("provisioner-secret", output)
