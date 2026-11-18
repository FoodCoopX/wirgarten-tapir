import datetime
from unittest.mock import patch, MagicMock

from tapir.deliveries.services.member_specific_delivery_day_calculator import (
    MemberSpecificDeliveryDayCalculator,
)
from tapir.deliveries.services.pickup_location_delivery_date_calculator import (
    PickupLocationDeliveryDateCalculator,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestMemberSpecificDeliveryDayCalculator(TapirUnitTest):
    @patch.object(
        PickupLocationDeliveryDateCalculator,
        "get_delivery_date_at_pickup_location",
        autospec=True,
    )
    @patch.object(
        MemberPickupLocationGetter,
        "get_member_pickup_location_id_from_cache",
        autospec=True,
    )
    def test_getSpecificDeliveryDate_default_returnsDateAtMemberPickupLocation(
        self,
        mock_get_member_pickup_location_id_from_cache: MagicMock,
        mock_get_delivery_date_at_pickup_location: MagicMock,
    ):
        mock_get_member_pickup_location_id_from_cache.return_value = "test_location"
        expected_result = datetime.date(year=2020, month=11, day=20)
        mock_get_delivery_date_at_pickup_location.return_value = expected_result
        cache = {}

        result = MemberSpecificDeliveryDayCalculator.get_specific_delivery_date(
            member_id="test_member",
            delivery_date=datetime.date(year=2020, month=11, day=18),  # Wednesday
            cache=cache,
        )

        self.assertEqual(expected_result, result)
        mock_get_member_pickup_location_id_from_cache.assert_called_once_with(
            member_id="test_member",
            reference_date=datetime.date(year=2020, month=11, day=16),  # Monday
            cache=cache,
        )
        mock_get_delivery_date_at_pickup_location.assert_called_once_with(
            pickup_location_id="test_location",
            delivery_date=datetime.date(year=2020, month=11, day=18),
            cache=cache,
        )
