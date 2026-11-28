import datetime
from unittest.mock import ANY, MagicMock, patch

from rest_framework.exceptions import ValidationError

from tapir.core.services.former_member_address_provider import (
    FormerMemberAddressProvider,
)
from tapir.core.services.mailman.mailing_list_join_validator import (
    MailingListJoinValidator,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(
    FormerMemberAddressProvider,
    "is_former_member_address",
    autospec=True,
    return_value=False,
)
class TestValidateAddressCanJoin(TapirUnitTest):
    def setUp(self):
        mock_timezone(test=self, now=datetime.datetime(2026, 11, 27))

    def test_validateAddressCanJoin_addressDoesNotBelongToAFormerMember_doesNotRaise(
        self, mock_is_former_member_address: MagicMock
    ):
        cache = {}

        MailingListJoinValidator.validate_address_can_join(
            address="a@example.com", cache=cache
        )

        mock_is_former_member_address.assert_called_once_with(
            address="a@example.com", reference_datetime=ANY, cache=cache
        )

    def test_validateAddressCanJoin_addressBelongsToAFormerMember_raisesValidationError(
        self, mock_is_former_member_address: MagicMock
    ):
        mock_is_former_member_address.return_value = True

        with self.assertRaisesMessage(
            ValidationError,
            "Diese Adresse gehört zu einem ehemaligen Mitglied und kann keiner Mailing-Liste beitreten",
        ):
            MailingListJoinValidator.validate_address_can_join(
                address="a@example.com", cache={}
            )
