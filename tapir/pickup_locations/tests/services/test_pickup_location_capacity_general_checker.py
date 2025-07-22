import datetime
from unittest.mock import Mock, patch

from django.core.exceptions import ImproperlyConfigured

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.config import PICKING_MODE_SHARE, PICKING_MODE_BASKET
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PickupLocationFactory,
    MemberFactory,
    MemberPickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationCapacityGeneralChecker(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    @patch.object(
        PickupLocationCapacityModeBasketChecker, "check_for_picking_mode_basket"
    )
    @patch.object(
        PickupLocationCapacityModeShareChecker, "check_for_picking_mode_share"
    )
    def test_doesPickupLocationHaveEnoughCapacity_pickingModeIsShare_callsCheckerForModeShare(
        self,
        mock_check_for_picking_mode_share: Mock,
        mock_check_for_picking_mode_basket: Mock,
    ):
        pickup_location = PickupLocationFactory.create()
        ordered_products_to_quantity_map = Mock()
        subscription_start = datetime.date(year=2024, month=5, day=1)
        already_registered_member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=already_registered_member,
            pickup_location=pickup_location,
            valid_from=subscription_start - datetime.timedelta(days=1),
        )
        expected = Mock()
        mock_check_for_picking_mode_share.return_value = expected
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_SHARE
        )
        pickup_location_cache = {}
        cache = {pickup_location: pickup_location_cache}

        result = PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
            pickup_location=pickup_location,
            order=ordered_products_to_quantity_map,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
            cache=cache,
        )

        self.assertEqual(expected, result)
        mock_check_for_picking_mode_share.assert_called_once_with(
            pickup_location=pickup_location,
            order=ordered_products_to_quantity_map,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
            cache=cache,
        )
        mock_check_for_picking_mode_basket.assert_not_called()

    @patch.object(
        PickupLocationCapacityModeBasketChecker, "check_for_picking_mode_basket"
    )
    @patch.object(
        PickupLocationCapacityModeShareChecker, "check_for_picking_mode_share"
    )
    def test_doesPickupLocationHaveEnoughCapacity_pickingModeIsBasket_callsCheckerForModeBasket(
        self,
        mock_check_for_picking_mode_share: Mock,
        mock_check_for_picking_mode_basket: Mock,
    ):
        pickup_location = PickupLocationFactory.create()
        ordered_products_to_quantity_map = Mock()
        subscription_start = datetime.date(year=2024, month=5, day=1)
        already_registered_member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=already_registered_member,
            pickup_location=pickup_location,
            valid_from=subscription_start - datetime.timedelta(days=1),
        )
        expected = Mock()
        mock_check_for_picking_mode_basket.return_value = expected
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_BASKET
        )
        pickup_location_cache = {}
        cache = {pickup_location: pickup_location_cache}

        result = PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
            pickup_location=pickup_location,
            order=ordered_products_to_quantity_map,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
            cache=cache,
        )

        self.assertEqual(expected, result)
        mock_check_for_picking_mode_share.assert_not_called()
        mock_check_for_picking_mode_basket.assert_called_once_with(
            pickup_location=pickup_location,
            order=ordered_products_to_quantity_map,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
            cache=cache,
        )

    @patch.object(
        PickupLocationCapacityModeBasketChecker, "check_for_picking_mode_basket"
    )
    @patch.object(
        PickupLocationCapacityModeShareChecker, "check_for_picking_mode_share"
    )
    def test_doesPickupLocationHaveEnoughCapacity_memberIsNotRegisteredToGivenPickupLocation_callsCheckerWithoutMember(
        self,
        mock_check_for_picking_mode_share: Mock,
        mock_check_for_picking_mode_basket: Mock,
    ):
        pickup_location = PickupLocationFactory.create()
        ordered_products_to_quantity_map = Mock()
        subscription_start = datetime.date(year=2024, month=5, day=1)
        already_registered_member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=already_registered_member,
            pickup_location=PickupLocationFactory.create(),
            valid_from=subscription_start - datetime.timedelta(days=1),
        )
        expected = Mock()
        mock_check_for_picking_mode_basket.return_value = expected
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_BASKET
        )
        cache = {}

        result = PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
            pickup_location=pickup_location,
            order=ordered_products_to_quantity_map,
            already_registered_member=already_registered_member,
            subscription_start=subscription_start,
            cache=cache,
        )

        self.assertEqual(expected, result)
        mock_check_for_picking_mode_share.assert_not_called()
        mock_check_for_picking_mode_basket.assert_called_once_with(
            pickup_location=pickup_location,
            order=ordered_products_to_quantity_map,
            already_registered_member=None,
            subscription_start=subscription_start,
            cache=cache,
        )

    def test_doesPickupLocationHaveEnoughCapacity_invalidPickingMode_raisesException(
        self,
    ):
        pickup_location = PickupLocationFactory.create()
        ordered_products_to_quantity_map = Mock()
        subscription_start = datetime.date(year=2024, month=5, day=1)
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value="invalid"
        )
        cache = {}

        with self.assertRaises(ImproperlyConfigured):
            PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                pickup_location=pickup_location,
                order=ordered_products_to_quantity_map,
                already_registered_member=None,
                subscription_start=subscription_start,
                cache=cache,
            )
