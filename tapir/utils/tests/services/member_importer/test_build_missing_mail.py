from tapir.utils.services.member_importer import MemberImporter
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestBuildMissingMail(TapirUnitTest):
    def test_buildMissingMail_default_returnsContactMailWithMemberNumberSuffix(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.SITE_EMAIL, value="Kontakt@Solawi.de"
        )

        result = MemberImporter.build_missing_mail(member_no=36, cache=cache)

        self.assertEqual("kontakt+missing_mail_36@solawi.de", result)
