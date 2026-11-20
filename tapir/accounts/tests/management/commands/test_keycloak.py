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

    def test_check_invalidConfig_exits2AndNamesEnvVar(self, _can_authenticate):
        out = StringIO()
        err = StringIO()
        with override_settings(
            KEYCLOAK_ADMIN_CONFIG={**ADMIN_CONFIG, "SERVER_URL": "keycloak:8080"}
        ):
            with patch(
                "tapir.accounts.management.commands.keycloak.get_provisioner_client"
            ) as get_client:
                with self.assertRaises(SystemExit) as context:
                    call_command("keycloak", "check", stdout=out, stderr=err)

        self.assertEqual(2, context.exception.code)
        self.assertIn("KEYCLOAK_ADMIN_SERVER_URL", err.getvalue())
        get_client.assert_not_called()

    def test_check_jsonInvalidConfig_exits2AndReturnsConfig(self, _can_authenticate):
        out = StringIO()
        err = StringIO()
        with override_settings(
            KEYCLOAK_ADMIN_CONFIG={**ADMIN_CONFIG, "SERVER_URL": "keycloak:8080"}
        ):
            with patch(
                "tapir.accounts.management.commands.keycloak.get_provisioner_client"
            ):
                with self.assertRaises(SystemExit) as context:
                    call_command("keycloak", "check", "--json", stdout=out, stderr=err)

        payload = json.loads(out.getvalue())
        self.assertEqual(2, context.exception.code)
        self.assertFalse(payload["ok"])
        self.assertIn("KEYCLOAK_ADMIN_SERVER_URL", payload["error"])
        self.assertEqual("keycloak:8080", payload["config"]["server_url"])

    def test_check_json_includesConfigWithoutSecrets(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        output, _ = self._run("check", "--json", fake=fake)
        payload = json.loads(output)

        self.assertEqual("http://keycloak:8080", payload["config"]["server_url"])
        self.assertEqual(
            "tapir-provisioner", payload["config"]["provisioner_client_id"]
        )
        self.assertTrue(
            any(
                "KEYCLOAK_ADMIN_SERVER_URL" in warning
                for warning in payload["warnings"]
            )
        )
        self.assertNotIn("backend-secret", output)
        self.assertNotIn("provisioner-secret", output)

    def test_check_localDefaults_reportsConfigWarnings(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        output, _ = self._run("check", fake=fake)

        self.assertIn("[warning] KEYCLOAK_ADMIN_SERVER_URL", output)
        self.assertIn("[warning] KEYCLOAK_PUBLIC_URL", output)

    def test_check_printsTargetAndProvisionerClientId(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        output, _ = self._run("check", fake=fake)

        self.assertIn("target:", output)
        self.assertIn("public=http://localhost:8080", output)
        self.assertIn("tapir-provisioner", output)

    def test_check_converged_exits0(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        output, _ = self._run("check", fake=fake)

        self.assertIn("Checks:", output)
        self.assertIn("[ok] realm settings", output)
        self.assertIn("[ok] realm roles", output)
        self.assertIn("9/9", output)
        self.assertIn("[ok] superuser group", output)
        self.assertIn("[ok] clients", output)
        self.assertIn("[ok] default client scopes", output)
        self.assertIn("[ok] client role scope mappings", output)
        self.assertIn("[ok] service account roles", output)
        self.assertIn("[ok] runtime client secret", output)
        self.assertIn("[ok] SMTP server", output)

    def test_check_json_includesChecks(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        output, _ = self._run("check", "--json", fake=fake)
        payload = json.loads(output)
        checks = {check["description"]: check for check in payload["checks"]}

        self.assertEqual("warning", checks["configuration"]["status"])
        self.assertEqual("ok", checks["realm settings"]["status"])
        self.assertEqual("ok", checks["realm roles"]["status"])
        self.assertEqual("ok", checks["superuser group"]["status"])
        self.assertEqual("ok", checks["clients"]["status"])
        self.assertEqual("ok", checks["default client scopes"]["status"])
        self.assertEqual("ok", checks["client role scope mappings"]["status"])
        self.assertEqual("ok", checks["service account roles"]["status"])
        self.assertEqual("ok", checks["runtime client secret"]["status"])
        self.assertEqual("ok", checks["SMTP server"]["status"])
        self.assertNotIn("backend-secret", output)
        self.assertNotIn("provisioner-secret", output)

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

    def test_check_drift_jsonReportsErrorCheck(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}
        fake.groups = []

        output, _ = self._run_expecting_exit("check", "--json", fake=fake, code=1)
        payload = json.loads(output)
        checks = {check["description"]: check for check in payload["checks"]}

        self.assertEqual("error", checks["realm roles"]["status"])
        self.assertEqual("error", checks["superuser group"]["status"])
        self.assertIn("0/9", checks["realm roles"]["details"])

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

    def test_sync_jsonUsesVerificationChecks(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}
        fake.groups = []

        output, _ = self._run("sync", "--json", fake=fake)
        payload = json.loads(output)
        checks = {check["description"]: check for check in payload["checks"]}

        self.assertTrue(payload["ok"])
        self.assertEqual("ok", checks["realm roles"]["status"])
        self.assertEqual("ok", checks["superuser group"]["status"])
        self.assertTrue(any(change["fixed"] for change in payload["changes"]))

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
