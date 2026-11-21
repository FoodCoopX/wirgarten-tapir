from unittest.mock import MagicMock, patch

from tapir.pickup_locations.services.pickup_location_mail_token_service import (
    PickupLocationMailTokenService,
)
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestPickupLocationMailTokenServicePickupLocationNameOrEmpty(TapirUnitTest):
    @patch.object(
        PickupLocationMailTokenService,
        "get_pickup_location_if_available",
        autospec=True,
    )
    def test_pickupLocationNameOrEmpty_hasPickupLocation_returnsName(
        self, mock_get_pickup_location_if_available: MagicMock
    ):
        mock_get_pickup_location_if_available.return_value = (
            PickupLocationFactory.build(name="Station A")
        )
        member = MemberFactory.build()
        cache = {}

        result = PickupLocationMailTokenService.pickup_location_name_or_empty(
            recipient=member, cache=cache
        )

        self.assertEqual("Station A", result)
        mock_get_pickup_location_if_available.assert_called_once_with(member, cache)

    @patch.object(
        PickupLocationMailTokenService,
        "get_pickup_location_if_available",
        autospec=True,
    )
    def test_pickupLocationNameOrEmpty_noPickupLocation_returnsEmptyString(
        self, mock_get_pickup_location_if_available: MagicMock
    ):
        mock_get_pickup_location_if_available.return_value = None

        result = PickupLocationMailTokenService.pickup_location_name_or_empty(
            recipient=MemberFactory.build(), cache={}
        )

        self.assertEqual("", result)
