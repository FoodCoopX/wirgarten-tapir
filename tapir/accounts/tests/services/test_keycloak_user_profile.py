import json
import tempfile
from copy import deepcopy
from pathlib import Path

from tapir.accounts.services.keycloak_reconciler import _user_profile_drift
from tapir.accounts.services.keycloak_user_profile import (
    UserProfileError,
    load_managed_user_profile,
    load_user_profile,
    missing_user_profile_attributes,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest

EXAMPLE_PROFILE_PATH = "examples/keycloak-userprofile.json"

COMPLEX_USER_PROFILE_EXAMPLE = {
    "attributes": [
        {
            "name": "username",
            "displayName": "${username}",
            "validations": {
                "length": {"min": 3, "max": 255},
                "username-prohibited-characters": {},
                "up-username-not-idn-homograph": {},
            },
            "annotations": {},
            "permissions": {"view": ["admin", "user"], "edit": ["admin"]},
            "multivalued": False,
        },
        {
            "name": "email",
            "displayName": "${email}",
            "validations": {"email": {}, "length": {"max": 255}},
            "annotations": {},
            "required": {"roles": ["user"]},
            "permissions": {"view": ["admin", "user"], "edit": ["admin"]},
            "multivalued": False,
        },
        {
            "name": "firstName",
            "displayName": "${firstName}",
            "validations": {
                "length": {"max": 255},
                "person-name-prohibited-characters": {},
                "unique-firstname-lastname-attribute-combination": {},
            },
            "annotations": {},
            "required": {"roles": ["admin", "user"]},
            "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
            "multivalued": False,
        },
        {
            "name": "lastName",
            "displayName": "${lastName}",
            "validations": {
                "length": {"max": 255},
                "person-name-prohibited-characters": {},
                "unique-firstname-lastname-attribute-combination": {},
            },
            "annotations": {},
            "required": {"roles": ["admin", "user"]},
            "permissions": {"view": ["admin", "user"], "edit": ["admin", "user"]},
            "multivalued": False,
        },
        {
            "name": "customernumber",
            "displayName": "${profile.attributes.customernumber}",
            "validations": {},
            "annotations": {},
            "required": {"roles": ["user"]},
            "permissions": {"view": ["admin", "user"], "edit": ["admin"]},
            "multivalued": False,
        },
    ],
    "groups": [
        {
            "name": "superuser",
            "displayHeader": "Superuser",
            "displayDescription": "Full access to all cooperative data",
            "annotations": {},
        }
    ],
}


class TestKeycloakUserProfile(TapirUnitTest):
    def _write_profile(self, content) -> str:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "profile.json"
        path.write_text(
            content if isinstance(content, str) else json.dumps(content),
            encoding="utf-8",
        )
        return str(path)

    def test_loadUserProfile_default_returnsDocument(self):
        profile = {"attributes": [{"name": "email", "displayName": "${email}"}]}

        loaded = load_user_profile(self._write_profile(profile))

        self.assertEqual(profile, loaded)

    def test_loadUserProfile_relativePath_resolvesAgainstRepositoryRoot(self):
        profile = load_user_profile(EXAMPLE_PROFILE_PATH)
        names = {attribute["name"] for attribute in profile["attributes"]}

        self.assertIn("customernumber", names)

    def test_loadUserProfile_emptyPath_raisesUserProfileError(self):
        with self.assertRaisesMessage(
            UserProfileError, "KEYCLOAK_USER_PROFILE_FILE is not set"
        ):
            load_user_profile("")

    def test_loadUserProfile_missingFile_raisesUserProfileError(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)

        with self.assertRaisesMessage(UserProfileError, "cannot be read"):
            load_user_profile(str(Path(directory.name) / "missing.json"))

    def test_loadUserProfile_invalidJson_raisesUserProfileError(self):
        with self.assertRaisesMessage(UserProfileError, "is not valid JSON"):
            load_user_profile(self._write_profile("{"))

    def test_loadUserProfile_nonObject_raisesUserProfileError(self):
        with self.assertRaisesMessage(UserProfileError, "must contain a JSON object"):
            load_user_profile(self._write_profile([]))

    def test_loadUserProfile_missingAttributes_raisesUserProfileError(self):
        with self.assertRaisesMessage(
            UserProfileError, "must contain an 'attributes' list"
        ):
            load_user_profile(self._write_profile({}))

    def test_loadUserProfile_attributeWithoutName_raisesUserProfileError(self):
        with self.assertRaisesMessage(UserProfileError, "must have a non-empty 'name'"):
            load_user_profile(self._write_profile({"attributes": [{}]}))

    def test_loadUserProfile_duplicateAttributeNames_raisesUserProfileError(self):
        profile = {
            "attributes": [
                {"name": "email"},
                {"name": "email"},
            ]
        }

        with self.assertRaisesMessage(UserProfileError, "duplicate attributes: email"):
            load_user_profile(self._write_profile(profile))

    def test_missingUserProfileAttributes_default_returnsMissingKeycloakNames(self):
        missing = missing_user_profile_attributes(
            {"attributes": [{"name": "email"}]},
            [
                {"keycloak": "customernumber", "tapir": "member_no"},
                {"keycloak": "email", "tapir": "email"},
            ],
        )

        self.assertEqual(("customernumber",), missing)

    def test_loadManagedUserProfile_missingMappedAttribute_raisesUserProfileError(
        self,
    ):
        path = self._write_profile({"attributes": [{"name": "email"}]})

        with self.assertRaisesMessage(UserProfileError, "customernumber"):
            load_managed_user_profile(
                path, [{"keycloak": "customernumber", "tapir": "member_no"}]
            )

    def test_loadManagedUserProfile_allMappedAttributesPresent_returnsProfile(self):
        path = self._write_profile(
            {
                "attributes": [
                    {"name": "email"},
                    {"name": "customernumber"},
                ]
            }
        )

        profile = load_managed_user_profile(
            path, [{"keycloak": "customernumber", "tapir": "member_no"}]
        )

        self.assertIn("customernumber", {a["name"] for a in profile["attributes"]})

    def test_exampleProfile_isValidAndContainsStandardAttributes(self):
        profile = load_user_profile(EXAMPLE_PROFILE_PATH)
        names = {attribute["name"] for attribute in profile["attributes"]}

        self.assertLessEqual(
            {"username", "email", "firstName", "lastName", "customernumber"},
            names,
        )

    def test_complexExample_hasNoDriftAgainstItself(self):
        self.assertEqual(
            [],
            _user_profile_drift(
                COMPLEX_USER_PROFILE_EXAMPLE, COMPLEX_USER_PROFILE_EXAMPLE
            ),
        )

    def test_complexExample_groupDescriptionDriftIsDetected(self):
        changed = deepcopy(COMPLEX_USER_PROFILE_EXAMPLE)
        changed["groups"][0]["displayDescription"] = "Changed"

        self.assertEqual(
            ["group superuser differs"],
            _user_profile_drift(COMPLEX_USER_PROFILE_EXAMPLE, changed),
        )
