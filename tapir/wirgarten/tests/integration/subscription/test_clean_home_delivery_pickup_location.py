from django.core.exceptions import ValidationError

from tapir.wirgarten.forms.subscription import clean_home_delivery_pickup_location
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCleanHomeDeliveryPickupLocation(TapirIntegrationTest):
    def test_cleanHomeDeliveryPickupLocation_homeDeliveryWithoutAddress_raisesValidationError(
        self,
    ):
        member = MemberFactory.create(street="", postcode="", city="")

        with self.assertRaisesMessage(
            ValidationError,
            "Für die Hauslieferung wird eine vollständige Lieferadresse (Straße, PLZ und Ort) benötigt.",
        ):
            clean_home_delivery_pickup_location(
                pickup_location=PickupLocationFactory.create(is_home_delivery=True),
                member_id=member.id,
            )

    def test_cleanHomeDeliveryPickupLocation_homeDeliveryWithAddress_returnsLocation(
        self,
    ):
        member = MemberFactory.create(
            street="Rechnungsstraße 1", postcode="11111", city="Rechnungsstadt"
        )
        pickup_location = PickupLocationFactory.create(is_home_delivery=True)

        self.assertEqual(
            pickup_location,
            clean_home_delivery_pickup_location(
                pickup_location=pickup_location, member_id=member.id
            ),
        )
