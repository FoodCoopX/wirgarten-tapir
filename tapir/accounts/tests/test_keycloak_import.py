import json
from pathlib import Path

from django.conf import settings

from tapir.wirgarten.tests.test_utils import TapirUnitTest

IMPORT_PATH = (
    Path(settings.BASE_DIR).parent
    / "docker"
    / "keycloak"
    / "import"
    / "tapir-realm.json"
)


class TestKeycloakRealmImport(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.import_data = json.loads(IMPORT_PATH.read_text())
        self.import_text = json.dumps(self.import_data)

    def test_import_default_containsOnlyTheProvisionerClient(self):
        clients = self.import_data["clients"]

        self.assertEqual(1, len(clients))
        self.assertEqual("tapir-provisioner", clients[0]["clientId"])
        self.assertNotIn("tapir-backend", self.import_text)
        self.assertNotIn("tapir-frontend", self.import_text)

    def test_import_provisionerClient_isConfidentialWithServiceAccount(self):
        client = self.import_data["clients"][0]

        self.assertFalse(client["publicClient"])
        self.assertTrue(client["serviceAccountsEnabled"])
        self.assertFalse(client["standardFlowEnabled"])
        self.assertFalse(client["directAccessGrantsEnabled"])
        self.assertEqual([], client["redirectUris"])
        self.assertEqual([], client["webOrigins"])
        self.assertFalse(client["fullScopeAllowed"])

    def test_import_provisionerClient_hasRoleScopeMappingForRealmAdmin(self):
        self.assertEqual(
            {
                "realm-management": [
                    {"client": "tapir-provisioner", "roles": ["realm-admin"]}
                ]
            },
            self.import_data["clientScopeMappings"],
        )

    def test_import_provisionerServiceAccount_hasRealmAdmin(self):
        users = self.import_data["users"]

        self.assertEqual(1, len(users))
        service_account = users[0]
        self.assertEqual("tapir-provisioner", service_account["serviceAccountClientId"])
        self.assertEqual(
            {"realm-management": ["realm-admin"]},
            service_account["clientRoles"],
        )

    def test_import_containsNoTapirRolesOrSuperuserGroup(self):
        self.assertNotIn("coop.manage", self.import_text)
        self.assertEqual([], self.import_data.get("roles", {}).get("realm", []))
        self.assertEqual([], self.import_data.get("groups", []))
        for role in (
            "coop.view",
            "accounts.view",
            "accounts.manage",
            "payments.view",
            "payments.manage",
            "products.view",
            "products.manage",
            "email.manage",
        ):
            self.assertNotIn(role, self.import_text)

    def test_import_hasNoGeneratedIdsOrKeycloakVersion(self):
        self.assertNotIn("id", self.import_data)
        self.assertNotIn("keycloakVersion", self.import_data)
        for client in self.import_data["clients"]:
            self.assertNotIn("id", client)

    def test_import_doesNotManageThemes(self):
        for key in (
            "loginTheme",
            "emailTheme",
            "accountTheme",
            "adminTheme",
            "displayNameHtml",
        ):
            self.assertNotIn(key, self.import_data)
