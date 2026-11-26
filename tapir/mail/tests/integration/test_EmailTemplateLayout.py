from django.urls import reverse
from tapir.mail.models import EmailTemplate, EmailTemplateType
from tapir.mail.tests.factories import EmailTemplateFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class EmailTemplateLayoutTest(TapirIntegrationTest):
    BODY_TOKEN = "{{Body}}"
    CONTENT = f'<mjml><mj-body><mj-section css-class="tapir-layout-body"><mj-column><mj-text>{BODY_TOKEN}</mj-text></mj-column></mj-section></mj-body></mjml>'

    def setUp(self):
        super().setUp()
        self._login_as_admin()
        EmailTemplate.objects.all().delete()

    def test_createEmailTemplate_layoutWithBodyBlock_returns201(self):
        response = self._create(
            {
                "name": "My layout",
                "content": self.CONTENT,
                "template_type": EmailTemplateType.LAYOUT,
            }
        )

        self.assertStatusCode(response, 201)
        template = EmailTemplate.objects.get(name="My layout")
        self.assertEqual(EmailTemplateType.LAYOUT, template.template_type)

    def test_createEmailTemplate_layoutWithoutBodyBlock_returns400(self):
        response = self._create(
            {
                "name": "My layout",
                "content": "<mjml><mj-body></mj-body></mjml>",
                "template_type": EmailTemplateType.LAYOUT,
            }
        )

        self.assertStatusCode(response, 400)
        self.assertFalse(EmailTemplate.objects.filter(name="My layout").exists())

    def test_createEmailTemplate_layoutWithUnknownToken_returns400(self):
        response = self._create(
            {
                "name": "My layout",
                "content": self.CONTENT.replace(
                    self.BODY_TOKEN, "{{unknown.token}} {{Body}}"
                ),
                "template_type": EmailTemplateType.LAYOUT,
            }
        )

        self.assertStatusCode(response, 400)
        self.assertFalse(EmailTemplate.objects.filter(name="My layout").exists())

    def test_createEmailTemplate_startTemplateAsDefaultLayout_returns400(self):
        response = self._create(
            {
                "name": "My template",
                "content": "<mjml><mj-body></mj-body></mjml>",
                "template_type": EmailTemplateType.START,
                "is_default_layout": True,
            }
        )

        self.assertStatusCode(response, 400)
        self.assertFalse(EmailTemplate.objects.filter(name="My template").exists())

    def test_createEmailTemplate_secondLayoutAsDefault_unsetsTheFirst(self):
        first = EmailTemplateFactory.create(
            template_type=EmailTemplateType.LAYOUT,
            content=self.CONTENT,
            is_default_layout=True,
        )

        response = self._create(
            {
                "name": "Second layout",
                "content": self.CONTENT,
                "template_type": EmailTemplateType.LAYOUT,
                "is_default_layout": True,
            }
        )

        self.assertStatusCode(response, 201)
        self.assertEqual(
            1, EmailTemplate.objects.filter(is_default_layout=True).count()
        )
        first.refresh_from_db()
        self.assertFalse(first.is_default_layout)

    def test_updateEmailTemplate_layoutAsDefault_unsetsTheFirst(self):
        first = EmailTemplateFactory.create(
            template_type=EmailTemplateType.LAYOUT,
            content=self.CONTENT,
            is_default_layout=True,
        )
        second = EmailTemplateFactory.create(
            template_type=EmailTemplateType.LAYOUT,
            content=self.CONTENT,
        )

        response = self._update(
            second.id,
            {
                "name": second.name,
                "content": self.CONTENT,
                "template_type": EmailTemplateType.LAYOUT,
                "is_default_layout": True,
            },
        )

        self.assertStatusCode(response, 200)
        second.refresh_from_db()
        self.assertTrue(second.is_default_layout)
        first.refresh_from_db()
        self.assertFalse(first.is_default_layout)

    def test_updateEmailTemplate_layoutWithoutBodyBlock_returns400(self):
        layout = EmailTemplateFactory.create(
            template_type=EmailTemplateType.LAYOUT,
            content=self.CONTENT,
        )

        response = self._update(
            layout.id,
            {
                "name": layout.name,
                "content": "<mjml><mj-body></mj-body></mjml>",
                "template_type": EmailTemplateType.LAYOUT,
            },
        )

        self.assertStatusCode(response, 400)
        layout.refresh_from_db()
        self.assertEqual(self.CONTENT, layout.content)

    def test_createEmailTemplate_twoLayoutBodySections_returns400(self):
        body_section = (
            '<mj-section css-class="tapir-layout-body">'
            "<mj-column><mj-text>{{Body}}</mj-text></mj-column></mj-section>"
        )

        response = self._create(
            {
                "name": "My layout",
                "content": f"<mjml><mj-body>{body_section}{body_section}</mj-body></mjml>",
                "template_type": EmailTemplateType.LAYOUT,
            }
        )

        self.assertStatusCode(response, 400)
        self.assertFalse(EmailTemplate.objects.filter(name="My layout").exists())

    def _create(self, post_data: dict):
        return self.client.post(
            reverse("email_template-list"),
            data=post_data,
            content_type="application/json",
        )

    def _update(self, template_id: str, put_data: dict):
        return self.client.put(
            reverse("email_template-detail", args=[template_id]),
            data=put_data,
            content_type="application/json",
        )
