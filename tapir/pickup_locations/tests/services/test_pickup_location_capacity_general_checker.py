import datetime
from unittest.mock import Mock, patch

from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
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
        ParameterDefinitions().import_definitions(bulk_create=True)

    @patch.object(
        PickupLocationCapacityModeShareChecker, "check_for_picking_mode_share"
    )
    def test_doesPickupLocationHaveEnoughCapacity_default_callsCheckerForModeShare(
        self,
        mock_check_for_picking_mode_share: Mock,
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

    @patch.object(
        PickupLocationCapacityModeShareChecker, "check_for_picking_mode_share"
    )
    def test_doesPickupLocationHaveEnoughCapacity_memberIsNotRegisteredToGivenPickupLocation_callsCheckerWithoutMember(
        self,
        mock_check_for_picking_mode_share: Mock,
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
        mock_check_for_picking_mode_share.return_value = expected
        cache = {}

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
            already_registered_member=None,
            subscription_start=subscription_start,
            cache=cache,
        )
