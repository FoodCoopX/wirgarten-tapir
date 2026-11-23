import datetime
from decimal import Decimal

from tapir.bestell_wizard.serializers import BestellWizardGrowingPeriodChoiceSerializer
from tapir.bestell_wizard.services.growing_period_choice_builder import (
    GrowingPeriodChoice,
)
from tapir.pickup_locations.tests.factories import PickupLocationDeliveryChargeFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    PickupLocationFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestBestellWizardGrowingPeriodChoiceSerializer(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(self, now=datetime.datetime(year=2026, month=6, day=1))

    def test_productTypes_default_pricesAtContractStartDate(self):
        product = ProductPriceFactory.create(
            price=70, valid_from=datetime.date(year=2026, month=1, day=1)
        ).product
        ProductPriceFactory.create(
            product=product,
            price=80,
            valid_from=datetime.date(year=2027, month=1, day=1),
        )

        data = self._serialize(
            self._build_choice(product_types=[product.type], pickup_locations=[])
        )

        self.assertEqual(80, data["product_types"][0]["products"][0]["price"])

    def test_pickupLocations_default_deliveryChargeAtContractStartDate(self):
        pickup_location = PickupLocationFactory.create()
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=pickup_location,
            amount=Decimal("2.00"),
            valid_from=datetime.date(year=2026, month=1, day=1),
        )
        PickupLocationDeliveryChargeFactory.create(
            pickup_location=pickup_location,
            amount=Decimal("3.00"),
            valid_from=datetime.date(year=2027, month=1, day=1),
        )

        data = self._serialize(
            self._build_choice(product_types=[], pickup_locations=[pickup_location])
        )

        self.assertEqual("3.00", data["pickup_locations"][0]["current_delivery_charge"])

    @staticmethod
    def _build_choice(
        product_types: list, pickup_locations: list
    ) -> GrowingPeriodChoice:
        return GrowingPeriodChoice(
            growing_period=GrowingPeriodFactory.create(
                start_date=datetime.date(year=2027, month=1, day=1)
            ),
            contract_start_date=datetime.date(year=2027, month=1, day=1),
            product_types=product_types,
            product_type_ids_that_are_already_at_capacity=[],
            product_ids_that_are_already_at_capacity=[],
            pickup_locations=pickup_locations,
            solidarity_contribution_minimum=0.0,
        )

    @staticmethod
    def _serialize(growing_period_choice: GrowingPeriodChoice) -> dict:
        return BestellWizardGrowingPeriodChoiceSerializer(
            growing_period_choice, context={"cache": {}}
        ).data
