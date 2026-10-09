from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError

from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.core.config import (
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COMPANY,
)
from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.utils.tests_utils import mock_parameter_value
from tapir.waiting_list.services.waiting_list_entry_confirmation_applier import (
    WaitingListEntryConfirmationApplier,
)
from tapir.waiting_list.services.waiting_list_entry_confirmation_validator import (
    WaitingListEntryConfirmationValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateNewMemberData(TapirUnitTest):
    @patch.object(
        SolidarityValidator, "is_the_ordered_solidarity_allowed", autospec=True
    )
    @patch.object(
        WaitingListEntryConfirmationApplier, "get_contract_start_date", autospec=True
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
    def test_validateNewMemberData_legalStatusIsCooperative_validatesPersonalDataAndCoopData(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_build_tapir_order_from_waiting_list_entry: Mock,
        mock_validate_number_of_shares: Mock,
        mock_validate_association_content: Mock,
        mock_get_contract_start_date: Mock,
        mock_is_the_ordered_solidarity_allowed: Mock,
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
            "solidarity_contribution": 12,
        }
        order = Mock()
        contract_start_date = Mock()
        mock_build_tapir_order_from_waiting_list_entry.return_value = order
        mock_get_contract_start_date.return_value = contract_start_date
        mock_is_the_ordered_solidarity_allowed.return_value = True

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
        mock_get_contract_start_date.assert_called_once_with(
            waiting_list_entry=waiting_list_entry, cache=cache
        )
        mock_is_the_ordered_solidarity_allowed.assert_called_once_with(
            amount=12, start_date=contract_start_date, cache=cache
        )

    @patch.object(
        SolidarityValidator, "is_the_ordered_solidarity_allowed", autospec=True
    )
    @patch.object(
        WaitingListEntryConfirmationApplier, "get_contract_start_date", autospec=True
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
    def test_validateNewMemberData_legalStatusIsAssociation_validatesPersonalDataAndAssociationData(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_build_tapir_order_from_waiting_list_entry: Mock,
        mock_validate_number_of_shares: Mock,
        mock_validate_association_content: Mock,
        mock_get_contract_start_date: Mock,
        mock_is_the_ordered_solidarity_allowed: Mock,
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
            "solidarity_contribution": 12,
        }
        order = Mock()
        contract_start_date = Mock()
        mock_build_tapir_order_from_waiting_list_entry.return_value = order
        mock_get_contract_start_date.return_value = contract_start_date
        mock_is_the_ordered_solidarity_allowed.return_value = True

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
        mock_get_contract_start_date.assert_called_once_with(
            waiting_list_entry=waiting_list_entry, cache=cache
        )
        mock_is_the_ordered_solidarity_allowed.assert_called_once_with(
            amount=12, start_date=contract_start_date, cache=cache
        )

    @patch.object(
        SolidarityValidator, "is_the_ordered_solidarity_allowed", autospec=True
    )
    @patch.object(
        WaitingListEntryConfirmationApplier, "get_contract_start_date", autospec=True
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
        mock_get_contract_start_date: Mock,
        mock_is_the_ordered_solidarity_allowed: Mock,
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
            "solidarity_contribution": 12,
        }
        order = Mock()
        contract_start_date = Mock()
        mock_build_tapir_order_from_waiting_list_entry.return_value = order
        mock_get_contract_start_date.return_value = contract_start_date
        mock_is_the_ordered_solidarity_allowed.return_value = True

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
        mock_get_contract_start_date.assert_called_once_with(
            waiting_list_entry=waiting_list_entry, cache=cache
        )
        mock_is_the_ordered_solidarity_allowed.assert_called_once_with(
            amount=12, start_date=contract_start_date, cache=cache
        )

    @patch.object(
        SolidarityValidator, "is_the_ordered_solidarity_allowed", autospec=True
    )
    @patch.object(
        WaitingListEntryConfirmationApplier, "get_contract_start_date", autospec=True
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
    def test_validateNewMemberData_solidarityContributionIsTooLow_raisesValidationError(
        self,
        mock_validate_personal_data_new_member: Mock,
        mock_build_tapir_order_from_waiting_list_entry: Mock,
        mock_validate_number_of_shares: Mock,
        mock_validate_association_content: Mock,
        mock_get_contract_start_date: Mock,
        mock_is_the_ordered_solidarity_allowed: Mock,
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
            "solidarity_contribution": -16,
        }
        contract_start_date = Mock()
        mock_get_contract_start_date.return_value = contract_start_date
        mock_is_the_ordered_solidarity_allowed.return_value = False

        with self.assertRaises(ValidationError) as error:
            WaitingListEntryConfirmationValidator.validate_new_member_data(
                waiting_list_entry=waiting_list_entry,
                validated_data=validated_data,
                cache=cache,
            )

        self.assertEqual(
            "Solidarbeitrag ungültig oder zu niedrig", error.exception.message
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
        mock_get_contract_start_date.assert_called_once_with(
            waiting_list_entry=waiting_list_entry, cache=cache
        )
        mock_is_the_ordered_solidarity_allowed.assert_called_once_with(
            amount=-16, start_date=contract_start_date, cache=cache
        )
