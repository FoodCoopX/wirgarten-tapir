from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.waiting_list.services.waiting_list_entry_confirmation_validator import (
    WaitingListEntryConfirmationValidator,
)


class TestValidateNewMemberData(SimpleTestCase):
    @patch.object(
        MinimumNumberOfSharesValidator,
        "get_minimum_number_of_shares_for_tapir_order",
        autospec=True,
    )
    @patch.object(
        TapirOrderBuilder, "build_tapir_order_from_waiting_list_entry", autospec=True
    )
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateNewMemberData_default_validatesEverything(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_build_tapir_order_from_waiting_list_entry: Mock,
        mock_get_minimum_number_of_shares_for_tapir_order: Mock,
    ):
        waiting_list_entry = Mock()
        waiting_list_entry.email = "test_email"
        waiting_list_entry.phone_number = "test_phone_number"
        cache = Mock()
        validated_data = {
            "iban": "test_iban",
            "account_owner": "test_account_owner",
            "payment_rhythm": "test_payment_rhythm",
            "number_of_coop_shares": 5,
        }
        order = Mock()
        mock_build_tapir_order_from_waiting_list_entry.return_value = order
        mock_get_minimum_number_of_shares_for_tapir_order.return_value = 2

        WaitingListEntryConfirmationValidator.validate_new_member_data(
            waiting_list_entry=waiting_list_entry,
            validated_data=validated_data,
            cache=cache,
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_email",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            payment_rhythm="test_payment_rhythm",
            cache=cache,
            check_waiting_list=False,
        )
        mock_build_tapir_order_from_waiting_list_entry.assert_called_once_with(
            waiting_list_entry
        )
        mock_get_minimum_number_of_shares_for_tapir_order.assert_called_once_with(
            order, cache=cache
        )

    @patch.object(
        MinimumNumberOfSharesValidator,
        "get_minimum_number_of_shares_for_tapir_order",
        autospec=True,
    )
    @patch.object(
        TapirOrderBuilder, "build_tapir_order_from_waiting_list_entry", autospec=True
    )
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateNewMemberData_numberOfSharesIsEqualToMinimum_noExceptionRaised(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_build_tapir_order_from_waiting_list_entry: Mock,
        mock_get_minimum_number_of_shares_for_tapir_order: Mock,
    ):
        waiting_list_entry = Mock()
        waiting_list_entry.email = "test_email"
        waiting_list_entry.phone_number = "test_phone_number"
        cache = Mock()
        validated_data = {
            "iban": "test_iban",
            "account_owner": "test_account_owner",
            "payment_rhythm": "test_payment_rhythm",
            "number_of_coop_shares": 5,
        }
        order = Mock()
        mock_build_tapir_order_from_waiting_list_entry.return_value = order
        mock_get_minimum_number_of_shares_for_tapir_order.return_value = 5

        WaitingListEntryConfirmationValidator.validate_new_member_data(
            waiting_list_entry=waiting_list_entry,
            validated_data=validated_data,
            cache=cache,
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_email",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            payment_rhythm="test_payment_rhythm",
            cache=cache,
            check_waiting_list=False,
        )
        mock_build_tapir_order_from_waiting_list_entry.assert_called_once_with(
            waiting_list_entry
        )
        mock_get_minimum_number_of_shares_for_tapir_order.assert_called_once_with(
            order, cache=cache
        )

    @patch.object(
        MinimumNumberOfSharesValidator,
        "get_minimum_number_of_shares_for_tapir_order",
        autospec=True,
    )
    @patch.object(
        TapirOrderBuilder, "build_tapir_order_from_waiting_list_entry", autospec=True
    )
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateNewMemberData_numberOfSharesIsLessThanMinimum_exceptionRaised(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_build_tapir_order_from_waiting_list_entry: Mock,
        mock_get_minimum_number_of_shares_for_tapir_order: Mock,
    ):
        waiting_list_entry = Mock()
        waiting_list_entry.email = "test_email"
        waiting_list_entry.phone_number = "test_phone_number"
        cache = Mock()
        validated_data = {
            "iban": "test_iban",
            "account_owner": "test_account_owner",
            "payment_rhythm": "test_payment_rhythm",
            "number_of_coop_shares": 5,
        }
        order = Mock()
        mock_build_tapir_order_from_waiting_list_entry.return_value = order
        mock_get_minimum_number_of_shares_for_tapir_order.return_value = 10

        with self.assertRaises(ValidationError) as error:
            WaitingListEntryConfirmationValidator.validate_new_member_data(
                waiting_list_entry=waiting_list_entry,
                validated_data=validated_data,
                cache=cache,
            )

        self.assertEqual(
            "Diese Bestellung erfordert mindestens 10 Genossenschaftsanteile",
            error.exception.message,
        )

        mock_validate_personal_data_new_member.assert_called_once_with(
            email="test_email",
            phone_number="test_phone_number",
            iban="test_iban",
            account_owner="test_account_owner",
            payment_rhythm="test_payment_rhythm",
            cache=cache,
            check_waiting_list=False,
        )
        mock_build_tapir_order_from_waiting_list_entry.assert_called_once_with(
            waiting_list_entry
        )
        mock_get_minimum_number_of_shares_for_tapir_order.assert_called_once_with(
            order, cache=cache
        )
