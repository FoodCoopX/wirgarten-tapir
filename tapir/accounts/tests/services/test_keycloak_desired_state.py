from django.test import override_settings

from tapir.accounts.services.keycloak_desired_state import (
    PROVISIONER_SECRET_PLACEHOLDER,
    REALM_MANAGEMENT_CLIENT_ID,
    build_desired_state,
    build_redirect_uris,
    build_web_origins,
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
    SITE_URL="https://tapir.example.org/",
    KEYCLOAK_ADMIN_CONFIG=ADMIN_CONFIG,
    KEYCLOAK_PROVISIONER_CONFIG=PROVISIONER_CONFIG,
)


@override_settings(**SETTINGS)
class TestKeycloakDesiredState(TapirUnitTest):
    def test_buildRedirectUris_default_containsSiteUrlWildcard(self):
        self.assertEqual(
            ("https://tapir.example.org/*",),
            build_redirect_uris("https://tapir.example.org/", False),
        )

    def test_buildRedirectUris_debug_addsLocalDevelopmentUrls(self):
        uris = build_redirect_uris("https://tapir.example.org", True)

        self.assertIn("https://tapir.example.org/*", uris)
        self.assertIn("http://localhost:8000/*", uris)
        self.assertIn("http://127.0.0.1:8000/*", uris)
        self.assertIn("http://localhost:5173/*", uris)
        self.assertIn("http://127.0.0.1:5173/*", uris)

    def test_buildWebOrigins_default_returnsSiteOrigin(self):
        self.assertEqual(
            ("https://tapir.example.org",),
            build_web_origins("https://tapir.example.org/", False),
        )

    def test_buildWebOrigins_debug_addsLocalOrigins(self):
        origins = build_web_origins("https://tapir.example.org", True)

        self.assertIn("https://tapir.example.org", origins)
        self.assertIn("http://localhost:8000", origins)
        self.assertIn("http://127.0.0.1:8000", origins)
        self.assertIn("http://localhost:5173", origins)
        self.assertIn("http://127.0.0.1:5173", origins)

    def test_buildWebOrigins_invalidSiteUrl_raisesValueError(self):
        with self.assertRaises(ValueError):
            build_web_origins("tapir.example.org", False)

    def test_buildDesiredState_default_clientsHaveExpectedFlags(self):
        desired = build_desired_state()
        clients = {client.client_id: client for client in desired.clients}

        backend = clients["tapir-backend"]
        self.assertFalse(backend.public_client)
        self.assertTrue(backend.service_accounts_enabled)
        self.assertTrue(backend.standard_flow_enabled)
        self.assertFalse(backend.direct_access_grants_enabled)
        self.assertFalse(backend.full_scope_allowed)
        self.assertEqual("backend-secret", backend.secret)

        frontend = clients["tapir-frontend"]
        self.assertTrue(frontend.public_client)
        self.assertFalse(frontend.service_accounts_enabled)
        self.assertTrue(frontend.standard_flow_enabled)
        self.assertFalse(frontend.direct_access_grants_enabled)
        self.assertFalse(frontend.full_scope_allowed)
        self.assertIsNone(frontend.secret)

        provisioner = clients["tapir-provisioner"]
        self.assertFalse(provisioner.public_client)
        self.assertTrue(provisioner.service_accounts_enabled)
        self.assertFalse(provisioner.standard_flow_enabled)
        self.assertFalse(provisioner.direct_access_grants_enabled)
        self.assertFalse(provisioner.full_scope_allowed)
        self.assertEqual((), provisioner.redirect_uris)
        self.assertEqual((), provisioner.web_origins)

    def test_buildDesiredState_default_serviceAccountRolesAreMappedToRealmManagement(
        self,
    ):
        desired = build_desired_state()

        self.assertEqual(
            {"manage-users"},
            set(
                desired.service_account_roles["tapir-backend"][
                    REALM_MANAGEMENT_CLIENT_ID
                ]
            ),
        )
        self.assertEqual(
            {"realm-admin"},
            set(
                desired.service_account_roles["tapir-provisioner"][
                    REALM_MANAGEMENT_CLIENT_ID
                ]
            ),
        )

    def test_buildDesiredState_default_clientRoleScopeMappingsAreExplicit(self):
        desired = build_desired_state()

        mappings = {
            (mapping.client_id, mapping.role_owner_client_id, mapping.roles)
            for mapping in desired.client_role_scope_mappings
        }
        self.assertEqual(
            {
                ("tapir-backend", REALM_MANAGEMENT_CLIENT_ID, ("manage-users",)),
                ("tapir-provisioner", REALM_MANAGEMENT_CLIENT_ID, ("realm-admin",)),
            },
            mappings,
        )

    def test_buildDesiredState_default_redirectUrisComeFromSiteUrl(self):
        desired = build_desired_state()

        for client in desired.clients:
            if client.client_id == "tapir-provisioner":
                continue
            self.assertEqual(("https://tapir.example.org/*",), client.redirect_uris)
            self.assertEqual(("https://tapir.example.org",), client.web_origins)

    def test_buildDesiredState_default_doesNotUseWildcardsOutsideDebug(self):
        desired = build_desired_state()

        for client in desired.clients:
            self.assertNotIn("*", client.redirect_uris)
            self.assertNotIn("*", client.web_origins)

    def test_buildDesiredState_placeholderProvisionerSecretOutsideDebug_isWarning(
        self,
    ):
        with override_settings(
            DEBUG=False,
            KEYCLOAK_PROVISIONER_CONFIG={
                "CLIENT_ID": "tapir-provisioner",
                "CLIENT_SECRET_KEY": PROVISIONER_SECRET_PLACEHOLDER,
            },
        ):
            desired = build_desired_state()

        self.assertTrue(
            any(
                "KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY" in warning
                for warning in desired.warnings
            )
        )

    def test_buildDesiredState_placeholderProvisionerSecretInDebug_isNoWarning(
        self,
    ):
        with override_settings(
            DEBUG=True,
            KEYCLOAK_PROVISIONER_CONFIG={
                "CLIENT_ID": "tapir-provisioner",
                "CLIENT_SECRET_KEY": PROVISIONER_SECRET_PLACEHOLDER,
            },
        ):
            desired = build_desired_state()

        self.assertFalse(
            any(
                "KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY" in warning
                for warning in desired.warnings
            )
        )

    def test_buildDesiredState_default_doesNotManageThemeOrDisplayName(self):
        desired = build_desired_state()

        for key in (
            "loginTheme",
            "emailTheme",
            "accountTheme",
            "adminTheme",
            "displayName",
        ):
            self.assertNotIn(key, desired.realm_settings)
