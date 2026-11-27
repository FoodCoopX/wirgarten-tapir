from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError

from tapir.core.services.member_extra_email_confirmation_validator import (
    MemberExtraEmailConfirmationValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    TapirCache,
    "get_confirmed_member_extra_email_with_address",
    autospec=True,
    return_value=None,
)
@patch.object(TapirCache, "is_member_main_address", autospec=True, return_value=False)
class TestValidateAddressIsFree(TapirUnitTest):
    def test_validateAddressIsFree_addressIsFree_doesNotRaise(
        self, _: MagicMock, __: MagicMock
    ):
        extra_email = MemberExtraEmailFactory.build(email="extra@example.com")

        MemberExtraEmailConfirmationValidator.validate_address_is_free(
            extra_email=extra_email, cache={}
        )

    def test_validateAddressIsFree_addressIsAMainAddress_raises(
        self, mock_is_member_main_address: MagicMock, _: MagicMock
    ):
        mock_is_member_main_address.return_value = True
        extra_email = MemberExtraEmailFactory.build(email="extra@example.com")
        cache = {}

        with self.assertRaisesMessage(
            ValidationError,
            "Diese Adresse ist bereits die Hauptadresse eines Mitglieds",
        ):
            MemberExtraEmailConfirmationValidator.validate_address_is_free(
                extra_email=extra_email, cache=cache
            )
        mock_is_member_main_address.assert_called_once_with(
            address="extra@example.com", cache=cache
        )

    def test_validateAddressIsFree_addressIsConfirmedForAnotherExtra_raises(
        self, _: MagicMock, mock_get_confirmed_extra: MagicMock
    ):
        extra_email = MemberExtraEmailFactory.build(email="extra@example.com")
        mock_get_confirmed_extra.return_value = MemberExtraEmailFactory.build(
            email="extra@example.com"
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Diese Adresse ist bereits als zusätzliche Adresse eines anderen Mitglieds bestätigt",
        ):
            MemberExtraEmailConfirmationValidator.validate_address_is_free(
                extra_email=extra_email, cache={}
            )

    def test_validateAddressIsFree_onlyConfirmedExtraIsItself_doesNotRaise(
        self, _: MagicMock, mock_get_confirmed_extra: MagicMock
    ):
        extra_email = MemberExtraEmailFactory.build(email="extra@example.com")
        mock_get_confirmed_extra.return_value = extra_email

        MemberExtraEmailConfirmationValidator.validate_address_is_free(
            extra_email=extra_email, cache={}
        )
