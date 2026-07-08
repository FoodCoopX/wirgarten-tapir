from unittest.mock import patch, Mock

from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.core.config import (
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COMPANY,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.utils.tests_utils import mock_parameter_value
from tapir.waiting_list.services.waiting_list_entry_confirmation_validator import (
    WaitingListEntryConfirmationValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateNewMemberData(TapirUnitTest):
    @patch.object(
        WaitingListEntryConfirmationValidator,
        "validate_association_content",
        autospec=True,
    )
    @patch.object(
        WaitingListEntryConfirmationValidator,
        "validate_number_of_shares",
        autospec=True,
    )
    @patch.object(
        TapirOrderBuilder, "build_tapir_order_from_waiting_list_entry", autospec=True
    )
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateNewMemberData_legalStatusIsCooperative_validatesPersonalDataAndCoopData(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_build_tapir_order_from_waiting_list_entry: Mock,
        mock_validate_number_of_shares: Mock,
        mock_validate_association_content: Mock,
    ):
        waiting_list_entry = Mock()
        waiting_list_entry.email = "test_email"
        waiting_list_entry.phone_number = "test_phone_number"
        cache = {}
        mock_parameter_value(
            cache=cache,
            value=LEGAL_STATUS_COOPERATIVE,
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS,
        )
        validated_data = {
            "iban": "test_iban",
            "account_owner": "test_account_owner",
            "payment_rhythm": "test_payment_rhythm",
            "number_of_coop_shares": 5,
        }
        order = Mock()
        mock_build_tapir_order_from_waiting_list_entry.return_value = order

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
        mock_validate_number_of_shares.assert_called_once_with(
            order=order, desired_number_of_coop_shares=5, cache=cache
        )
        mock_validate_association_content.assert_not_called()

    @patch.object(
        WaitingListEntryConfirmationValidator,
        "validate_association_content",
        autospec=True,
    )
    @patch.object(
        WaitingListEntryConfirmationValidator,
        "validate_number_of_shares",
        autospec=True,
    )
    @patch.object(
        TapirOrderBuilder, "build_tapir_order_from_waiting_list_entry", autospec=True
    )
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateNewMemberData_legalStatusIsAssociation_validatesPersonalDataAndAssociationData(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_build_tapir_order_from_waiting_list_entry: Mock,
        mock_validate_number_of_shares: Mock,
        mock_validate_association_content: Mock,
    ):
        waiting_list_entry = Mock()
        waiting_list_entry.email = "test_email"
        waiting_list_entry.phone_number = "test_phone_number"
        cache = {}
        mock_parameter_value(
            cache=cache,
            value=LEGAL_STATUS_ASSOCIATION,
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS,
        )
        validated_data = {
            "iban": "test_iban",
            "account_owner": "test_account_owner",
            "payment_rhythm": "test_payment_rhythm",
            "association_membership_type_id": "test_type_id",
        }
        order = Mock()
        mock_build_tapir_order_from_waiting_list_entry.return_value = order

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
        mock_validate_number_of_shares.assert_not_called()
        mock_validate_association_content.assert_called_once_with(
            association_membership_type_id="test_type_id"
        )

    @patch.object(
        WaitingListEntryConfirmationValidator,
        "validate_association_content",
        autospec=True,
    )
    @patch.object(
        WaitingListEntryConfirmationValidator,
        "validate_number_of_shares",
        autospec=True,
    )
    @patch.object(
        TapirOrderBuilder, "build_tapir_order_from_waiting_list_entry", autospec=True
    )
    @patch.object(
        PersonalDataValidator, "validate_personal_data_new_member", autospec=True
    )
    def test_validateNewMemberData_legalStatusIsCompany_validatesPersonalDataOnly(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_build_tapir_order_from_waiting_list_entry: Mock,
        mock_validate_number_of_shares: Mock,
        mock_validate_association_content: Mock,
    ):
        waiting_list_entry = Mock()
        waiting_list_entry.email = "test_email"
        waiting_list_entry.phone_number = "test_phone_number"
        cache = {}
        mock_parameter_value(
            cache=cache,
            value=LEGAL_STATUS_COMPANY,
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS,
        )
        validated_data = {
            "iban": "test_iban",
            "account_owner": "test_account_owner",
            "payment_rhythm": "test_payment_rhythm",
            "association_membership_type_id": "test_type_id",
        }
        order = Mock()
        mock_build_tapir_order_from_waiting_list_entry.return_value = order

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
        mock_validate_number_of_shares.assert_not_called()
        mock_validate_association_content.assert_not_called()
