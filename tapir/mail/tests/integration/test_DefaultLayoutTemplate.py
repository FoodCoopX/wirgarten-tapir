from tapir.mail.models import EmailTemplate, EmailTemplateType
from tapir.mail.services.layout import (
    BODY_PLACEHOLDER_CSS_CLASS,
    apply_layout,
)
from tapir.mail.tests.factories import (
    DEFAULT_TAPIR_LAYOUT_CONTENT_PATH,
    DEFAULT_TAPIR_LAYOUT_NAME,
    create_default_tapir_layout,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class DefaultLayoutTemplateTest(TapirIntegrationTest):
    def setUp(self):
        super().setUp()
        self.template = create_default_tapir_layout()

    def test_defaultLayoutTemplate_testFixture_isNotMarkedAsDefault(self):
        self.assertEqual(EmailTemplateType.LAYOUT, self.template.template_type)
        self.assertFalse(self.template.is_default_layout)

    def test_defaultLayoutTemplate_fixtureFile_matchesStoredContent(self):
        expected_content = DEFAULT_TAPIR_LAYOUT_CONTENT_PATH.read_text(encoding="utf-8")

        self.assertEqual(expected_content, self.template.content)

    def test_defaultLayoutTemplate_fixtureFile_containsHeaderBodyMarkerDividerAndFooter(
        self,
    ):
        content = self.template.content

        self.assertIn("Vereinsname", content)
        self.assertIn("<mj-divider", content)
        self.assertIn("Impressum", content)
        self.assertIn(f'css-class="{BODY_PLACEHOLDER_CSS_CLASS}"', content)
        self.assertRegex(content, r"\{\{\s*Body\s*\}\}")

    def test_applyLayout_defaultTapirTemplate_replacesMarkerWithEmailBody(self):
        email_content = (
            "<mjml><mj-body>"
            "<mj-section><mj-column><mj-text>MAIL BODY</mj-text></mj-column></mj-section>"
            "</mj-body></mjml>"
        )

        result = apply_layout(email_content, self.template.content)

        self.assertIn("Vereinsname", result)
        self.assertIn("MAIL BODY", result)
        self.assertIn("Impressum", result)
        self.assertNotRegex(result, r"\{\{\s*Body\s*\}\}")
        self.assertNotIn(BODY_PLACEHOLDER_CSS_CLASS, result)


class LayoutMigrationSeedTest(TapirIntegrationTest):
    def test_migrations_doNotCreateDefaultTapirLayout(self):
        self.assertFalse(
            EmailTemplate.objects.filter(name=DEFAULT_TAPIR_LAYOUT_NAME).exists()
        )
