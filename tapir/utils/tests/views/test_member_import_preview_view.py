from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class TestMemberImportPreviewView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_anonymous_returns401(self):
        self.assertStatusCode(
            self.client.post(reverse("utils:member_import_preview")), 401
        )

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        self.assertStatusCode(
            self.client.post(reverse("utils:member_import_preview")), 403
        )

    def test_post_validFile_returnsPreviewWithoutSaving(self):
        self._login_as_admin()
        file = SimpleUploadedFile(
            "members.csv", b"Nr;Mailadresse\n101;mika@example.test\n"
        )
        response = self.client.post(
            reverse("utils:member_import_preview"), {"file": file}
        )
        self.assertStatusCode(response, 200)
        data = response.json()
        self.assertTrue(data["result"]["can_apply"])
        self.assertIsNotNone(data["token"])
        self.assertFalse(Member.objects.filter(member_no=101).exists())

    def test_post_invalidMemberNumber_returnsRowErrorWithoutToken(self):
        self._login_as_admin()
        member_count = Member.objects.count()
        file = SimpleUploadedFile(
            "members.csv", b"Nr;Mailadresse\ninvalid;mika@example.test\n"
        )
        response = self.client.post(
            reverse("utils:member_import_preview"), {"file": file}
        )
        self.assertStatusCode(response, 200)
        data = response.json()
        self.assertIsNone(data["token"])
        self.assertFalse(data["result"]["can_apply"])
        self.assertEqual(2, data["result"]["rows"][0]["line"])
        self.assertTrue(data["result"]["rows"][0]["error"])
        self.assertEqual(member_count, Member.objects.count())

    def test_post_unsupportedFile_returns400(self):
        self._login_as_admin()
        response = self.client.post(
            reverse("utils:member_import_preview"),
            {"file": SimpleUploadedFile("members.txt", b"data")},
        )
        self.assertStatusCode(response, 400)
        self.assertIn("CSV- oder Excel-Datei", response.json()["detail"])
