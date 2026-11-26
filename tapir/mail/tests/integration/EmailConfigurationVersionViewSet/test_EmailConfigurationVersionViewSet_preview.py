from tapir.wirgarten.parameters import ParameterDefinitions
from django.urls import reverse
from tapir.mail.models import EmailTemplate, EmailTemplateType
from tapir.mail.tests.factories import EmailTemplateFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestEmailConfigurationVersionViewSetPreview(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    MAIL_CONTENT = (
        "<mjml><mj-body>"
        "<mj-section><mj-column><mj-text>MAIL BODY</mj-text></mj-column></mj-section>"
        "</mj-body></mjml>"
    )

    def setUp(self):
        super().setUp()
        self._login_as_admin()
        EmailTemplate.objects.all().delete()

    def _layout_content(self, label: str):
        return (
            "<mjml><mj-body>"
            f"<mj-section><mj-column><mj-text>{label}</mj-text></mj-column></mj-section>"
            '<mj-section css-class="tapir-layout-body">'
            "<mj-column><mj-text>{{Body}}</mj-text></mj-column></mj-section>"
            "</mj-body></mjml>"
        )

    def _create_layout(self, label: str, is_default: bool = False):
        return EmailTemplateFactory.create(
            template_type=EmailTemplateType.LAYOUT,
            content=self._layout_content(label),
            is_default_layout=is_default,
        )

    def _preview(self, post_data: dict):
        return self.client.post(
            reverse("emailconfigurationversion-preview"),
            data=post_data,
            content_type="application/json",
        )

    def test_preview_layoutDisabled_returnsHtmlWithoutLayout(self):
        layout = self._create_layout("DEFAULT HEADER", is_default=True)

        response = self._preview(
            {
                "content": self.MAIL_CONTENT,
                "layout_template_id": layout.id,
                "layout_enabled": False,
            }
        )

        self.assertStatusCode(response, 200)
        self.assertIn("MAIL BODY", response.data["html"])
        self.assertNotIn("DEFAULT HEADER", response.data["html"])

    def test_preview_explicitLayoutTemplate_returnsHtmlWithThatLayout(self):
        layout = self._create_layout("EXPLICIT HEADER")

        response = self._preview(
            {
                "content": self.MAIL_CONTENT,
                "layout_template_id": layout.id,
                "layout_enabled": True,
            }
        )

        self.assertStatusCode(response, 200)
        self.assertIn("EXPLICIT HEADER", response.data["html"])
        self.assertIn("MAIL BODY", response.data["html"])

    def test_preview_withoutExplicitLayout_usesDefaultLayout(self):
        self._create_layout("DEFAULT HEADER", is_default=True)

        response = self._preview(
            {
                "content": self.MAIL_CONTENT,
                "layout_enabled": True,
            }
        )

        self.assertStatusCode(response, 200)
        self.assertIn("DEFAULT HEADER", response.data["html"])
        self.assertIn("MAIL BODY", response.data["html"])

    def test_preview_unknownLayoutTemplateId_returns400(self):
        response = self._preview(
            {
                "content": self.MAIL_CONTENT,
                "layout_template_id": "does-not-exist",
                "layout_enabled": True,
            }
        )

        self.assertStatusCode(response, 400)

    def test_preview_startTemplateIdAsLayout_returns400(self):
        start_template = EmailTemplateFactory.create(
            template_type=EmailTemplateType.START,
            content=self.MAIL_CONTENT,
        )

        response = self._preview(
            {
                "content": self.MAIL_CONTENT,
                "layout_template_id": start_template.id,
                "layout_enabled": True,
            }
        )

        self.assertStatusCode(response, 400)

    def test_preview_nonMjmlContent_returns400(self):
        response = self._preview(
            {
                "content": "not mjml",
                "layout_enabled": False,
            }
        )

        self.assertStatusCode(response, 400)
