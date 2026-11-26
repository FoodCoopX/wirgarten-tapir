from tapir.mail.exceptions import TapirMailException
from tapir.mail.services.layout import (
    BODY_PLACEHOLDER_CSS_CLASS,
    apply_layout,
    extract_mj_body_inner,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class LayoutTest(TapirUnitTest):
    BODY = (
        "<mjml><mj-head></mj-head><mj-body>"
        "<mj-text>Hello</mj-text>"
        "</mj-body></mjml>"
    )
    LAYOUT_WITH_TOKEN = (
        "<mjml><mj-head></mj-head><mj-body>"
        "<mj-text>HEAD</mj-text>{{Body}}<mj-text>FOOT</mj-text>"
        "</mj-body></mjml>"
    )
    LAYOUT_WITH_MARKER = (
        "<mjml><mj-body>"
        "<mj-section><mj-column><mj-text>HEAD</mj-text></mj-column></mj-section>"
        f'<mj-section css-class="{BODY_PLACEHOLDER_CSS_CLASS}">'
        "<mj-column><mj-text>{{Body}}</mj-text></mj-column></mj-section>"
        "<mj-section><mj-column><mj-text>FOOT</mj-text></mj-column></mj-section>"
        "</mj-body></mjml>"
    )

    def test_extractMjBodyInner_mjmlWithBody_returnsInnerContent(self):
        self.assertEqual("<mj-text>Hello</mj-text>", extract_mj_body_inner(self.BODY))

    def test_extractMjBodyInner_mjmlWithoutBody_returnsInputUnchanged(self):
        self.assertEqual(
            "<mj-text>Hello</mj-text>",
            extract_mj_body_inner("<mj-text>Hello</mj-text>"),
        )

    def test_applyLayout_layoutWithMarkerSection_replacesWholeSectionWithBody(self):
        result = apply_layout(self.BODY, self.LAYOUT_WITH_MARKER)

        self.assertIn("<mj-text>HEAD</mj-text>", result)
        self.assertIn("<mj-text>Hello</mj-text>", result)
        self.assertIn("<mj-text>FOOT</mj-text>", result)
        self.assertNotIn("{{Body}}", result)
        self.assertNotIn(BODY_PLACEHOLDER_CSS_CLASS, result)

    def test_applyLayout_layoutWithoutMarkerSection_raisesException(self):
        with self.assertRaises(TapirMailException):
            apply_layout(self.BODY, self.LAYOUT_WITH_TOKEN)

    def test_applyLayout_bodyWithoutMjBodyWrapper_insertsBodyAsIs(self):
        result = apply_layout("<mj-text>Hello</mj-text>", self.LAYOUT_WITH_MARKER)

        self.assertIn("<mj-text>HEAD</mj-text>", result)
        self.assertIn("<mj-text>Hello</mj-text>", result)
        self.assertIn("<mj-text>FOOT</mj-text>", result)
