from unittest.mock import patch, Mock

from django.test import SimpleTestCase

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


class TestValidateAndCreateWaitingListEntryExistingMember(SimpleTestCase):
    @patch.object(
        WaitingListEntryConfirmationEmailSender, "send_confirmation_mail", autospec=True
    )
    @patch.object(
        WaitingListEntryCreator, "create_entry_existing_member", autospec=True
    )
    @patch.object(
        WaitingListEntryValidator,
        "validate_creation_of_waiting_list_entry_for_an_existing_member",
        autospec=True,
    )
    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    def test_validateAndCreateWaitingListEntryExistingMember_default_validatesThenCreateEntryAndSendsConfirmationMail(
        self,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
        mock_validate_creation_of_waiting_list_entry_for_an_existing_member: Mock,
        mock_create_entry_existing_member: Mock,
        mock_send_confirmation_mail: Mock,
    ):
        member = Mock()
        member.id = "test_id"
        cache = Mock()
        shopping_cart_waiting_list = Mock()
        shopping_cart_order = Mock()
        waiting_list_order = Mock()
        fulfilled_order = Mock()
        pickup_location_ids = Mock()
        validated_serializer_data = {
            "shopping_cart_waiting_list": shopping_cart_waiting_list,
            "shopping_cart_order": shopping_cart_order,
            "pickup_location_ids": pickup_location_ids,
            "growing_period_id": "growing_period_test_id",
        }
        entry = Mock()

        mock_build_tapir_order_from_shopping_cart_serializer.side_effect = (
            lambda shopping_cart, cache: (
                waiting_list_order
                if shopping_cart == shopping_cart_waiting_list
                else fulfilled_order
            )
        )
        mock_create_entry_existing_member.return_value = entry

        BestellWizardConfirmOrderApiView.validate_and_create_waiting_list_entry_existing_member(
            member=member,
            validated_serializer_data=validated_serializer_data,
            cache=cache,
        )

        mock_build_tapir_order_from_shopping_cart_serializer.assert_called_once_with(
            shopping_cart=shopping_cart_waiting_list, cache=cache
        )
        mock_validate_creation_of_waiting_list_entry_for_an_existing_member.assert_called_once_with(
            member_id="test_id", order=waiting_list_order, cache=cache
        )
        mock_create_entry_existing_member.assert_called_once_with(
            order=waiting_list_order,
            pickup_location_ids_in_priority_order=pickup_location_ids,
            member=member,
            growing_period_id="growing_period_test_id",
            cache=cache,
        )
        mock_send_confirmation_mail.assert_called_once_with(
            entry=entry, existing_member_id="test_id"
        )

    @patch.object(
        WaitingListEntryConfirmationEmailSender, "send_confirmation_mail", autospec=True
    )
    @patch.object(
        WaitingListEntryCreator, "create_entry_existing_member", autospec=True
    )
    @patch.object(
        WaitingListEntryValidator,
        "validate_creation_of_waiting_list_entry_for_an_existing_member",
        autospec=True,
    )
    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    def test_validateAndCreateWaitingListEntryExistingMember_memberAlreadyGotAPickupLocationAssigned_createsEntryWithoutPickupLocationWishes(
        self,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
        mock_validate_creation_of_waiting_list_entry_for_an_existing_member: Mock,
        mock_create_entry_existing_member: Mock,
        mock_send_confirmation_mail: Mock,
    ):
        member = Mock()
        member.id = "test_id"
        cache = Mock()
        shopping_cart_waiting_list = Mock()
        shopping_cart_order = Mock()
        waiting_list_order = Mock()
        fulfilled_order = Mock()
        pickup_location_ids = Mock()
        validated_serializer_data = {
            "shopping_cart_waiting_list": shopping_cart_waiting_list,
            "shopping_cart_order": shopping_cart_order,
            "pickup_location_ids": pickup_location_ids,
            "growing_period_id": "test_growing_period_id",
        }
        entry = Mock()

        mock_build_tapir_order_from_shopping_cart_serializer.side_effect = (
            lambda shopping_cart, cache: (
                waiting_list_order
                if shopping_cart == shopping_cart_waiting_list
                else fulfilled_order
            )
        )
        mock_create_entry_existing_member.return_value = entry

        BestellWizardConfirmOrderApiView.validate_and_create_waiting_list_entry_existing_member(
            member=member,
            validated_serializer_data=validated_serializer_data,
            cache=cache,
        )

        mock_build_tapir_order_from_shopping_cart_serializer.assert_called_once_with(
            shopping_cart=shopping_cart_waiting_list, cache=cache
        )
        mock_validate_creation_of_waiting_list_entry_for_an_existing_member.assert_called_once_with(
            member_id="test_id", order=waiting_list_order, cache=cache
        )
        mock_create_entry_existing_member.assert_called_once_with(
            order=waiting_list_order,
            pickup_location_ids_in_priority_order=pickup_location_ids,
            member=member,
            growing_period_id="test_growing_period_id",
            cache=cache,
        )
        mock_send_confirmation_mail.assert_called_once_with(
            entry=entry, existing_member_id="test_id"
        )
