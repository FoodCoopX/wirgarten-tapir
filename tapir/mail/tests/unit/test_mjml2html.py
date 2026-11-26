from tapir.mail.services.mjml import mjml2html
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestMjml2Html(TapirUnitTest):
    def test_mjml2html_hasCustomFontsInHtml(self):
        html = mjml2html("""<mjml>
  <mj-head>
    <mj-font name="Montserrat" href="http://test/Montserrat.css" />
    <mj-font name="Bitter" href="http://test/Bitter.css" />
  </mj-head>
  <mj-body>
      <mj-wrapper
      padding="20px 0px 20px 0px"
      border="none"
      direction="ltr"
      text-align="center"
    >
      <mj-section
        padding="0px"
        text-align="left"
      >
        <mj-column>
          <mj-text
            padding="10px 25px 10px 25px"
            align="left"
            >This is a dummy email!</mj-text
          >
        </mj-column>
      </mj-section>
    </mj-wrapper>
  </mj-body></mjml>""")

        self.assertIn("@import url(http://test/Montserrat.css)", html)
        self.assertIn(
            """<link href="http://test/Montserrat.css" rel="stylesheet" type="text/css">""",
            html,
        )
        self.assertIn("@import url(http://test/Bitter.css)", html)
        self.assertIn(
            """<link href="http://test/Bitter.css" rel="stylesheet" type="text/css">""",
            html,
        )
