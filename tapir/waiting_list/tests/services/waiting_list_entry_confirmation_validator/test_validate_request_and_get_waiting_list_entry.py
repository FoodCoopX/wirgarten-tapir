from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.waiting_list.services.waiting_list_entry_confirmation_validator import (
    WaitingListEntryConfirmationValidator,
)


class TestValidateRequestAndGetWaitingListEntry(TapirUnitTest):
    @patch.object(
        WaitingListEntryConfirmationValidator, "validate_new_member_data", autospec=True
    )
    @patch.object(
        WaitingListEntryConfirmationValidator,
        "get_entry_by_id_and_validate_link_key",
        autospec=True,
    )
    def test_validateRequestAndGetWaitingListEntry_memberDoesntExistYet_validatesNewMemberData(
        self,
        mock_get_entry_by_id_and_validate_link_key: Mock,
        mock_validate_new_member_data: Mock,
    ):
        mock_waiting_list_entry = Mock()
        mock_waiting_list_entry.product_wishes.exists.return_value = False
        mock_waiting_list_entry.member = None

        mock_get_entry_by_id_and_validate_link_key.return_value = (
            mock_waiting_list_entry
        )
        validated_data = {"entry_id": "test_entry_id", "link_key": "test_link_key"}
        cache = {}

        result = WaitingListEntryConfirmationValidator.validate_request_and_get_waiting_list_entry(
            validated_data=validated_data, cache=cache
        )

        self.assertEqual(mock_waiting_list_entry, result)
        mock_get_entry_by_id_and_validate_link_key.assert_called_once_with(
            entry_id="test_entry_id", link_key="test_link_key"
        )
        mock_validate_new_member_data.assert_called_once_with(
            waiting_list_entry=mock_waiting_list_entry,
            validated_data=validated_data,
            cache=cache,
        )

    @patch.object(
        WaitingListEntryConfirmationValidator, "validate_new_member_data", autospec=True
    )
    @patch.object(
        WaitingListEntryConfirmationValidator,
        "get_entry_by_id_and_validate_link_key",
        autospec=True,
    )
    def test_validateRequestAndGetWaitingListEntry_memberAlreadyExists_doesntValidatesNewMemberData(
        self,
        mock_get_entry_by_id_and_validate_link_key: Mock,
        mock_validate_new_member_data: Mock,
    ):
        mock_waiting_list_entry = Mock()
        mock_waiting_list_entry.product_wishes.exists.return_value = False
        mock_waiting_list_entry.member = Mock()

        mock_get_entry_by_id_and_validate_link_key.return_value = (
            mock_waiting_list_entry
        )
        validated_data = {"entry_id": "test_entry_id", "link_key": "test_link_key"}
        cache = {}

        result = WaitingListEntryConfirmationValidator.validate_request_and_get_waiting_list_entry(
            validated_data=validated_data, cache=cache
        )

        self.assertEqual(mock_waiting_list_entry, result)
        mock_get_entry_by_id_and_validate_link_key.assert_called_once_with(
            entry_id="test_entry_id", link_key="test_link_key"
        )
        mock_validate_new_member_data.assert_not_called()

    @patch.object(
        WaitingListEntryConfirmationValidator,
        "get_entry_by_id_and_validate_link_key",
        autospec=True,
    )
    def test_validateRequestAndGetWaitingListEntry_noProductWishes_dontCheckSepaAndContract(
        self, mock_get_entry_by_id_and_validate_link_key: Mock
    ):
        mock_waiting_list_entry = Mock()
        mock_waiting_list_entry.product_wishes.exists.return_value = False
        mock_waiting_list_entry.member = Mock()

        mock_get_entry_by_id_and_validate_link_key.return_value = (
            mock_waiting_list_entry
        )
        validated_data = {
            "entry_id": "test_entry_id",
            "link_key": "test_link_key",
            "sepa_allowed": False,
            "contract_accepted": False,
        }
        cache = {}

        result = WaitingListEntryConfirmationValidator.validate_request_and_get_waiting_list_entry(
            validated_data=validated_data, cache=cache
        )

        self.assertEqual(mock_waiting_list_entry, result)
        mock_get_entry_by_id_and_validate_link_key.assert_called_once_with(
            entry_id="test_entry_id", link_key="test_link_key"
        )

    @patch.object(
        WaitingListEntryConfirmationValidator,
        "get_entry_by_id_and_validate_link_key",
        autospec=True,
    )
    def test_validateRequestAndGetWaitingListEntry_sepaNotAllowed_raisesValidationError(
        self, mock_get_entry_by_id_and_validate_link_key: Mock
    ):
        mock_waiting_list_entry = Mock()
        mock_waiting_list_entry.product_wishes.exists.return_value = True
        mock_waiting_list_entry.member = Mock()

        mock_get_entry_by_id_and_validate_link_key.return_value = (
            mock_waiting_list_entry
        )
        validated_data = {
            "entry_id": "test_entry_id",
            "link_key": "test_link_key",
            "sepa_allowed": False,
            "contract_accepted": True,
        }
        cache = {}

        with self.assertRaises(ValidationError) as error:
            WaitingListEntryConfirmationValidator.validate_request_and_get_waiting_list_entry(
                validated_data=validated_data, cache=cache
            )

        self.assertEqual("SEPA-Mandat muss erlaubt sein", error.exception.message)

        mock_get_entry_by_id_and_validate_link_key.assert_called_once_with(
            entry_id="test_entry_id", link_key="test_link_key"
        )

    @patch.object(
        WaitingListEntryConfirmationValidator,
        "get_entry_by_id_and_validate_link_key",
        autospec=True,
    )
    def test_validateRequestAndGetWaitingListEntry_contractNotAccepted_raisesValidationError(
        self, mock_get_entry_by_id_and_validate_link_key: Mock
    ):
        mock_waiting_list_entry = Mock()
        mock_waiting_list_entry.product_wishes.exists.return_value = True
        mock_waiting_list_entry.member = Mock()

        mock_get_entry_by_id_and_validate_link_key.return_value = (
            mock_waiting_list_entry
        )
        validated_data = {
            "entry_id": "test_entry_id",
            "link_key": "test_link_key",
            "sepa_allowed": True,
            "contract_accepted": False,
        }
        cache = {}

        with self.assertRaises(ValidationError) as error:
            WaitingListEntryConfirmationValidator.validate_request_and_get_waiting_list_entry(
                validated_data=validated_data, cache=cache
            )

        self.assertEqual(
            "Vertragsgrundsätze müssen akzeptiert sein", error.exception.message
        )

        mock_get_entry_by_id_and_validate_link_key.assert_called_once_with(
            entry_id="test_entry_id", link_key="test_link_key"
        )

    @patch.object(
        WaitingListEntryConfirmationValidator, "validate_new_member_data", autospec=True
    )
    @patch.object(
        WaitingListEntryConfirmationValidator,
        "get_entry_by_id_and_validate_link_key",
        autospec=True,
    )
    def test_validateRequestAndGetWaitingListEntry_default_validatesEverythingAndReturnsWaitingListEntry(
        self,
        mock_get_entry_by_id_and_validate_link_key: Mock,
        mock_validate_new_member_data: Mock,
    ):
        mock_waiting_list_entry = Mock()
        mock_waiting_list_entry.product_wishes.exists.return_value = True
        mock_waiting_list_entry.member = None

        mock_get_entry_by_id_and_validate_link_key.return_value = (
            mock_waiting_list_entry
        )
        validated_data = {
            "entry_id": "test_entry_id",
            "link_key": "test_link_key",
            "sepa_allowed": True,
            "contract_accepted": True,
        }
        cache = {}

        result = WaitingListEntryConfirmationValidator.validate_request_and_get_waiting_list_entry(
            validated_data=validated_data, cache=cache
        )

        self.assertEqual(mock_waiting_list_entry, result)
        mock_get_entry_by_id_and_validate_link_key.assert_called_once_with(
            entry_id="test_entry_id", link_key="test_link_key"
        )
        mock_validate_new_member_data.assert_called_once_with(
            waiting_list_entry=mock_waiting_list_entry,
            validated_data=validated_data,
            cache=cache,
        )
