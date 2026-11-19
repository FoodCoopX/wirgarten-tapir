import datetime
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    ProductCapacityChecker,
    "does_product_have_enough_free_capacity_to_add_order",
    autospec=True,
    return_value=True,
)
@patch.object(
    GlobalCapacityChecker,
    "get_product_type_ids_without_enough_capacity_for_order",
    autospec=True,
    return_value=[],
)
@patch.object(
    PickupLocationCapacityGeneralChecker,
    "does_pickup_location_have_enough_capacity_to_add_subscriptions",
    autospec=True,
    return_value=True,
)
@patch.object(
    OrderValidator,
    "does_order_need_a_pickup_location",
    autospec=True,
    return_value=True,
)
class TestOrderValidatorValidateCapacities(TapirUnitTest):
    def setUp(self):
        super().setUp()
        self.member = MemberFactory.build()
        self.product = ProductFactory.build()
        self.order = {self.product: 2}
        self.pickup_location = PickupLocationFactory.build()
        self.contract_start_date = datetime.date(year=2027, month=6, day=7)
        self.cache = {}

    def _validate(self):
        OrderValidator.validate_capacities(
            order=self.order,
            contract_start_date=self.contract_start_date,
            member=self.member,
            pickup_location=self.pickup_location,
            cache=self.cache,
        )

    def test_validateCapacities_enoughCapacity_callsAllCheckersWithCorrectParameters(
        self,
        mock_does_order_need_a_pickup_location: MagicMock,
        mock_does_pickup_location_have_enough_capacity: MagicMock,
        mock_get_product_type_ids_without_enough_capacity: MagicMock,
        mock_does_product_have_enough_free_capacity: MagicMock,
    ):
        self._validate()

        mock_does_order_need_a_pickup_location.assert_called_once_with(
            order=self.order, cache=self.cache
        )
        mock_does_pickup_location_have_enough_capacity.assert_called_once_with(
            pickup_location=self.pickup_location,
            order=self.order,
            already_registered_member=self.member,
            subscription_start=self.contract_start_date,
            cache=self.cache,
        )
        mock_get_product_type_ids_without_enough_capacity.assert_called_once_with(
            order_with_all_product_types=self.order,
            member_id=self.member.id,
            subscription_start_date=self.contract_start_date,
            cache=self.cache,
        )
        mock_does_product_have_enough_free_capacity.assert_called_once_with(
            product=self.product,
            member_id=self.member.id,
            subscription_start_date=self.contract_start_date,
            ordered_quantity=2,
            cache=self.cache,
        )

    def test_validateCapacities_orderDoesNotNeedPickupLocation_doesNotCheckPickupLocation(
        self,
        mock_does_order_need_a_pickup_location: MagicMock,
        mock_does_pickup_location_have_enough_capacity: MagicMock,
        *_: MagicMock,
    ):
        mock_does_order_need_a_pickup_location.return_value = False

        self._validate()

        mock_does_pickup_location_have_enough_capacity.assert_not_called()

    def test_validateCapacities_pickupLocationFull_raisesValidationError(
        self,
        _: MagicMock,
        mock_does_pickup_location_have_enough_capacity: MagicMock,
        *__: MagicMock,
    ):
        mock_does_pickup_location_have_enough_capacity.return_value = False

        with self.assertRaisesMessage(ValidationError, "Abholort ist leider voll"):
            self._validate()

    def test_validateCapacities_productTypeFull_raisesValidationError(
        self,
        _: MagicMock,
        __: MagicMock,
        mock_get_product_type_ids_without_enough_capacity: MagicMock,
        *___: MagicMock,
    ):
        mock_get_product_type_ids_without_enough_capacity.return_value = ["type_id"]

        with self.assertRaisesMessage(
            ValidationError, "Produkt-Typen haben nicht genug Kapazität"
        ):
            self._validate()

    def test_validateCapacities_productFull_raisesValidationError(
        self,
        _: MagicMock,
        __: MagicMock,
        ___: MagicMock,
        mock_does_product_have_enough_free_capacity: MagicMock,
    ):
        mock_does_product_have_enough_free_capacity.return_value = False

        with self.assertRaisesMessage(
            ValidationError,
            f"nicht genug Kapazität für diese Bestellung: {self.product.name}",
        ):
            self._validate()

    def test_validateCapacities_noMember_passesNoMemberId(
        self,
        _: MagicMock,
        __: MagicMock,
        mock_get_product_type_ids_without_enough_capacity: MagicMock,
        mock_does_product_have_enough_free_capacity: MagicMock,
    ):
        self.member = None

        self._validate()

        self.assertIsNone(
            mock_get_product_type_ids_without_enough_capacity.call_args.kwargs[
                "member_id"
            ]
        )
        self.assertIsNone(
            mock_does_product_have_enough_free_capacity.call_args.kwargs["member_id"]
        )
