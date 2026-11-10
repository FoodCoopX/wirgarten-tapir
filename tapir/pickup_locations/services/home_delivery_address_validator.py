from django.core.exceptions import ValidationError

from tapir.pickup_locations.services.member_delivery_address_getter import (
    MemberDeliveryAddressGetter,
)
from tapir.wirgarten.models import Member, PickupLocation, WaitingListEntry


class HomeDeliveryAddressValidator:
    MISSING_ADDRESS_MESSAGE = "Für die Hauslieferung wird eine vollständige Lieferadresse (Straße, PLZ und Ort) benötigt."

    @classmethod
    def validate(
        cls,
        address_owner: Member | WaitingListEntry,
        pickup_location: PickupLocation,
    ):
        if not pickup_location.is_home_delivery:
            return

        address = MemberDeliveryAddressGetter.get_delivery_address(
            address_owner=address_owner
        )
        if not (address.street and address.postcode and address.city):
            raise ValidationError(cls.MISSING_ADDRESS_MESSAGE)
