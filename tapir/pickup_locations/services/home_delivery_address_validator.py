from django.core.exceptions import ValidationError

from tapir.pickup_locations.services.member_delivery_address_getter import (
    DeliveryAddress,
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

        cls.validate_address(
            delivery_address=MemberDeliveryAddressGetter.get_delivery_address(
                address_owner=address_owner
            ),
            pickup_location=pickup_location,
        )

    @classmethod
    def validate_address(
        cls, delivery_address: DeliveryAddress, pickup_location: PickupLocation
    ):
        if not pickup_location.is_home_delivery:
            return

        if not cls.is_complete(delivery_address=delivery_address):
            raise ValidationError(cls.MISSING_ADDRESS_MESSAGE)

    @staticmethod
    def is_complete(delivery_address: DeliveryAddress) -> bool:
        return bool(
            delivery_address.street
            and delivery_address.postcode
            and delivery_address.city
        )
