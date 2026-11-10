from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.pickup_locations.models import MemberDeliveryAddressChangedLogEntry
from tapir.pickup_locations.services.member_delivery_address_getter import (
    DeliveryAddressInput,
)
from tapir.wirgarten.models import Member, WaitingListEntry

ADDRESS_FIELDS = [
    "delivery_street",
    "delivery_street_2",
    "delivery_postcode",
    "delivery_city",
    "delivery_country",
]


class MemberDeliveryAddressSetter:
    SAME_AS_BILLING_LOG_TEXT = "Wie Rechnungsadresse"

    @classmethod
    @transaction.atomic
    def save_delivery_address(cls, member: Member, actor: TapirUser | None) -> None:
        if member.delivery_same_as_billing_address:
            for field_name in ADDRESS_FIELDS:
                setattr(member, field_name, "")

        old_address = cls._format_for_log(Member.objects.get(id=member.id))
        member.save(update_fields=["delivery_same_as_billing_address", *ADDRESS_FIELDS])
        new_address = cls._format_for_log(member)

        if new_address != old_address:
            MemberDeliveryAddressChangedLogEntry().populate_delivery_address(
                actor=actor,
                user=member,
                old_address=old_address,
                new_address=new_address,
            ).save()

    @staticmethod
    def copy_delivery_address(
        source: Member | WaitingListEntry, target: Member | WaitingListEntry
    ) -> None:
        for field_name in ["delivery_same_as_billing_address", *ADDRESS_FIELDS]:
            setattr(target, field_name, getattr(source, field_name))

    @staticmethod
    def apply_delivery_address_input(
        target: Member | WaitingListEntry, delivery_address_input: DeliveryAddressInput
    ) -> None:
        target.delivery_same_as_billing_address = (
            delivery_address_input.same_as_billing_address
        )
        target.delivery_street = delivery_address_input.street
        target.delivery_street_2 = delivery_address_input.street_2
        target.delivery_postcode = delivery_address_input.postcode
        target.delivery_city = delivery_address_input.city
        target.delivery_country = delivery_address_input.country

    @classmethod
    def _format_for_log(cls, member: Member) -> str:
        if member.delivery_same_as_billing_address:
            return cls.SAME_AS_BILLING_LOG_TEXT
        return ", ".join(
            part
            for part in [
                member.delivery_street,
                member.delivery_street_2,
                f"{member.delivery_postcode} {member.delivery_city}".strip(),
                str(member.delivery_country),
            ]
            if part
        )
