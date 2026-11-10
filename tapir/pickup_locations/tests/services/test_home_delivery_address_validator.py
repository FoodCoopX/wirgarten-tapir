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


@patch.object(MemberDeliveryAddressGetter, "get_delivery_address", autospec=True)
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

    def test_validate_normalLocation_doesNotResolveAddress(
        self, mock_get_delivery_address: MagicMock
    ):
        HomeDeliveryAddressValidator.validate(
            address_owner=MemberFactory.build(),
            pickup_location=PickupLocationFactory.build(is_home_delivery=False),
        )

        mock_get_delivery_address.assert_not_called()

    def test_validate_homeDeliveryAndCompleteAddress_doesNotRaise(
        self, mock_get_delivery_address: MagicMock
    ):
        member = MemberFactory.build()
        mock_get_delivery_address.return_value = self._build_address()

        HomeDeliveryAddressValidator.validate(
            address_owner=member,
            pickup_location=PickupLocationFactory.build(is_home_delivery=True),
        )

        mock_get_delivery_address.assert_called_once_with(address_owner=member)

    def test_validate_homeDeliveryAndStreetMissing_raisesValidationError(
        self, mock_get_delivery_address: MagicMock
    ):
        mock_get_delivery_address.return_value = self._build_address(street="")

        with self.assertRaisesMessage(ValidationError, MISSING_ADDRESS_MESSAGE):
            HomeDeliveryAddressValidator.validate(
                address_owner=MemberFactory.build(),
                pickup_location=PickupLocationFactory.build(is_home_delivery=True),
            )

    def test_validate_homeDeliveryAndPostcodeMissing_raisesValidationError(
        self, mock_get_delivery_address: MagicMock
    ):
        mock_get_delivery_address.return_value = self._build_address(postcode="")

        with self.assertRaisesMessage(ValidationError, MISSING_ADDRESS_MESSAGE):
            HomeDeliveryAddressValidator.validate(
                address_owner=MemberFactory.build(),
                pickup_location=PickupLocationFactory.build(is_home_delivery=True),
            )

    def test_validate_homeDeliveryAndCityMissing_raisesValidationError(
        self, mock_get_delivery_address: MagicMock
    ):
        mock_get_delivery_address.return_value = self._build_address(city="")

        with self.assertRaisesMessage(ValidationError, MISSING_ADDRESS_MESSAGE):
            HomeDeliveryAddressValidator.validate(
                address_owner=MemberFactory.build(),
                pickup_location=PickupLocationFactory.build(is_home_delivery=True),
            )
