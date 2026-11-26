from tapir.wirgarten.parameters import ParameterDefinitions
from django.core import mail

from tapir.mail.models import EmailTemplate, EmailTemplateType, ReleaseStatus
from tapir.mail.service.email_dispatch import SendEmailBatch
from tapir.mail.service.layout import (
    BODY_PLACEHOLDER_CSS_CLASS,
    get_effective_layout,
)
from tapir.mail.tests.factories import (
    TEST_FILES_DIR,
    EmailConfigurationDispatchFactory,
    EmailConfigurationVersionFactory,
    EmailTemplateFactory,
)
from tapir.mail.tests.integration.utils import TestUtils
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class LayoutRenderingTest(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        EmailTemplate.objects.all().delete()
        self.layout_content = (
            TEST_FILES_DIR / "dummy_layout_template_content.mjml"
        ).read_text(encoding="utf-8")
        self.layout = EmailTemplateFactory.create(
            template_type=EmailTemplateType.LAYOUT,
            content=self.layout_content,
        )
        self.version = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED,
            layout_enabled=True,
            layout_template=self.layout,
        )
        self.config_dispatch = EmailConfigurationDispatchFactory.create(
            email_configuration_version=self.version,
        )

    def _send_one(self):
        TestUtils.create_email_dispatches(
            1,
            config_dispatch=self.config_dispatch,
            recipient_prefix="layout",
        )
        SendEmailBatch.send_email_dispatches()

    def test_sendEmailBatch_layoutEnabledExplicitLayout_wrapsBodyWithLayout(self):
        self._send_one()

        self.assertEqual(1, len(mail.outbox))
        body = mail.outbox[0].body
        self.assertIn("LAYOUT HEADER", body)
        self.assertIn("This is a dummy email!", body)
        self.assertIn("LAYOUT FOOTER", body)

    def test_getEffectiveLayout_layoutEnabledWithoutDefault_returnsNone(self):
        self.version.layout_template = None

        self.assertIsNone(get_effective_layout(self.version))

    def test_sendEmailBatch_layoutEnabledExplicitLayoutAndDefaultLayout_usesExplicitLayout(
        self,
    ):
        default_content = self.layout_content.replace(
            "LAYOUT HEADER", "DEFAULT HEADER"
        ).replace("LAYOUT FOOTER", "DEFAULT FOOTER")
        EmailTemplateFactory.create(
            template_type=EmailTemplateType.LAYOUT,
            content=default_content,
            is_default_layout=True,
        )

        self._send_one()

        body = mail.outbox[0].body
        self.assertIn("LAYOUT HEADER", body)
        self.assertIn("LAYOUT FOOTER", body)
        self.assertNotIn("DEFAULT HEADER", body)
        self.assertNotIn("DEFAULT FOOTER", body)

    def test_sendEmailBatch_layoutEnabledWithoutExplicitLayout_usesGlobalDefault(self):
        self.layout.is_default_layout = True
        self.layout.save()
        self.version.layout_template = None
        self.version.save()

        self._send_one()

        self.assertEqual(1, len(mail.outbox))
        body = mail.outbox[0].body
        self.assertIn("LAYOUT HEADER", body)
        self.assertIn("This is a dummy email!", body)

    def test_sendEmailBatch_layoutDisabled_doesNotWrapBodyWithLayout(self):
        self.version.layout_enabled = False
        self.version.save()

        self._send_one()

        self.assertEqual(1, len(mail.outbox))
        body = mail.outbox[0].body
        self.assertNotIn("LAYOUT HEADER", body)
        self.assertIn("This is a dummy email!", body)

    def test_sendEmailBatch_layoutEnabledWithoutAvailableLayout_doesNotWrapBody(self):
        self.version.layout_template = None
        self.version.save()

        self._send_one()

        self.assertEqual(1, len(mail.outbox))
        body = mail.outbox[0].body
        self.assertNotIn("LAYOUT HEADER", body)
        self.assertIn("This is a dummy email!", body)

    def test_sendEmailBatch_layoutContentWithMarkerSection_replacesMarkerWithBody(self):
        self.assertIn(BODY_PLACEHOLDER_CSS_CLASS, self.layout_content)

        self._send_one()

        body = mail.outbox[0].body
        self.assertNotRegex(body, r"\{\{\s*Body\s*\}\}")
        self.assertIn("This is a dummy email!", body)
