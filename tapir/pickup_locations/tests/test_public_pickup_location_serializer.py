from django.test import override_settings

from tapir.pickup_locations.serializers import PublicPickupLocationSerializer
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPublicPickupLocationSerializer(TapirIntegrationTest):
    @override_settings(BAKERY_ENABLED=True)
    def test_getDeliveryDay_bakeryEnabled_returnsDeliveryDay(self):
        pickup_location = create_pickup_location_with_opening_times([4, 1])

        data = PublicPickupLocationSerializer(
            pickup_location, context={"cache": {}}
        ).data

        self.assertEqual(data["delivery_day"], 1)

    @override_settings(BAKERY_ENABLED=False)
    def test_getDeliveryDay_bakeryDisabled_returnsNone(self):
        pickup_location = create_pickup_location_with_opening_times([4, 1])

        data = PublicPickupLocationSerializer(
            pickup_location, context={"cache": {}}
        ).data

        self.assertIsNone(data["delivery_day"])
