from unittest.mock import MagicMock, patch

from django.core.exceptions import ValidationError

from tapir.pickup_locations.services.home_delivery_address_validator import (
    HomeDeliveryAddressValidator,
)
from tapir.pickup_locations.services.member_delivery_address_getter import (
    DeliveryAddress,
    MemberDeliveryAddressGetter,
)
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest

MISSING_ADDRESS_MESSAGE = "Für die Hauslieferung wird eine vollständige Lieferadresse (Straße, PLZ und Ort) benötigt."


class TestHomeDeliveryAddressValidator(TapirUnitTest):
    @staticmethod
    def _build_address(**overrides: str) -> DeliveryAddress:
        fields = {
            "street": "Lieferweg 2",
            "street_2": "",
            "postcode": "22222",
            "city": "Lieferdorf",
            "country": "DE",
        }
        fields.update(overrides)
        return DeliveryAddress(**fields)

    @patch.object(HomeDeliveryAddressValidator, "validate_address", autospec=True)
    @patch.object(MemberDeliveryAddressGetter, "get_delivery_address", autospec=True)
    def test_validate_normalLocation_doesNotResolveAddress(
        self, mock_get_delivery_address: MagicMock, mock_validate_address: MagicMock
    ):
        HomeDeliveryAddressValidator.validate(
            address_owner=MemberFactory.build(),
            pickup_location=PickupLocationFactory.build(is_home_delivery=False),
        )

        mock_get_delivery_address.assert_not_called()
        mock_validate_address.assert_not_called()

    @patch.object(HomeDeliveryAddressValidator, "validate_address", autospec=True)
    @patch.object(MemberDeliveryAddressGetter, "get_delivery_address", autospec=True)
    def test_validate_homeDelivery_validatesResolvedAddress(
        self, mock_get_delivery_address: MagicMock, mock_validate_address: MagicMock
    ):
        member = MemberFactory.build()
        pickup_location = PickupLocationFactory.build(is_home_delivery=True)
        address = self._build_address()
        mock_get_delivery_address.return_value = address

        HomeDeliveryAddressValidator.validate(
            address_owner=member, pickup_location=pickup_location
        )

        mock_get_delivery_address.assert_called_once_with(address_owner=member)
        mock_validate_address.assert_called_once_with(
            delivery_address=address, pickup_location=pickup_location
        )

    def test_validateAddress_normalLocationAndIncompleteAddress_doesNotRaise(self):
        HomeDeliveryAddressValidator.validate_address(
            delivery_address=self._build_address(street=""),
            pickup_location=PickupLocationFactory.build(is_home_delivery=False),
        )

    def test_validateAddress_homeDeliveryAndCompleteAddress_doesNotRaise(self):
        HomeDeliveryAddressValidator.validate_address(
            delivery_address=self._build_address(),
            pickup_location=PickupLocationFactory.build(is_home_delivery=True),
        )

    def test_validateAddress_homeDeliveryAndStreetMissing_raisesValidationError(
        self,
    ):
        with self.assertRaisesMessage(ValidationError, MISSING_ADDRESS_MESSAGE):
            HomeDeliveryAddressValidator.validate_address(
                delivery_address=self._build_address(street=""),
                pickup_location=PickupLocationFactory.build(is_home_delivery=True),
            )

    def test_validateAddress_homeDeliveryAndPostcodeMissing_raisesValidationError(
        self,
    ):
        with self.assertRaisesMessage(ValidationError, MISSING_ADDRESS_MESSAGE):
            HomeDeliveryAddressValidator.validate_address(
                delivery_address=self._build_address(postcode=""),
                pickup_location=PickupLocationFactory.build(is_home_delivery=True),
            )

    def test_validateAddress_homeDeliveryAndCityMissing_raisesValidationError(
        self,
    ):
        with self.assertRaisesMessage(ValidationError, MISSING_ADDRESS_MESSAGE):
            HomeDeliveryAddressValidator.validate_address(
                delivery_address=self._build_address(city=""),
                pickup_location=PickupLocationFactory.build(is_home_delivery=True),
            )
