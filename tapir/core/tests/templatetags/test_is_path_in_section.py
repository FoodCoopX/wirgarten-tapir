from tapir.core.templatetags.core import is_path_in_section
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestIsPathInSection(TapirUnitTest):
    def test_isPathInSection_pathIsSectionUrl_returnsTrue(self):
        self.assertTrue(
            is_path_in_section(path="/tapirmail/", section_url="/tapirmail/")
        )

    def test_isPathInSection_pathIsSubpage_returnsTrue(self):
        self.assertTrue(
            is_path_in_section(
                path="/tapirmail/emailconfiguration/edit/123",
                section_url="/tapirmail/",
            )
        )

    def test_isPathInSection_sectionUrlWithoutTrailingSlash_returnsTrueForSubpage(
        self,
    ):
        self.assertTrue(
            is_path_in_section(path="/tapir/members/123", section_url="/tapir/members")
        )

    def test_isPathInSection_pathOnlySharesTheBeginningOfTheName_returnsFalse(self):
        self.assertFalse(
            is_path_in_section(path="/tapir/members_old", section_url="/tapir/members")
        )

    def test_isPathInSection_otherSection_returnsFalse(self):
        self.assertFalse(
            is_path_in_section(path="/tapir/contracts", section_url="/tapirmail/")
        )
