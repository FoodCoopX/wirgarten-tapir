from dataclasses import dataclass

from tapir.wirgarten.models import Member, WaitingListEntry


@dataclass(frozen=True)
class DeliveryAddress:
    street: str
    street_2: str
    postcode: str
    city: str
    country: str


@dataclass(frozen=True)
class DeliveryAddressInput:
    same_as_billing_address: bool
    street: str
    street_2: str
    postcode: str
    city: str
    country: str


class MemberDeliveryAddressGetter:
    @classmethod
    def get_delivery_address(
        cls, address_owner: Member | WaitingListEntry
    ) -> DeliveryAddress:
        if address_owner.delivery_same_as_billing_address:
            billing_owner = cls._get_billing_owner(address_owner=address_owner)
            return DeliveryAddress(
                street=billing_owner.street,
                street_2=billing_owner.street_2,
                postcode=billing_owner.postcode,
                city=billing_owner.city,
                country=str(billing_owner.country),
            )
        return DeliveryAddress(
            street=address_owner.delivery_street,
            street_2=address_owner.delivery_street_2,
            postcode=address_owner.delivery_postcode,
            city=address_owner.delivery_city,
            country=str(address_owner.delivery_country),
        )

    @staticmethod
    def get_delivery_address_from_input(
        delivery_address_input: DeliveryAddressInput, personal_data: dict
    ) -> DeliveryAddress:
        if delivery_address_input.same_as_billing_address:
            return DeliveryAddress(
                street=personal_data["street"],
                street_2=personal_data["street_2"],
                postcode=personal_data["postcode"],
                city=personal_data["city"],
                country=personal_data["country"],
            )
        return DeliveryAddress(
            street=delivery_address_input.street,
            street_2=delivery_address_input.street_2,
            postcode=delivery_address_input.postcode,
            city=delivery_address_input.city,
            country=delivery_address_input.country,
        )

    @staticmethod
    def _get_billing_owner(
        address_owner: Member | WaitingListEntry,
    ) -> Member | WaitingListEntry:
        # Entries of existing members carry no billing address of their own.
        if isinstance(address_owner, WaitingListEntry) and address_owner.member:
            return address_owner.member
        return address_owner
