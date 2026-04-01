import datetime
from unittest.mock import patch, Mock, call

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.bestell_wizard.views import BestellWizardConfirmOrderApiView
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestValidateEverythingAndApplyAllChanges(SimpleTestCase):
    def setUp(self):
        self.now = mock_timezone(self, datetime.datetime(year=2021, month=9, day=12))

    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_existing_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_potential_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView, "validate_and_fulfill_order", autospec=True
    )
    def test_validateEverythingAndApplyAllChanges_privacyPolicyNotRead_raisesValidationException(
        self, *mocks
    ):
        validated_serializer_data = {
            "privacy_policy_read": False,
        }

        with self.assertRaises(ValidationError):
            BestellWizardConfirmOrderApiView.validate_everything_and_apply_all_changes(
                validated_serializer_data=validated_serializer_data,
                request=None,
                cache={},
            )

        for mock in mocks:
            mock.assert_not_called()

    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_existing_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_potential_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView, "validate_and_fulfill_order", autospec=True
    )
    def test_validateEverythingAndApplyAllChanges_orderIsNotEmpty_callsValidateAndFulfillOrder(
        self,
        mock_validate_and_fulfill_order: Mock,
        mock_validate_and_create_waiting_list_entry_potential_member: Mock,
        mock_validate_and_create_waiting_list_entry_existing_member: Mock,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
    ):
        shopping_cart_order = Mock()
        cache = Mock()
        request = Mock()
        growing_period = GrowingPeriodFactory.build()
        validated_serializer_data = {
            "privacy_policy_read": True,
            "shopping_cart_order": shopping_cart_order,
            "become_member_now": None,
            "shopping_cart_waiting_list": {},
            "growing_period_id": growing_period.id,
            "pickup_location_ids": [],
        }

        mock_build_tapir_order_from_shopping_cart_serializer.side_effect = (
            lambda data, cache: ({Mock: 2} if data == shopping_cart_order else {})
        )

        BestellWizardConfirmOrderApiView.validate_everything_and_apply_all_changes(
            validated_serializer_data=validated_serializer_data,
            request=request,
            cache=cache,
        )

        mock_build_tapir_order_from_shopping_cart_serializer.assert_has_calls(
            [call(shopping_cart_order, cache=cache)]
        )
        mock_validate_and_fulfill_order.assert_called_once_with(
            request=request,
            validated_serializer_data=validated_serializer_data,
            cache=cache,
        )
        mock_validate_and_create_waiting_list_entry_potential_member.assert_not_called()
        mock_validate_and_create_waiting_list_entry_existing_member.assert_not_called()

    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_existing_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_potential_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView, "validate_and_fulfill_order", autospec=True
    )
    def test_validateEverythingAndApplyAllChanges_orderIsEmptyButBecomeMemberNowIsTrue_callsValidateAndFulfillOrder(
        self,
        mock_validate_and_fulfill_order: Mock,
        mock_validate_and_create_waiting_list_entry_potential_member: Mock,
        mock_validate_and_create_waiting_list_entry_existing_member: Mock,
    ):
        cache = Mock()
        request = Mock()
        growing_period = GrowingPeriodFactory.build()
        validated_serializer_data = {
            "privacy_policy_read": True,
            "shopping_cart_order": {},
            "become_member_now": True,
            "shopping_cart_waiting_list": {},
            "growing_period_id": growing_period.id,
            "pickup_location_ids": [],
        }

        BestellWizardConfirmOrderApiView.validate_everything_and_apply_all_changes(
            validated_serializer_data=validated_serializer_data,
            request=request,
            cache=cache,
        )

        mock_validate_and_fulfill_order.assert_called_once_with(
            request=request,
            validated_serializer_data=validated_serializer_data,
            cache=cache,
        )
        mock_validate_and_create_waiting_list_entry_potential_member.assert_not_called()
        mock_validate_and_create_waiting_list_entry_existing_member.assert_not_called()

    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_existing_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_potential_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView, "validate_and_fulfill_order", autospec=True
    )
    def test_validateEverythingAndApplyAllChanges_memberNotCreatedAndWaitingListOrderNotEmpty_callsCorrectWaitingListCreationFunction(
        self,
        mock_validate_and_fulfill_order: Mock,
        mock_validate_and_create_waiting_list_entry_potential_member: Mock,
        mock_validate_and_create_waiting_list_entry_existing_member: Mock,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
    ):
        shopping_cart_order = Mock()
        shopping_cart_waiting_list = Mock()
        cache = Mock()
        request = Mock()
        growing_period = GrowingPeriodFactory.build()
        validated_serializer_data = {
            "privacy_policy_read": True,
            "shopping_cart_order": shopping_cart_order,
            "become_member_now": False,
            "shopping_cart_waiting_list": shopping_cart_waiting_list,
            "growing_period_id": growing_period.id,
        }

        mock_build_tapir_order_from_shopping_cart_serializer.side_effect = (
            lambda data, cache: (
                {Mock: 2} if data == shopping_cart_waiting_list else {}
            )
        )

        BestellWizardConfirmOrderApiView.validate_everything_and_apply_all_changes(
            validated_serializer_data=validated_serializer_data,
            request=request,
            cache=cache,
        )

        mock_build_tapir_order_from_shopping_cart_serializer.assert_has_calls(
            [
                call(shopping_cart_order, cache=cache),
                call(shopping_cart_waiting_list, cache=cache),
            ]
        )
        mock_validate_and_fulfill_order.assert_not_called()
        mock_validate_and_create_waiting_list_entry_potential_member.assert_called_once_with(
            validated_serializer_data=validated_serializer_data, cache=cache
        )
        mock_validate_and_create_waiting_list_entry_existing_member.assert_not_called()

    @patch.object(
        TapirOrderBuilder,
        "build_tapir_order_from_shopping_cart_serializer",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_existing_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView,
        "validate_and_create_waiting_list_entry_potential_member",
        autospec=True,
    )
    @patch.object(
        BestellWizardConfirmOrderApiView, "validate_and_fulfill_order", autospec=True
    )
    def test_validateEverythingAndApplyAllChanges_memberCreatedAndWaitingListOrderNotEmpty_callsCorrectWaitingListCreationFunction(
        self,
        mock_validate_and_fulfill_order: Mock,
        mock_validate_and_create_waiting_list_entry_potential_member: Mock,
        mock_validate_and_create_waiting_list_entry_existing_member: Mock,
        mock_build_tapir_order_from_shopping_cart_serializer: Mock,
    ):
        shopping_cart_order = Mock()
        shopping_cart_waiting_list = Mock()
        cache = Mock()
        request = Mock()
        member = Mock()
        pickup_location_ids = Mock()
        growing_period = GrowingPeriodFactory.build()
        validated_serializer_data = {
            "privacy_policy_read": True,
            "shopping_cart_order": shopping_cart_order,
            "become_member_now": False,
            "shopping_cart_waiting_list": shopping_cart_waiting_list,
            "growing_period_id": growing_period.id,
            "pickup_location_ids": pickup_location_ids,
        }

        mock_build_tapir_order_from_shopping_cart_serializer.return_value = {Mock: 2}
        mock_validate_and_fulfill_order.return_value = member

        BestellWizardConfirmOrderApiView.validate_everything_and_apply_all_changes(
            validated_serializer_data=validated_serializer_data,
            request=request,
            cache=cache,
        )

        mock_build_tapir_order_from_shopping_cart_serializer.assert_has_calls(
            [
                call(shopping_cart_order, cache=cache),
                call(shopping_cart_waiting_list, cache=cache),
            ]
        )
        mock_validate_and_fulfill_order.assert_called_once_with(
            request=request,
            validated_serializer_data=validated_serializer_data,
            cache=cache,
        )
        mock_validate_and_create_waiting_list_entry_potential_member.assert_not_called()
        mock_validate_and_create_waiting_list_entry_existing_member.assert_called_once_with(
            member=member,
            validated_serializer_data=validated_serializer_data,
            cache=cache,
        )
