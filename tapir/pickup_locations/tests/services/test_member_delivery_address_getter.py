from tapir.pickup_locations.services.member_delivery_address_getter import (
    DeliveryAddress,
    MemberDeliveryAddressGetter,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestMemberDeliveryAddressGetter(TapirUnitTest):
    @staticmethod
    def _build_member(**overrides):
        fields = {
            "street": "Rechnungsstraße 1",
            "street_2": "Hinterhaus",
            "postcode": "11111",
            "city": "Rechnungsstadt",
            "country": "DE",
            "delivery_street": "Lieferweg 2",
            "delivery_street_2": "",
            "delivery_postcode": "22222",
            "delivery_city": "Lieferdorf",
            "delivery_country": "AT",
        }
        fields.update(overrides)
        return MemberFactory.build(**fields)

    def test_getDeliveryAddress_sameAsBillingAddress_returnsBillingAddress(self):
        member = self._build_member(delivery_same_as_billing_address=True)

        self.assertEqual(
            DeliveryAddress(
                street="Rechnungsstraße 1",
                street_2="Hinterhaus",
                postcode="11111",
                city="Rechnungsstadt",
                country="DE",
            ),
            MemberDeliveryAddressGetter.get_delivery_address(member=member),
        )

    def test_getDeliveryAddress_separateAddress_returnsDeliveryAddress(self):
        member = self._build_member(delivery_same_as_billing_address=False)

        self.assertEqual(
            DeliveryAddress(
                street="Lieferweg 2",
                street_2="",
                postcode="22222",
                city="Lieferdorf",
                country="AT",
            ),
            MemberDeliveryAddressGetter.get_delivery_address(member=member),
        )
