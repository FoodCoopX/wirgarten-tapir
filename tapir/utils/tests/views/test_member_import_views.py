from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberImportViews(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getAndPost_regularMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))
        for name, method in (
            ("member_import", self.client.get),
            ("member_import_template", self.client.get),
            ("member_import_apply", self.client.post),
        ):
            with self.subTest(name=name):
                self.assertStatusCode(method(reverse("utils:" + name)), 403)

    def test_getAndPost_anonymous_redirectsToLogin(self):
        for name, method in (
            ("member_import", self.client.get),
            ("member_import_template", self.client.get),
            ("member_import_apply", self.client.post),
        ):
            with self.subTest(name=name):
                self.assertStatusCode(method(reverse("utils:" + name)), 302)

    def test_post_adminPreviewAndConfirm_savesOnlyAfterConfirmation(self):
        self._login_as_admin()
        file = SimpleUploadedFile(
            "members.csv", b"Nr;Mailadresse\n101;mika@example.test\n"
        )

        preview = self.client.post(reverse("utils:member_import"), {"file": file})

        self.assertStatusCode(preview, 200)
        self.assertContains(preview, "Mitglieder importieren")
        self.assertFalse(Member.objects.filter(member_no=101).exists())
        response = self.client.post(
            reverse("utils:member_import_apply"), {"token": preview.context["token"]}
        )
        self.assertStatusCode(response, 200)
        self.assertTrue(response.context["result"].applied)
        self.assertEqual("mika@example.test", Member.objects.get(member_no=101).email)

    def test_post_invalidEmail_showsRowErrorWithoutApplyButton(self):
        self._login_as_admin()
        file = SimpleUploadedFile("members.csv", b"Nr;Mailadresse\n101;invalid\n")

        response = self.client.post(reverse("utils:member_import"), {"file": file})

        self.assertStatusCode(response, 200)
        self.assertContains(response, "Ungültige E-Mail-Adresse")
        self.assertIsNone(response.context["token"])
        self.assertFalse(Member.objects.filter(member_no=101).exists())

    def test_get_templateAsAdmin_receivesCsv(self):
        self._login_as_admin()

        response = self.client.get(reverse("utils:member_import_template"))

        self.assertStatusCode(response, 200)
        self.assertEqual("text/csv; charset=utf-8", response["Content-Type"])
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbfNr;"))
