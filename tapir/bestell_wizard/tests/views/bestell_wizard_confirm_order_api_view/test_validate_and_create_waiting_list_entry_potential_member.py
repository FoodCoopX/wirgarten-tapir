from unittest.mock import patch, Mock

from django.test import SimpleTestCase
from tapir_mail.triggers.transactional_trigger import TransactionalTriggerData

from tapir.bestell_wizard.views import BestellWizardConfirmOrderApiView
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.waiting_list.services.waiting_list_entry_confirmation_email_sender import (
    WaitingListEntryConfirmationEmailSender,
)
from tapir.waiting_list.services.waiting_list_entry_creator import (
    WaitingListEntryCreator,
)
from tapir.waiting_list.services.waiting_list_entry_validator import (
    WaitingListEntryValidator,
)


class TestValidateAndCreateWaitingListEntryPotentialMember(SimpleTestCase):
    @patch.object(
        WaitingListEntryConfirmationEmailSender, "send_confirmation_mail", autospec=True
    )
    @patch.object(
        WaitingListEntryCreator, "create_entry_potential_member", autospec=True
    )
    @patch.object(
        WaitingListEntryValidator,
        "validate_creation_of_waiting_list_entry_for_a_potential_member",
        autospec=True,
    )
    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    def test_validateAndCreateWaitingListEntryPotentialMember_default_validatesThenCreatesEntryAndSendConfirmationMail(
        self,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
        mock_validate_creation_of_waiting_list_entry_for_a_potential_member: Mock,
        mock_create_entry_potential_member: Mock,
        mock_send_confirmation_mail: Mock,
    ):
        cache = Mock()
        shopping_cart_waiting_list = Mock()
        pickup_location_ids = Mock()
        personal_data = {"email": "test_mail", "first_name": "John", "last_name": "Doe"}
        validated_serializer_data = {
            "shopping_cart_waiting_list": shopping_cart_waiting_list,
            "personal_data": personal_data,
            "number_of_coop_shares": 7,
            "pickup_location_ids": pickup_location_ids,
        }
        waiting_list_order = Mock()
        mock_build_tapir_order_from_shopping_cart_serializer.return_value = (
            waiting_list_order
        )
        entry = Mock()
        mock_create_entry_potential_member.return_value = entry

        BestellWizardConfirmOrderApiView.validate_and_create_waiting_list_entry_potential_member(
            validated_serializer_data=validated_serializer_data, cache=cache
        )

        mock_build_tapir_order_from_shopping_cart_serializer.assert_called_once_with(
            shopping_cart=shopping_cart_waiting_list, cache=cache
        )
        mock_validate_creation_of_waiting_list_entry_for_a_potential_member.assert_called_once_with(
            order=waiting_list_order,
            email="test_mail",
            number_of_coop_shares=7,
            cache=cache,
        )
        mock_create_entry_potential_member.assert_called_once_with(
            order=waiting_list_order,
            pickup_location_ids_in_priority_order=pickup_location_ids,
            number_of_coop_shares=7,
            personal_data=personal_data,
            cache=cache,
        )
        mock_send_confirmation_mail.assert_called_once_with(
            entry=entry,
            potential_member_info=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                email="test_mail",
                first_name="John",
                last_name="Doe",
            ),
        )
