from tapir.pickup_locations.services.pickup_location_mail_token_service import (
    PickupLocationMailTokenService,
)
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestPickupLocationMailTokenServiceBuildAddress(TapirUnitTest):
    @staticmethod
    def _build_member():
        return MemberFactory.build(
            delivery_same_as_billing_address=False,
            delivery_street="Lieferweg 2",
            delivery_street_2="Hinterhaus",
            delivery_postcode="22222",
            delivery_city="Lieferdorf",
        )

    def test_buildAddress_normalLocation_returnsLocationAddress(self):
        pickup_location = PickupLocationFactory.build(
            is_home_delivery=False,
            street="Stationsstraße 1",
            street_2="",
            postcode="11111",
            city="Stationsstadt",
        )

        self.assertEqual(
            "Stationsstraße 1, 11111 Stationsstadt",
            PickupLocationMailTokenService.build_address(
                member=self._build_member(), pickup_location=pickup_location
            ),
        )

    def test_buildAddress_homeDelivery_returnsMemberDeliveryAddress(self):
        pickup_location = PickupLocationFactory.build(
            is_home_delivery=True,
            street="Stationsstraße 1",
            street_2="",
            postcode="11111",
            city="Stationsstadt",
        )

        self.assertEqual(
            "Lieferweg 2, Hinterhaus, 22222 Lieferdorf",
            PickupLocationMailTokenService.build_address(
                member=self._build_member(), pickup_location=pickup_location
            ),
        )
