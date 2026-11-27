import datetime
from unittest.mock import MagicMock, patch

from tapir.core.services.former_member_address_provider import (
    FormerMemberAddressProvider,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    FormerMemberAddressProvider, "get_former_member_by_address", autospec=True
)
class TestIsFormerMemberAddress(TapirUnitTest):
    REFERENCE_DATETIME = datetime.datetime(2026, 11, 27, tzinfo=datetime.UTC)

    def test_isFormerMemberAddress_addressBelongsToAFormerMember_returnsTrue(
        self, mock_get_former_member_by_address: MagicMock
    ):
        mock_get_former_member_by_address.return_value = {
            "former@example.com": MemberFactory.build()
        }
        cache = {}

        result = FormerMemberAddressProvider.is_former_member_address(
            address="former@example.com",
            reference_datetime=self.REFERENCE_DATETIME,
            cache=cache,
        )

        self.assertTrue(result)
        mock_get_former_member_by_address.assert_called_once_with(
            reference_datetime=self.REFERENCE_DATETIME, cache=cache
        )

    def test_isFormerMemberAddress_otherAddress_returnsFalse(
        self, mock_get_former_member_by_address: MagicMock
    ):
        mock_get_former_member_by_address.return_value = {
            "former@example.com": MemberFactory.build()
        }

        result = FormerMemberAddressProvider.is_former_member_address(
            address="other@example.com",
            reference_datetime=self.REFERENCE_DATETIME,
            cache={},
        )

        self.assertFalse(result)
