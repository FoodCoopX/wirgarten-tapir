from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

from django.test import override_settings

from tapir.accounts.services.keycloak_client_factory import (
    REASON_AUTHENTICATION_FAILED,
    REASON_MISSING_ADMIN_API_SCOPE,
)
from tapir.accounts.services.keycloak_desired_state import (
    ADMIN_API_CLIENT_SCOPE,
    build_desired_state,
)
from tapir.accounts.services.keycloak_reconciler import (
    ADMIN_API_SCOPE_MISSING_MESSAGE,
    KeycloakReconciler,
    KeycloakSetupError,
)
from tapir.accounts.tests.services.keycloak_fake import FakeKeycloakAdmin
from tapir.accounts.tests.services.test_keycloak_user_profile import (
    COMPLEX_USER_PROFILE_EXAMPLE,
)
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
    KEYCLOAK_USERNAME_SOURCE="email",
    KEYCLOAK_USERNAME_FORMAT="raw",
    KEYCLOAK_REGISTRATION_EMAIL_AS_USERNAME=True,
    KEYCLOAK_EDIT_USERNAME_ALLOWED=False,
    KEYCLOAK_VERIFY_EMAIL=True,
    KEYCLOAK_USER_PROFILE_MANAGED=False,
    KEYCLOAK_USER_PROFILE_FILE="",
    KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[],
)

EXAMPLE_PROFILE_FILE = "examples/keycloak-userprofile.json"

MUTATING_CALL_PREFIXES = ("create_", "update_", "assign_", "add_", "delete_")


def mutating_calls(fake: FakeKeycloakAdmin) -> list:
    return [call for call in fake.calls if call[0].startswith(MUTATING_CALL_PREFIXES)]


@override_settings(**SETTINGS)
@patch(
    "tapir.accounts.services.keycloak_reconciler.can_authenticate",
    return_value=(True, None),
)
class TestKeycloakReconciler(TapirUnitTest):
    def test_reconcile_converged_isClean(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertFalse(result.has_errors)
        self.assertEqual(9, result.role_count)
        self.assertEqual(9, result.role_present)
        self.assertEqual(9, result.group_role_count)
        self.assertEqual(9, result.group_role_present)
        self.assertFalse(mutating_calls(fake))

    def test_reconcile_reorderedClientLists_isClean(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        for client in fake.clients:
            for key in ("redirectUris", "webOrigins"):
                if key in client:
                    client[key] = list(reversed(client[key]))

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertFalse(result.has_errors)
        self.assertFalse(mutating_calls(fake))

    def test_reconcile_missingRoles_reportsEveryMissingRole(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        role_errors = [
            change
            for change in result.changes
            if change.section == "roles" and change.level == "error"
        ]
        self.assertEqual(9, len(role_errors))
        messages = " ".join(change.message for change in role_errors)
        for role in desired.realm_roles:
            self.assertIn(role.name, messages)
        self.assertIn("coop.manage", messages)
        self.assertFalse(mutating_calls(fake))

    def test_reconcile_syncCreatesAllMissingRoles(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        create_calls = fake.calls_of("create_realm_role")
        self.assertEqual(9, len(create_calls))
        for role in desired.realm_roles:
            self.assertIn(role.name, fake.roles)
        self.assertFalse(fake.calls_of("delete_realm_role"))

    def test_reconcile_missingGroup_createsItAndAssignsAllRoles(
        self, _can_authenticate
    ):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.groups = []

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        self.assertEqual(1, len(fake.calls_of("create_group")))
        assign_calls = fake.calls_of("assign_group_realm_roles")
        self.assertEqual(1, len(assign_calls))
        assigned_names = {role["name"] for role in assign_calls[0][2]}
        self.assertEqual({role.name for role in desired.realm_roles}, assigned_names)

    def test_reconcile_groupWithSomeRoles_assignsOnlyMissingRoles(
        self, _can_authenticate
    ):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.groups[0]["realmRoles"] = ["coop.view", "coop.manage"]

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        assign_calls = fake.calls_of("assign_group_realm_roles")
        self.assertEqual(1, len(assign_calls))
        assigned_names = {role["name"] for role in assign_calls[0][2]}
        self.assertEqual(7, len(assigned_names))
        self.assertNotIn("coop.view", assigned_names)
        self.assertNotIn("coop.manage", assigned_names)

    def test_reconcile_convergedSecondRun_mutatesNothing(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        reconciler = KeycloakReconciler(fake, desired)

        reconciler.reconcile(dry_run=False)
        fake.calls.clear()
        result = reconciler.reconcile(dry_run=False)

        self.assertFalse(result.has_errors)
        self.assertFalse(mutating_calls(fake))

    def test_reconcile_checkWithDrift_doesNotMutate(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}
        fake.groups = []
        fake.clients = []

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertTrue(result.has_errors)
        self.assertFalse(mutating_calls(fake))

    def test_reconcile_wrongRoleFlags_reportsAndFixes(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles["coop.manage"]["composite"] = True

        check = KeycloakReconciler(fake, desired).reconcile(dry_run=True)
        self.assertTrue(
            any(
                change.section == "roles" and "coop.manage" in change.message
                for change in check.changes
            )
        )
        self.assertTrue(fake.roles["coop.manage"]["composite"])

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)
        self.assertFalse(fake.roles["coop.manage"]["composite"])
        self.assertEqual(1, len(fake.calls_of("update_realm_role")))

    def test_reconcile_extraGroupRole_warnsAndDoesNotDelete(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles["extra.role"] = {
            "id": "role-extra.role",
            "name": "extra.role",
            "clientRole": False,
            "composite": False,
        }
        fake.groups[0]["realmRoles"].append("extra.role")

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertTrue(
            any(
                change.level == "warning" and "extra.role" in change.message
                for change in result.changes
            )
        )
        self.assertFalse(fake.calls_of("delete_group_realm_roles"))

    def test_reconcile_realmDrift_updatesOnlyTheManagedKeys(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.realm["enabled"] = False

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        update_calls = fake.calls_of("update_realm")
        self.assertEqual(1, len(update_calls))
        self.assertEqual({"enabled": True}, update_calls[0][2])
        self.assertTrue(fake.realm["enabled"])

    def test_reconcile_clientDrift_updatesTheClient(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        backend = next(
            client for client in fake.clients if client["clientId"] == "tapir-backend"
        )
        backend["directAccessGrantsEnabled"] = True

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        update_calls = fake.calls_of("update_client")
        self.assertEqual(1, len(update_calls))
        self.assertFalse(update_calls[0][2]["directAccessGrantsEnabled"])

    def test_reconcile_clientFullScopeAllowedDrift_updatesTheClient(
        self, _can_authenticate
    ):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        frontend = next(
            client for client in fake.clients if client["clientId"] == "tapir-frontend"
        )
        frontend["fullScopeAllowed"] = True

        check = KeycloakReconciler(fake, desired).reconcile(dry_run=True)
        self.assertTrue(
            any(
                change.section == "clients" and "fullScopeAllowed" in change.message
                for change in check.changes
            )
        )
        self.assertTrue(frontend["fullScopeAllowed"])

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)
        self.assertFalse(frontend["fullScopeAllowed"])

    def test_reconcile_missingRoleScopeMapping_reportsAndAdds(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.client_scope_roles = {}

        check = KeycloakReconciler(fake, desired).reconcile(dry_run=True)
        mapping_errors = [
            change
            for change in check.changes
            if change.section == "clients" and "role scope mapping" in change.message
        ]
        self.assertEqual(2, len(mapping_errors))
        messages = " ".join(change.message for change in mapping_errors)
        self.assertIn("manage-users", messages)
        self.assertIn("realm-admin", messages)
        self.assertFalse(fake.calls_of("assign_client_roles_to_client_scope"))

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        assign_calls = fake.calls_of("assign_client_roles_to_client_scope")
        self.assertEqual(2, len(assign_calls))
        assigned = {
            (call[1], call[2]): {role["name"] for role in call[3]}
            for call in assign_calls
        }
        self.assertEqual(
            {"manage-users"},
            assigned[("client-tapir-backend", "client-realm-management")],
        )
        self.assertEqual(
            {"realm-admin"},
            assigned[("client-tapir-provisioner", "client-realm-management")],
        )

    def test_reconcile_extraRoleScopeMapping_warnsAndDoesNotDelete(
        self, _can_authenticate
    ):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.client_scope_roles[
            ("client-tapir-backend", "client-realm-management")
        ].add("extra.role")

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertTrue(
            any(
                change.level == "warning" and "extra.role" in change.message
                for change in result.changes
            )
        )
        self.assertFalse([call for call in fake.calls if call[0].startswith("delete_")])

    def test_reconcile_roleScopeMappingBeforeFullScopeUpdate(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.client_scope_roles = {}
        provisioner = next(
            client
            for client in fake.clients
            if client["clientId"] == "tapir-provisioner"
        )
        provisioner["fullScopeAllowed"] = True

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        assign_index = next(
            index
            for index, call in enumerate(fake.calls)
            if call[0] == "assign_client_roles_to_client_scope"
            and call[1] == "client-tapir-provisioner"
        )
        update_index = next(
            index
            for index, call in enumerate(fake.calls)
            if call[0] == "update_client" and call[1] == "client-tapir-provisioner"
        )
        self.assertLess(assign_index, update_index)

    def test_reconcile_missingClient_createsIt(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.clients = [
            client for client in fake.clients if client["clientId"] != "tapir-backend"
        ]

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        create_calls = fake.calls_of("create_client")
        self.assertEqual(1, len(create_calls))
        self.assertEqual("tapir-backend", create_calls[0][1]["clientId"])

    def test_reconcile_missingServiceAccountRole_assignsIt(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.service_account_roles["tapir-backend"] = {"realm-management": set()}

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        assign_calls = fake.calls_of("assign_client_role")
        self.assertEqual(1, len(assign_calls))
        self.assertEqual(
            {"manage-users"}, {role["name"] for role in assign_calls[0][3]}
        )

    def test_reconcile_missingSmtp_warnsWithoutFailing(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.realm.pop("smtpServer")

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertFalse(result.has_errors)
        self.assertTrue(
            any(
                change.level == "warning" and "smtpServer" in change.message
                for change in result.changes
            )
        )
        check = next(
            check for check in result.checks if check.description == "SMTP server"
        )
        self.assertEqual("warning", check.status)

    def test_reconcile_converged_checksAreOk(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        descriptions = {check.description for check in result.checks}
        self.assertEqual(
            {
                "realm settings",
                "realm roles",
                "superuser group",
                "clients",
                "default client scopes",
                "client role scope mappings",
                "service account roles",
                "runtime client secret",
                "SMTP server",
                "user profile",
            },
            descriptions,
        )
        self.assertTrue(
            all(check.status in {"ok", "skipped"} for check in result.checks),
            [check for check in result.checks if check.status not in {"ok", "skipped"}],
        )

    def test_reconcile_missingRoles_checkIsError(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        check = next(
            check for check in result.checks if check.description == "realm roles"
        )
        self.assertEqual("error", check.status)
        self.assertIn("0/9", check.details)

    def test_reconcile_missingClient_checkIsError(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.clients = []

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        check = next(check for check in result.checks if check.description == "clients")
        self.assertEqual("error", check.status)
        self.assertIn("0/3", check.details)

    def test_reconcile_neverDeletesAnything(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.roles = {}
        fake.groups = []

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        self.assertFalse([call for call in fake.calls if call[0].startswith("delete_")])

    def test_reconcile_missingRealm_raisesSetupError(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin(realm_error_code=404)

        with self.assertRaises(KeycloakSetupError) as context:
            KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertIn("realm does not exist", str(context.exception))

    def test_reconcile_unauthorized_raisesSetupError(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin(realm_error_code=401)

        with self.assertRaises(KeycloakSetupError) as context:
            KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertIn("could not authenticate", str(context.exception))

    def test_reconcile_forbidden_raisesSetupError(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin(realm_error_code=403)

        with self.assertRaises(KeycloakSetupError) as context:
            KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertIn("realm-admin", str(context.exception))

    def test_reconcile_connectionError_raisesSetupError(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin(connection_error=True)

        with self.assertRaises(KeycloakSetupError) as context:
            KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertIn("not reachable", str(context.exception))

    def test_reconcile_missingAdminApiScope_reportsAndAdds(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        backend = next(
            client for client in fake.clients if client["clientId"] == "tapir-backend"
        )
        backend["defaultClientScopes"].remove(ADMIN_API_CLIENT_SCOPE)

        check = KeycloakReconciler(fake, desired).reconcile(dry_run=True)
        self.assertTrue(
            any(
                change.section == "clients" and ADMIN_API_CLIENT_SCOPE in change.message
                for change in check.changes
            )
        )
        self.assertFalse(fake.calls_of("add_client_default_client_scope"))

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        add_calls = fake.calls_of("add_client_default_client_scope")
        self.assertEqual(1, len(add_calls))
        self.assertEqual(f"scope-{ADMIN_API_CLIENT_SCOPE}", add_calls[0][2])
        self.assertIn(ADMIN_API_CLIENT_SCOPE, backend["defaultClientScopes"])

    def test_reconcile_adminApiScopeMissingOnServer_reportsNotFixable(
        self, _can_authenticate
    ):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)
        fake.client_scope_names.remove(ADMIN_API_CLIENT_SCOPE)
        backend = next(
            client for client in fake.clients if client["clientId"] == "tapir-backend"
        )
        backend["defaultClientScopes"].remove(ADMIN_API_CLIENT_SCOPE)

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        self.assertTrue(
            any(
                change.section == "clients"
                and change.message == ADMIN_API_SCOPE_MISSING_MESSAGE
                and not change.fixable
                for change in result.changes
            )
        )
        self.assertFalse(fake.calls_of("add_client_default_client_scope"))

    def test_reconcile_convergedWithManagedUserProfile_checkIsOk(
        self, _can_authenticate
    ):
        with self.settings(
            KEYCLOAK_USER_PROFILE_MANAGED=True,
            KEYCLOAK_USER_PROFILE_FILE=EXAMPLE_PROFILE_FILE,
            KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[
                {"keycloak": "customernumber", "tapir": "member_no"}
            ],
        ):
            desired = build_desired_state()
            fake = FakeKeycloakAdmin.converged(desired)

            result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        check = next(
            check for check in result.checks if check.description == "user profile"
        )
        self.assertEqual("ok", check.status)
        self.assertFalse(mutating_calls(fake))

    def test_reconcile_userProfileDrift_syncReplacesProfile(self, _can_authenticate):
        with self.settings(
            KEYCLOAK_USER_PROFILE_MANAGED=True,
            KEYCLOAK_USER_PROFILE_FILE=EXAMPLE_PROFILE_FILE,
            KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[
                {"keycloak": "customernumber", "tapir": "member_no"}
            ],
        ):
            desired = build_desired_state()
            fake = FakeKeycloakAdmin.converged(desired)
            fake.profile["attributes"] = [
                attribute
                for attribute in fake.profile["attributes"]
                if attribute["name"] != "customernumber"
            ]
            fake.profile["attributes"].append(
                {"name": "legacy", "displayName": "legacy"}
            )

            check = KeycloakReconciler(fake, desired).reconcile(dry_run=True)
            self.assertTrue(
                any(
                    change.section == "user-profile"
                    and "customernumber is missing" in change.message
                    for change in check.changes
                )
            )
            self.assertTrue(
                any(
                    change.section == "user-profile"
                    and "legacy is not managed" in change.message
                    for change in check.changes
                )
            )
            self.assertFalse(fake.calls_of("update_realm_users_profile"))

            KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        self.assertTrue(fake.calls_of("update_realm_users_profile"))
        self.assertEqual(desired.user_profile, fake.profile)

    def test_reconcile_userProfileNotManaged_checkIsSkipped(self, _can_authenticate):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        check = next(
            check for check in result.checks if check.description == "user profile"
        )
        self.assertEqual("skipped", check.status)
        self.assertFalse(fake.calls_of("get_realm_users_profile"))

    def test_reconcile_userProfileNotManagedMissingMappedAttribute_reportsNotFixable(
        self, _can_authenticate
    ):
        with self.settings(
            KEYCLOAK_USER_PROFILE_MANAGED=False,
            KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP=[
                {"keycloak": "customernumber", "tapir": "member_no"}
            ],
        ):
            desired = build_desired_state()
            fake = FakeKeycloakAdmin.converged(desired)

            result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        check = next(
            check for check in result.checks if check.description == "user profile"
        )
        self.assertEqual("error", check.status)
        self.assertTrue(
            any(
                change.section == "user-profile"
                and "customernumber" in change.message
                and not change.fixable
                for change in result.changes
            )
        )
        self.assertFalse(fake.calls_of("update_realm_users_profile"))

    def test_reconcile_userProfileApiUnavailable_reportsError(self, _can_authenticate):
        with self.settings(
            KEYCLOAK_USER_PROFILE_MANAGED=True,
            KEYCLOAK_USER_PROFILE_FILE=EXAMPLE_PROFILE_FILE,
        ):
            desired = build_desired_state()
            fake = FakeKeycloakAdmin.converged(desired)
            fake.profile_error_code = 404

            result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        self.assertTrue(
            any(
                change.section == "user-profile" and not change.fixable
                for change in result.changes
            )
        )

    def test_reconcile_complexUserProfile_noDrift(self, _can_authenticate):
        desired = build_desired_state()
        complex_desired = replace(
            desired, user_profile=deepcopy(COMPLEX_USER_PROFILE_EXAMPLE)
        )
        fake = FakeKeycloakAdmin.converged(complex_desired)
        fake.profile = deepcopy(COMPLEX_USER_PROFILE_EXAMPLE)

        result = KeycloakReconciler(fake, complex_desired).reconcile(dry_run=True)

        check = next(
            check for check in result.checks if check.description == "user profile"
        )
        self.assertEqual("ok", check.status)
        self.assertFalse(
            any(change.section == "user-profile" for change in result.changes)
        )


@override_settings(**SETTINGS)
class TestKeycloakReconcilerRuntimeSecret(TapirUnitTest):
    @patch(
        "tapir.accounts.services.keycloak_reconciler.can_authenticate",
        return_value=(False, REASON_AUTHENTICATION_FAILED),
    )
    def test_reconcile_runtimeClientCannotAuthenticate_checkIsError(
        self, _can_authenticate
    ):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=True)

        check = next(
            check
            for check in result.checks
            if check.description == "runtime client secret"
        )
        self.assertEqual("error", check.status)

    @patch(
        "tapir.accounts.services.keycloak_reconciler.can_authenticate",
        side_effect=[(False, REASON_AUTHENTICATION_FAILED), (True, None)],
    )
    def test_reconcile_runtimeClientCannotAuthenticate_repairsSecret(
        self, _can_authenticate
    ):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        update_calls = fake.calls_of("update_client")
        self.assertEqual(1, len(update_calls))
        self.assertEqual({"secret": "backend-secret"}, update_calls[0][2])
        self.assertEqual(2, _can_authenticate.call_count)

    @patch(
        "tapir.accounts.services.keycloak_reconciler.can_authenticate",
        return_value=(False, REASON_MISSING_ADMIN_API_SCOPE),
    )
    def test_reconcile_runtimeClientMissingAdminApiScope_doesNotRewriteSecret(
        self, _can_authenticate
    ):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        result = KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        self.assertFalse(fake.calls_of("update_client"))
        self.assertTrue(
            any(
                change.section == "clients"
                and "Admin API" in change.message
                and not change.fixable
                for change in result.changes
            )
        )

    @patch(
        "tapir.accounts.services.keycloak_reconciler.can_authenticate",
        return_value=(False, "keycloak is not reachable"),
    )
    def test_reconcile_runtimeClientUnreachable_doesNotRewriteSecret(
        self, _can_authenticate
    ):
        desired = build_desired_state()
        fake = FakeKeycloakAdmin.converged(desired)

        KeycloakReconciler(fake, desired).reconcile(dry_run=False)

        self.assertFalse(fake.calls_of("update_client"))
