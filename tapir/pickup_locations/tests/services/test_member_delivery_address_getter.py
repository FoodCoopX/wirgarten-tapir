from tapir.pickup_locations.services.member_delivery_address_getter import (
    DeliveryAddress,
    DeliveryAddressInput,
    MemberDeliveryAddressGetter,
)
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestMemberDeliveryAddressGetter(TapirUnitTest):
    @staticmethod
    def _build_member(**overrides: str | bool):
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
            MemberDeliveryAddressGetter.get_delivery_address(address_owner=member),
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
            MemberDeliveryAddressGetter.get_delivery_address(address_owner=member),
        )

    def test_getDeliveryAddress_entryWithoutMemberSameAsBilling_returnsEntryBillingAddress(
        self,
    ):
        waiting_list_entry = WaitingListEntryFactory.build(
            member=None,
            delivery_same_as_billing_address=True,
            street="Eintragsstraße 3",
            street_2="",
            postcode="33333",
            city="Eintragsstadt",
            country="DE",
        )

        self.assertEqual(
            DeliveryAddress(
                street="Eintragsstraße 3",
                street_2="",
                postcode="33333",
                city="Eintragsstadt",
                country="DE",
            ),
            MemberDeliveryAddressGetter.get_delivery_address(
                address_owner=waiting_list_entry
            ),
        )

    def test_getDeliveryAddress_entryOfExistingMemberSameAsBilling_returnsMemberBillingAddress(
        self,
    ):
        waiting_list_entry = WaitingListEntryFactory.build(
            member=self._build_member(),
            delivery_same_as_billing_address=True,
            street="",
            street_2="",
            postcode="",
            city="",
        )

        self.assertEqual(
            DeliveryAddress(
                street="Rechnungsstraße 1",
                street_2="Hinterhaus",
                postcode="11111",
                city="Rechnungsstadt",
                country="DE",
            ),
            MemberDeliveryAddressGetter.get_delivery_address(
                address_owner=waiting_list_entry
            ),
        )

    def test_getDeliveryAddress_entryOfExistingMemberSeparateAddress_returnsEntryDeliveryAddress(
        self,
    ):
        waiting_list_entry = WaitingListEntryFactory.build(
            member=self._build_member(),
            delivery_same_as_billing_address=False,
            delivery_street="Wunschweg 4",
            delivery_street_2="",
            delivery_postcode="44444",
            delivery_city="Wunschdorf",
            delivery_country="DE",
        )

        self.assertEqual(
            DeliveryAddress(
                street="Wunschweg 4",
                street_2="",
                postcode="44444",
                city="Wunschdorf",
                country="DE",
            ),
            MemberDeliveryAddressGetter.get_delivery_address(
                address_owner=waiting_list_entry
            ),
        )

    def test_getDeliveryAddressFromInput_sameAsBillingAddress_returnsPersonalDataAddress(
        self,
    ):
        self.assertEqual(
            DeliveryAddress(
                street="Rechnungsstraße 1",
                street_2="Hinterhaus",
                postcode="11111",
                city="Rechnungsstadt",
                country="DE",
            ),
            MemberDeliveryAddressGetter.get_delivery_address_from_input(
                delivery_address_input=DeliveryAddressInput(
                    same_as_billing_address=True,
                    street="",
                    street_2="",
                    postcode="",
                    city="",
                    country="",
                ),
                personal_data={
                    "street": "Rechnungsstraße 1",
                    "street_2": "Hinterhaus",
                    "postcode": "11111",
                    "city": "Rechnungsstadt",
                    "country": "DE",
                },
            ),
        )

    def test_getDeliveryAddressFromInput_separateAddress_returnsInputAddress(self):
        self.assertEqual(
            DeliveryAddress(
                street="Lieferweg 2",
                street_2="",
                postcode="22222",
                city="Lieferdorf",
                country="AT",
            ),
            MemberDeliveryAddressGetter.get_delivery_address_from_input(
                delivery_address_input=DeliveryAddressInput(
                    same_as_billing_address=False,
                    street="Lieferweg 2",
                    street_2="",
                    postcode="22222",
                    city="Lieferdorf",
                    country="AT",
                ),
                personal_data={
                    "street": "Rechnungsstraße 1",
                    "street_2": "Hinterhaus",
                    "postcode": "11111",
                    "city": "Rechnungsstadt",
                    "country": "DE",
                },
            ),
        )
