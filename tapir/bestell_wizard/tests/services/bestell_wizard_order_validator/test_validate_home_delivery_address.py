from unittest.mock import MagicMock, call, patch

from django.core.exceptions import ValidationError

from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.pickup_locations.services.home_delivery_address_validator import (
    HomeDeliveryAddressValidator,
)
from tapir.pickup_locations.services.member_delivery_address_getter import (
    DeliveryAddress,
    DeliveryAddressInput,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.factories import PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateHomeDeliveryAddress(TapirUnitTest):
    @staticmethod
    def _build_delivery_address_input() -> DeliveryAddressInput:
        return DeliveryAddressInput(
            same_as_billing_address=False,
            street="Lieferweg 2",
            street_2="",
            postcode="22222",
            city="Lieferdorf",
            country="DE",
        )

    @patch.object(HomeDeliveryAddressValidator, "validate_address", autospec=True)
    @patch.object(TapirCache, "get_pickup_location_by_id", autospec=True)
    def test_validateHomeDeliveryAddress_default_validatesEveryChosenLocation(
        self,
        mock_get_pickup_location_by_id: MagicMock,
        mock_validate_address: MagicMock,
    ):
        pickup_location_1 = PickupLocationFactory.build(id="location_1")
        pickup_location_2 = PickupLocationFactory.build(id="location_2")
        mock_get_pickup_location_by_id.side_effect = lambda cache, pickup_location_id: {
            "location_1": pickup_location_1,
            "location_2": pickup_location_2,
        }[pickup_location_id]

        BestellWizardOrderValidator.validate_home_delivery_address(
            pickup_location_ids=["location_1", "location_2"],
            delivery_address_input=self._build_delivery_address_input(),
            personal_data={},
            cache={},
        )

        delivery_address = DeliveryAddress(
            street="Lieferweg 2",
            street_2="",
            postcode="22222",
            city="Lieferdorf",
            country="DE",
        )
        self.assertEqual(
            [
                call(
                    delivery_address=delivery_address,
                    pickup_location=pickup_location_1,
                ),
                call(
                    delivery_address=delivery_address,
                    pickup_location=pickup_location_2,
                ),
            ],
            mock_validate_address.call_args_list,
        )

    @patch.object(
        HomeDeliveryAddressValidator,
        "validate_address",
        autospec=True,
        side_effect=ValidationError("Adresse fehlt"),
    )
    @patch.object(TapirCache, "get_pickup_location_by_id", autospec=True)
    def test_validateHomeDeliveryAddress_validatorRaises_raisesValidationError(
        self, *_
    ):
        with self.assertRaisesMessage(ValidationError, "Adresse fehlt"):
            BestellWizardOrderValidator.validate_home_delivery_address(
                pickup_location_ids=["location_1"],
                delivery_address_input=self._build_delivery_address_input(),
                personal_data={},
                cache={},
            )
