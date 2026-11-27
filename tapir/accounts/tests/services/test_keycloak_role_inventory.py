from django.test import override_settings

from tapir.accounts.services.keycloak_desired_state import (
    REALM_ROLES,
    build_desired_state,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.tests.test_utils import TapirUnitTest

EXPECTED_ROLES = {
    "coop.view",
    "coop.manage",
    "accounts.view",
    "accounts.manage",
    "payments.view",
    "payments.manage",
    "products.view",
    "products.manage",
    "email.manage",
}


@override_settings(DEBUG=True)
class TestKeycloakRoleInventory(TapirUnitTest):
    def test_permissionAll_default_containsTheNineExpectedRoles(self):
        self.assertEqual(EXPECTED_ROLES, set(Permission.all()))

    def test_permissionAll_default_hasNoDuplicates(self):
        self.assertEqual(len(Permission.all()), len(set(Permission.all())))

    def test_permissionAll_default_containsCoopManage(self):
        self.assertIn("coop.manage", Permission.all())

    def test_realmRoles_default_isSortedPermissionAll(self):
        self.assertEqual(tuple(sorted(Permission.all())), REALM_ROLES)

    def test_buildDesiredState_default_usesEveryRealmRole(self):
        desired = build_desired_state()

        self.assertEqual(
            tuple(REALM_ROLES),
            tuple(role.name for role in desired.realm_roles),
        )
        self.assertTrue(
            all(
                role.client_role is False and role.composite is False
                for role in desired.realm_roles
            )
        )
        self.assertIn("coop.manage", {role.name for role in desired.realm_roles})

    def test_buildDesiredState_default_superuserGroupHasEveryRealmRole(self):
        desired = build_desired_state()

        self.assertEqual(REALM_ROLES, desired.superuser_group.realm_roles)
        self.assertEqual("superuser", desired.superuser_group.name)
