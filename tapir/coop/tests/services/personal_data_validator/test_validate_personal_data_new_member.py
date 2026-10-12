from unittest.mock import patch, Mock

from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidatePersonalDataNewMember(TapirUnitTest):
    @patch.object(
        MemberPaymentRhythmService,
        "is_payment_rhythm_allowed",
        autospec=True,
        return_value=True,
    )
    @patch("tapir.coop.services.personal_data_validator.IBANValidator", autospec=True)
    @patch.object(
        PersonalDataValidator, "validate_phone_number_is_valid", autospec=True
    )
    @patch.object(
        PersonalDataValidator, "validate_email_address_not_in_use", autospec=True
    )
    def test_validatePersonalDataNewMember_default_validatesPhoneNumber(
        self,
        mock_validate_email_address_not_in_use: Mock,
        mock_validate_phone_number_is_valid: Mock,
        mock_iban_validator: Mock,
        mock_is_payment_rhythm_allowed: Mock,
    ):
        cache = Mock()

        PersonalDataValidator.validate_personal_data_new_member(
            email="test_mail",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            cache=cache,
            check_waiting_list=True,
            payment_rhythm="test_payment_rhythm",
        )

        mock_validate_email_address_not_in_use.assert_called_once_with(
            "test_mail", cache=cache, check_waiting_list=True
        )
        mock_validate_phone_number_is_valid.assert_called_once_with(
            "test_phone_number", cache=cache
        )
        mock_iban_validator.return_value.assert_called_once_with("test_iban")
        mock_is_payment_rhythm_allowed.assert_called_once_with(
            "test_payment_rhythm", cache=cache
        )
