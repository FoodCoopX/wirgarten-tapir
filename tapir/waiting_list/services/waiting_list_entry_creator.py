from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import (
    WaitingListEntry,
    WaitingListProductWish,
    WaitingListPickupLocationWish,
)
from tapir.wirgarten.utils import get_now


class WaitingListEntryCreator:
    @classmethod
    def create_entry_potential_member(
        cls,
        order: TapirOrder,
        pickup_location_ids_in_priority_order: list[str],
        number_of_coop_shares: int,
        personal_data: dict,
        cache: dict,
    ):
        cls._create_entry(
            order=order,
            pickup_location_ids_in_priority_order=pickup_location_ids_in_priority_order,
            number_of_coop_shares=number_of_coop_shares,
            personal_data=personal_data,
            member_id=None,
            cache=cache,
        )

    @classmethod
    def create_entry_existing_member(
        cls,
        order: TapirOrder,
        pickup_location_ids_in_priority_order: list[str],
        member_id: str,
        cache: dict,
    ):
        cls._create_entry(
            order=order,
            pickup_location_ids_in_priority_order=pickup_location_ids_in_priority_order,
            number_of_coop_shares=0,
            personal_data=None,
            member_id=member_id,
            cache=cache,
        )

    @classmethod
    def _create_entry(
        cls,
        order: TapirOrder,
        pickup_location_ids_in_priority_order: list[str],
        number_of_coop_shares: int,
        personal_data: dict | None,
        member_id: None | str,
        cache: dict,
    ):
        waiting_list_entry = WaitingListEntry(
            privacy_consent=get_now(cache=cache),
            number_of_coop_shares=number_of_coop_shares,
            member_id=member_id,
        )

        if member_id is None:
            cls.set_personal_data_from_validated_data(waiting_list_entry, personal_data)

        waiting_list_entry.save()

        cls.create_product_wishes(order=order, entry=waiting_list_entry)
        cls.create_pickup_location_wishes(
            pickup_location_ids_in_priority_order=pickup_location_ids_in_priority_order,
            entry=waiting_list_entry,
        )

        return waiting_list_entry

    @classmethod
    def create_product_wishes(cls, order: TapirOrder, entry: WaitingListEntry):
        product_wishes = []
        for product_id, quantity in order:
            if quantity == 0:
                continue
            product_wishes.append(
                WaitingListProductWish(
                    waiting_list_entry=entry,
                    product_id=product_id,
                    quantity=quantity,
                )
            )
        WaitingListProductWish.objects.bulk_create(product_wishes)

    @classmethod
    def create_pickup_location_wishes(
        cls, pickup_location_ids_in_priority_order: list[str], entry: WaitingListEntry
    ):
        pickup_location_wishes = []
        for index, pickup_location_id in enumerate(
            pickup_location_ids_in_priority_order
        ):
            pickup_location_wishes.append(
                WaitingListPickupLocationWish(
                    waiting_list_entry=entry,
                    pickup_location_id=pickup_location_id,
                    priority=index + 1,
                )
            )
        WaitingListPickupLocationWish.objects.bulk_create(pickup_location_wishes)

    @classmethod
    def set_personal_data_from_validated_data(
        cls, waiting_list_entry: WaitingListEntry, validated_data: dict
    ):
        fields = [
            "first_name",
            "last_name" "email",
            "phone_number",
            "street",
            "street_2",
            "postcode",
            "city",
        ]
        for field in fields:
            setattr(waiting_list_entry, field, validated_data[field])
