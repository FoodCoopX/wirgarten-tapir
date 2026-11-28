import re

from tapir.mail.exceptions import TapirMailException

# Matches a full <mj-body ...>...</mj-body> element and captures its inner content.
MJ_BODY_RE = re.compile(r"<mj-body[^>]*>(.*)</mj-body>", re.DOTALL)

# Matches the {{Body}} placeholder, tolerating whitespace: {{ Body }}.
BODY_TOKEN_RE = re.compile(r"\{\{\s*Body\s*\}\}")

# The visual editor cannot keep a bare {{Body}} text node at the top level of
# <mj-body>. Layout templates therefore place the placeholder in a normal section
# that carries this CSS class. At render time the whole section is replaced by the
# email body, so no invalid nested sections end up in the result.
BODY_PLACEHOLDER_CSS_CLASS = "tapir-layout-body"
BODY_PLACEHOLDER_SECTION_RE = re.compile(
    r'<mj-section\b(?=[^>]*css-class="[^"]*tapir-layout-body[^"]*")[^>]*>'
    r".*?</mj-section>",
    re.DOTALL,
)


def extract_mj_body_inner(mjml: str) -> str:
    """
    Return the inner content of the <mj-body> element of a full MJML document.
    If the document has no <mj-body> (e.g. a fragment), the input is returned unchanged.
    """
    match = MJ_BODY_RE.search(mjml or "")
    if match is None:
        return mjml
    return match.group(1)


def apply_layout(body_mjml: str, layout_mjml: str) -> str:
    """
    Wrap an email body into a layout template.

    Layout templates must contain a section marked with
    BODY_PLACEHOLDER_CSS_CLASS. That whole section is replaced by the inner
    content of the body's <mj-body> element.
    """
    body_inner = extract_mj_body_inner(body_mjml)

    if not BODY_PLACEHOLDER_SECTION_RE.search(layout_mjml or ""):
        raise TapirMailException("Layout-Vorlage enthält keinen E-Mail-Inhalt-Block.")

    return BODY_PLACEHOLDER_SECTION_RE.sub(lambda _: body_inner, layout_mjml, count=1)


def get_effective_layout(version):
    """
    Resolve the layout template that applies to a version at send time.

    - Versions that existed before the layout feature (layout_enabled == False) never
      get a layout, so their behaviour stays unchanged.
    - Otherwise the explicitly chosen layout is used, falling back to the global
      default layout (which is resolved live at send time).
    """
    if not getattr(version, "layout_enabled", False):
        return None

    if version.layout_template_id:
        return version.layout_template

    from tapir.mail.models import EmailTemplate, EmailTemplateType

    return EmailTemplate.objects.filter(
        template_type=EmailTemplateType.LAYOUT,
        is_default_layout=True,
    ).first()


def render_email_mjml(version) -> str:
    """
    Return the MJML that should actually be rendered for a version: the body wrapped
    in the effective layout, or the raw content when no layout applies.
    """
    layout = get_effective_layout(version)
    if layout is None:
        return version.content
    return apply_layout(version.content, layout.content)
