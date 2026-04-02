from unittest.mock import patch, Mock

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.wirgarten.models import PickupLocation


@patch.object(PickupLocation, "objects", autospec=True)
@patch.object(
    MemberPickupLocationGetter, "get_member_pickup_location_id", autospec=True
)
@patch.object(OrderValidator, "does_order_need_a_pickup_location", autospec=True)
class TestSubscriptionUpdateViewValidatorValidatePickupLocation(SimpleTestCase):
    def build_default_params(self):
        self.order = Mock()
        self.member = Mock()
        self.contract_start_date = Mock()
        self.cache = Mock()
        return {
            "order": self.order,
            "member": self.member,
            "contract_start_date": self.contract_start_date,
            "desired_pickup_location_id": "desired_id",
            "cache": self.cache,
        }

    def assert_raises_validation_error(self, error_message: str, **params):
        with self.assertRaises(ValidationError) as error:
            SubscriptionUpdateViewValidator.validate_pickup_location(**params)

        self.assertEqual(error_message, error.exception.message)

    def test_validatePickupLocation_orderDoesNotNeedPickupLocation_returnsNone(
        self,
        mock_does_order_need_a_pickup_location: Mock,
        mock_get_member_pickup_location_id: Mock,
        mock_pickup_location_objects: Mock,
    ):
        mock_does_order_need_a_pickup_location.return_value = False
        params = self.build_default_params()

        result = SubscriptionUpdateViewValidator.validate_pickup_location(**params)

        self.assertIsNone(result)
        mock_does_order_need_a_pickup_location.assert_called_once_with(
            order=self.order, cache=self.cache
        )
        mock_get_member_pickup_location_id.assert_not_called()
        mock_pickup_location_objects.get.assert_not_called()

    def test_validatePickupLocation_memberAlreadyHasALocationAndANewOneIsSent_raisesValidationError(
        self,
        mock_does_order_need_a_pickup_location: Mock,
        mock_get_member_pickup_location_id: Mock,
        mock_pickup_location_objects: Mock,
    ):
        mock_does_order_need_a_pickup_location.return_value = True
        mock_get_member_pickup_location_id.return_value = "current_id"
        params = self.build_default_params()
        params["desired_pickup_location_id"] = "different_desired_id"

        self.assert_raises_validation_error(
            "Du hast schon eine Verteilstation", **params
        )

        mock_does_order_need_a_pickup_location.assert_called_once_with(
            order=self.order, cache=self.cache
        )
        mock_get_member_pickup_location_id.assert_called_once_with(
            member=self.member, reference_date=self.contract_start_date
        )
        mock_pickup_location_objects.get.assert_not_called()

    def test_validatePickupLocation_memberAlreadyHasALocationAndASameOneIsSent_returnsPickupLocation(
        self,
        mock_does_order_need_a_pickup_location: Mock,
        mock_get_member_pickup_location_id: Mock,
        mock_pickup_location_objects: Mock,
    ):
        mock_does_order_need_a_pickup_location.return_value = True
        mock_get_member_pickup_location_id.return_value = "same_id"
        mock_pickup_location = Mock()
        mock_pickup_location_objects.get.return_value = mock_pickup_location
        params = self.build_default_params()
        params["desired_pickup_location_id"] = "same_id"

        result = SubscriptionUpdateViewValidator.validate_pickup_location(**params)

        self.assertEqual(mock_pickup_location, result)

        mock_does_order_need_a_pickup_location.assert_called_once_with(
            order=self.order, cache=self.cache
        )
        mock_get_member_pickup_location_id.assert_called_once_with(
            member=self.member, reference_date=self.contract_start_date
        )
        mock_pickup_location_objects.get.assert_called_once_with(id="same_id")

    def test_validatePickupLocation_aCurrentLocationExistsAndNoNewOneIsSent_returnsPickupLocationWithCurrentId(
        self,
        mock_does_order_need_a_pickup_location: Mock,
        mock_get_member_pickup_location_id: Mock,
        mock_pickup_location_objects: Mock,
    ):
        mock_does_order_need_a_pickup_location.return_value = True
        mock_get_member_pickup_location_id.return_value = "current_id"
        mock_pickup_location = Mock()
        mock_pickup_location_objects.get.return_value = mock_pickup_location
        params = self.build_default_params()
        params["desired_pickup_location_id"] = None

        result = SubscriptionUpdateViewValidator.validate_pickup_location(**params)

        self.assertEqual(mock_pickup_location, result)

        mock_does_order_need_a_pickup_location.assert_called_once_with(
            order=self.order, cache=self.cache
        )
        mock_get_member_pickup_location_id.assert_called_once_with(
            member=self.member, reference_date=self.contract_start_date
        )
        mock_pickup_location_objects.get.assert_called_once_with(id="current_id")

    def test_validatePickupLocation_noCurrentLocationExistsAndNoNewOneIsSent_returnsPickupLocationWithDesiredId(
        self,
        mock_does_order_need_a_pickup_location: Mock,
        mock_get_member_pickup_location_id: Mock,
        mock_pickup_location_objects: Mock,
    ):
        mock_does_order_need_a_pickup_location.return_value = True
        mock_get_member_pickup_location_id.return_value = None
        mock_pickup_location = Mock()
        mock_pickup_location_objects.get.return_value = mock_pickup_location
        params = self.build_default_params()

        result = SubscriptionUpdateViewValidator.validate_pickup_location(**params)

        self.assertEqual(mock_pickup_location, result)

        mock_does_order_need_a_pickup_location.assert_called_once_with(
            order=self.order, cache=self.cache
        )
        mock_get_member_pickup_location_id.assert_called_once_with(
            member=self.member, reference_date=self.contract_start_date
        )
        mock_pickup_location_objects.get.assert_called_once_with(id="desired_id")

    def test_validatePickupLocation_neitherCurrentNorNewLocationSet_raisesValidationError(
        self,
        mock_does_order_need_a_pickup_location: Mock,
        mock_get_member_pickup_location_id: Mock,
        mock_pickup_location_objects: Mock,
    ):
        mock_does_order_need_a_pickup_location.return_value = True
        mock_get_member_pickup_location_id.return_value = None
        params = self.build_default_params()
        params["desired_pickup_location_id"] = None

        self.assert_raises_validation_error("Bitte wähle einen Abholort aus!", **params)

        mock_does_order_need_a_pickup_location.assert_called_once_with(
            order=self.order, cache=self.cache
        )
        mock_get_member_pickup_location_id.assert_called_once_with(
            member=self.member, reference_date=self.contract_start_date
        )
        mock_pickup_location_objects.get.assert_not_called()
