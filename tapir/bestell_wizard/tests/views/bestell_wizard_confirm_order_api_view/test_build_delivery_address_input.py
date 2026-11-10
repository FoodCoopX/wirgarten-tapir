from tapir.bestell_wizard.views import BestellWizardConfirmOrderApiView
from tapir.pickup_locations.services.member_delivery_address_getter import (
    DeliveryAddressInput,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest

SAME_AS_BILLING_INPUT = DeliveryAddressInput(
    same_as_billing_address=True,
    street="",
    street_2="",
    postcode="",
    city="",
    country="",
)


class TestBuildDeliveryAddressInput(TapirUnitTest):
    def test_buildDeliveryAddressInput_noDeliveryAddress_returnsSameAsBilling(self):
        self.assertEqual(
            SAME_AS_BILLING_INPUT,
            BestellWizardConfirmOrderApiView.build_delivery_address_input(
                validated_serializer_data={}
            ),
        )

    def test_buildDeliveryAddressInput_sameAsBillingAddress_ignoresAddressFields(
        self,
    ):
        self.assertEqual(
            SAME_AS_BILLING_INPUT,
            BestellWizardConfirmOrderApiView.build_delivery_address_input(
                validated_serializer_data={
                    "delivery_address": {
                        "same_as_billing_address": True,
                        "street": "Lieferweg 2",
                        "street_2": "",
                        "postcode": "22222",
                        "city": "Lieferdorf",
                        "country": "DE",
                    }
                }
            ),
        )

    def test_buildDeliveryAddressInput_separateAddress_returnsAddressFields(self):
        self.assertEqual(
            DeliveryAddressInput(
                same_as_billing_address=False,
                street="Lieferweg 2",
                street_2="Hof",
                postcode="22222",
                city="Lieferdorf",
                country="AT",
            ),
            BestellWizardConfirmOrderApiView.build_delivery_address_input(
                validated_serializer_data={
                    "delivery_address": {
                        "same_as_billing_address": False,
                        "street": "Lieferweg 2",
                        "street_2": "Hof",
                        "postcode": "22222",
                        "city": "Lieferdorf",
                        "country": "AT",
                    }
                }
            ),
        )
