from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse

from tapir.utils.services.member_import_service import MemberImportService
from tapir.utils.models import MemberImportedLogEntry
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class TestMemberImportApplyView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_anonymous_returns401(self):
        self.assertStatusCode(
            self.client.post(reverse("utils:member_import_apply")), 401
        )

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        self.assertStatusCode(
            self.client.post(reverse("utils:member_import_apply")), 403
        )

    def test_post_previewToken_importsOnce(self):
        admin = self._login_as_admin()
        file = SimpleUploadedFile(
            "members.csv", b"Nr;Mailadresse\n101;mika@example.test\n"
        )
        token, _ = MemberImportService.preview(file=file, user_id=admin.pk)
        response = self.client.post(
            reverse("utils:member_import_apply"), {"token": token}
        )
        self.assertStatusCode(response, 200)
        self.assertTrue(response.json()["applied"])
        member = Member.objects.get(member_no=101)
        self.assertEqual("mika@example.test", member.email)
        self.assertEqual(
            admin.pk, MemberImportedLogEntry.objects.get(user=member).actor_id
        )
        self.assertStatusCode(
            self.client.post(reverse("utils:member_import_apply"), {"token": token}),
            400,
        )

    def test_post_otherAdminToken_returns400(self):
        self._login_as_admin()
        file = SimpleUploadedFile(
            "members.csv", b"Nr;Mailadresse\n101;mika@example.test\n"
        )
        other_admin = MemberFactory.create(is_superuser=True)
        token, _ = MemberImportService.preview(file=file, user_id=other_admin.pk)
        response = self.client.post(
            reverse("utils:member_import_apply"), {"token": token}
        )
        self.assertStatusCode(response, 400)
        self.assertFalse(Member.objects.filter(member_no=101).exists())
