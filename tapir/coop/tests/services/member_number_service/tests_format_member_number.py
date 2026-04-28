from django.test import SimpleTestCase

from tapir.coop.services.member_number_service import MemberNumberService
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestFormatMemberNumber(SimpleTestCase):
    def test_formatMemberNumber_withPrefixAndPadding_returnsFormattedString(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_PREFIX, value="BT"
        )
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, value=4
        )

        self.assertEqual(
            "BT0017", MemberNumberService.format_member_number(17, cache=cache)
        )

    def test_formatMemberNumber_withoutPadding_returnsUnpaddedString(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_PREFIX, value="BT"
        )
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, value=0
        )

        self.assertEqual(
            "BT17", MemberNumberService.format_member_number(17, cache=cache)
        )

    def test_formatMemberNumber_withoutPrefix_returnsOnlyNumber(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_PREFIX, value=""
        )
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, value=4
        )

        self.assertEqual(
            "0017", MemberNumberService.format_member_number(17, cache=cache)
        )

    def test_formatMemberNumber_withNoneInput_returnsNone(self):
        self.assertIsNone(MemberNumberService.format_member_number(None, cache={}))

    def test_formatMemberNumber_numberLongerThanLength_returnsUntruncatedNumber(self):
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_PREFIX, value=""
        )
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, value=2
        )

        self.assertEqual(
            "12345", MemberNumberService.format_member_number(12345, cache=cache)
        )
