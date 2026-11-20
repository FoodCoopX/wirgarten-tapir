import json

from django.test import override_settings

from tapir.accounts.services.keycloak_config import (
    build_keycloak_config_summary,
    check_keycloak_config,
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
)
EXTERNAL_ADMIN_CONFIG = {
    **ADMIN_CONFIG,
    "SERVER_URL": "https://auth.example.org",
    "PUBLIC_URL": "https://auth.example.org",
}


@override_settings(**SETTINGS)
class TestKeycloakConfig(TapirUnitTest):
    def test_checkKeycloakConfig_default_returnsNoErrors(self):
        check = check_keycloak_config()

        self.assertFalse(check.errors)

    def test_checkKeycloakConfig_externalServer_returnsNoIssues(self):
        with override_settings(KEYCLOAK_ADMIN_CONFIG=EXTERNAL_ADMIN_CONFIG):
            check = check_keycloak_config()

        self.assertFalse(check.errors)
        self.assertFalse(check.warnings)

    def test_checkKeycloakConfig_relativeServerUrl_returnsErrorForServerUrl(self):
        with override_settings(
            KEYCLOAK_ADMIN_CONFIG={**ADMIN_CONFIG, "SERVER_URL": "keycloak:8080"}
        ):
            check = check_keycloak_config()

        self.assertTrue(
            any(issue.variable == "KEYCLOAK_ADMIN_SERVER_URL" for issue in check.errors)
        )

    def test_checkKeycloakConfig_serverUrlWithRealmPath_returnsError(self):
        with override_settings(
            KEYCLOAK_ADMIN_CONFIG={
                **ADMIN_CONFIG,
                "SERVER_URL": "https://auth.example.org/realms/tapir",
            }
        ):
            check = check_keycloak_config()

        self.assertTrue(
            any(
                issue.variable == "KEYCLOAK_ADMIN_SERVER_URL"
                and "/realms/" in issue.message
                for issue in check.errors
            )
        )

    def test_checkKeycloakConfig_relativePublicUrl_returnsErrorForPublicUrl(self):
        with override_settings(
            KEYCLOAK_ADMIN_CONFIG={**ADMIN_CONFIG, "PUBLIC_URL": "localhost:8080"}
        ):
            check = check_keycloak_config()

        self.assertTrue(
            any(issue.variable == "KEYCLOAK_PUBLIC_URL" for issue in check.errors)
        )

    def test_checkKeycloakConfig_emptyRealm_returnsError(self):
        with override_settings(
            KEYCLOAK_ADMIN_CONFIG={**ADMIN_CONFIG, "REALM_NAME": ""}
        ):
            check = check_keycloak_config()

        self.assertTrue(
            any(issue.variable == "KEYCLOAK_REALM_NAME" for issue in check.errors)
        )

    def test_checkKeycloakConfig_realmWithSlash_returnsError(self):
        with override_settings(
            KEYCLOAK_ADMIN_CONFIG={**ADMIN_CONFIG, "REALM_NAME": "tapir/other"}
        ):
            check = check_keycloak_config()

        self.assertTrue(
            any(issue.variable == "KEYCLOAK_REALM_NAME" for issue in check.errors)
        )

    def test_checkKeycloakConfig_duplicateClientIds_returnsError(self):
        with override_settings(
            KEYCLOAK_ADMIN_CONFIG={
                **ADMIN_CONFIG,
                "FRONTEND_CLIENT_ID": ADMIN_CONFIG["CLIENT_ID"],
            }
        ):
            check = check_keycloak_config()

        self.assertTrue(
            any(issue.variable == "KEYCLOAK_CLIENT_ID" for issue in check.errors)
        )

    def test_checkKeycloakConfig_emptyBackendSecret_returnsError(self):
        with override_settings(
            KEYCLOAK_ADMIN_CONFIG={**ADMIN_CONFIG, "CLIENT_SECRET_KEY": ""}
        ):
            check = check_keycloak_config()

        self.assertTrue(
            any(
                issue.variable == "KEYCLOAK_ADMIN_CLIENT_SECRET_KEY"
                for issue in check.errors
            )
        )

    def test_checkKeycloakConfig_emptyProvisionerSecret_returnsError(self):
        with override_settings(
            KEYCLOAK_PROVISIONER_CONFIG={
                **PROVISIONER_CONFIG,
                "CLIENT_SECRET_KEY": "",
            }
        ):
            check = check_keycloak_config()

        self.assertTrue(
            any(
                issue.variable == "KEYCLOAK_PROVISIONER_CLIENT_SECRET_KEY"
                for issue in check.errors
            )
        )

    def test_checkKeycloakConfig_placeholderProvisionerSecretInDebug_returnsNoError(
        self,
    ):
        with override_settings(
            DEBUG=True,
            KEYCLOAK_PROVISIONER_CONFIG={
                **PROVISIONER_CONFIG,
                "CLIENT_SECRET_KEY": "**********",
            },
        ):
            check = check_keycloak_config()

        self.assertFalse(check.errors)

    def test_checkKeycloakConfig_localDefaultsOutsideDebug_returnsWarnings(self):
        check = check_keycloak_config()
        variables = {issue.variable for issue in check.warnings}

        self.assertIn("KEYCLOAK_ADMIN_SERVER_URL", variables)
        self.assertIn("KEYCLOAK_PUBLIC_URL", variables)

    def test_buildKeycloakConfigSummary_default_containsNoSecrets(self):
        summary = build_keycloak_config_summary()
        serialized = json.dumps(summary)

        self.assertEqual("http://keycloak:8080", summary["server_url"])
        self.assertEqual("http://localhost:8080", summary["public_url"])
        self.assertEqual("tapir-provisioner", summary["provisioner_client_id"])
        self.assertNotIn("backend-secret", serialized)
        self.assertNotIn("provisioner-secret", serialized)

    @override_settings(
        KEYCLOAK_USERNAME_SOURCE="customernumber",
        KEYCLOAK_REGISTRATION_EMAIL_AS_USERNAME=True,
        KEYCLOAK_EDIT_USERNAME_ALLOWED=True,
    )
    def test_checkKeycloakConfig_customernumberUsernameFlags_returnsWarnings(self):
        check = check_keycloak_config()
        variables = {issue.variable for issue in check.warnings}

        self.assertIn("KEYCLOAK_REGISTRATION_EMAIL_AS_USERNAME", variables)
        self.assertIn("KEYCLOAK_EDIT_USERNAME_ALLOWED", variables)

    @override_settings(
        KEYCLOAK_USERNAME_SOURCE="customernumber",
        KEYCLOAK_USERNAME_FORMAT="formatted",
    )
    def test_buildKeycloakConfigSummary_customernumber_containsUsernamePolicy(self):
        summary = build_keycloak_config_summary()

        self.assertEqual("customernumber", summary["username_source"])
        self.assertEqual("formatted", summary["username_format"])
