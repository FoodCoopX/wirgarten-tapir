from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.services.data_import_utils import DataImportUtils
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestParseMemberNumber(TapirUnitTest):
    @staticmethod
    def _build_cache(prefix: str) -> dict:
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.MEMBER_NUMBER_PREFIX, value=prefix
        )
        return cache

    def test_parseMemberNumber_emptyValue_returnsNone(self):
        result = DataImportUtils.parse_member_number(
            value="  ", cache=self._build_cache(prefix="WG")
        )

        self.assertIsNone(result)

    def test_parseMemberNumber_rawNumber_returnsNumber(self):
        result = DataImportUtils.parse_member_number(
            value=" 0042 ", cache=self._build_cache(prefix="WG")
        )

        self.assertEqual(42, result)

    def test_parseMemberNumber_prefixedNumber_returnsNumberWithoutPrefix(self):
        result = DataImportUtils.parse_member_number(
            value="WG0042", cache=self._build_cache(prefix="WG")
        )

        self.assertEqual(42, result)

    def test_parseMemberNumber_emptyPrefix_returnsNumber(self):
        result = DataImportUtils.parse_member_number(
            value="42", cache=self._build_cache(prefix="")
        )

        self.assertEqual(42, result)

    def test_parseMemberNumber_otherPrefix_raisesException(self):
        with self.assertRaisesMessage(
            TapirDataImportException, "Invalid member number: 'XY0042'"
        ):
            DataImportUtils.parse_member_number(
                value="XY0042", cache=self._build_cache(prefix="WG")
            )
