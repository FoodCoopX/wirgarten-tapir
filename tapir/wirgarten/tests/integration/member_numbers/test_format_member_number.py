from tapir.coop.services.member_number_service import MemberNumberService
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestFormatMemberNumber(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_formatMemberNumber_withPrefixAndPadding_returnsFormattedString(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 4)

        self.assertEqual(
            "BT0017", MemberNumberService.format_member_number(17, cache={})
        )

    def test_formatMemberNumber_withoutPadding_returnsUnpaddedString(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "BT")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 0)

        self.assertEqual("BT17", MemberNumberService.format_member_number(17, cache={}))

    def test_formatMemberNumber_withoutPrefix_returnsOnlyNumber(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 4)

        self.assertEqual("0017", MemberNumberService.format_member_number(17, cache={}))

    def test_formatMemberNumber_withNoneInput_returnsNone(self):
        self.assertIsNone(MemberNumberService.format_member_number(None, cache={}))

    def test_formatMemberNumber_numberLongerThanLength_returnsUntruncatedNumber(self):
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_PREFIX, "")
        self._set_parameter(ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, 2)

        self.assertEqual(
            "12345", MemberNumberService.format_member_number(12345, cache={})
        )
