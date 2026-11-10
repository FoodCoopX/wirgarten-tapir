from dataclasses import dataclass

from tapir.wirgarten.models import Member


@dataclass(frozen=True)
class DeliveryAddress:
    street: str
    street_2: str
    postcode: str
    city: str
    country: str


class MemberDeliveryAddressGetter:
    @classmethod
    def get_delivery_address(cls, member: Member) -> DeliveryAddress:
        if member.delivery_same_as_billing_address:
            return DeliveryAddress(
                street=member.street,
                street_2=member.street_2,
                postcode=member.postcode,
                city=member.city,
                country=str(member.country),
            )
        return DeliveryAddress(
            street=member.delivery_street,
            street_2=member.delivery_street_2,
            postcode=member.delivery_postcode,
            city=member.delivery_city,
            country=str(member.delivery_country),
        )
