import datetime
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.single_subscription_validator import (
    SingleSubscriptionValidator,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    SingleSubscriptionValidator,
    "are_single_subscription_products_are_ordered_at_most_once",
    autospec=True,
    return_value=True,
)
@patch.object(OrderValidator, "validate_capacities", autospec=True)
class TestOrderValidatorValidateOrderGeneral(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.member = MemberFactory.build()
        self.product = ProductFactory.build()
        self.order = {self.product: 1}
        self.pickup_location = PickupLocationFactory.build()
        self.contract_start_date = datetime.date(year=2027, month=6, day=7)
        self.cache = {}
        mock_parameter_value(
            cache=self.cache,
            key=ParameterKeys.DELIVERY_DONATION_FORWARD_TO_PICKUP_LOCATION,
            value="donation_id",
        )

    def _validate(self):
        OrderValidator.validate_order_general(
            order=self.order,
            contract_start_date=self.contract_start_date,
            cache=self.cache,
            member=self.member,
            pickup_location=self.pickup_location,
        )

    def test_validateOrderGeneral_validOrder_validatesCapacities(
        self, mock_validate_capacities: MagicMock, _: MagicMock
    ):
        self._validate()

        mock_validate_capacities.assert_called_once_with(
            order=self.order,
            contract_start_date=self.contract_start_date,
            member=self.member,
            pickup_location=self.pickup_location,
            cache=self.cache,
        )

    def test_validateOrderGeneral_productTypeOnlyForWaitingList_raisesBeforeCapacityChecks(
        self, mock_validate_capacities: MagicMock, _: MagicMock
    ):
        self.product.type.force_waiting_list = True

        with self.assertRaisesMessage(ValidationError, "nur Wartelisteneinträge"):
            self._validate()

        mock_validate_capacities.assert_not_called()

    def test_validateOrderGeneral_donationPickupLocation_raisesValidationError(
        self, _: MagicMock, __: MagicMock
    ):
        self.pickup_location.id = "donation_id"

        with self.assertRaisesMessage(ValidationError, "Sonder-Abholort für Spenden"):
            self._validate()

    def test_validateOrderGeneral_singleSubscriptionProductOrderedTwice_raisesValidationError(
        self,
        _: MagicMock,
        mock_are_single_subscription_products_ordered_at_most_once: MagicMock,
    ):
        mock_are_single_subscription_products_ordered_at_most_once.return_value = False

        with self.assertRaisesMessage(ValidationError, "nur einmal bestellt"):
            self._validate()
