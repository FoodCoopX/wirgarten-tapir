from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import (
    WaitingListEntry,
    WaitingListProductWish,
    WaitingListPickupLocationWish,
    Member,
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
        return cls._create_entry(
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
        growing_period_id: str,
        member: Member,
        cache: dict,
    ):
        pickup_location_ids_in_priority_order = (
            cls.get_pickup_location_ids_that_should_go_on_waiting_list(
                pickup_location_ids=pickup_location_ids_in_priority_order,
                member=member,
                growing_period_id=growing_period_id,
                cache=cache,
            )
        )
        return cls._create_entry(
            order=order,
            pickup_location_ids_in_priority_order=pickup_location_ids_in_priority_order,
            number_of_coop_shares=0,
            personal_data=None,
            member_id=member.id,
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

        if personal_data is not None:
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
        for product, quantity in order.items():
            if quantity == 0:
                continue
            product_wishes.append(
                WaitingListProductWish(
                    waiting_list_entry=entry,
                    product_id=product.id,
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
            "last_name",
            "email",
            "phone_number",
            "street",
            "street_2",
            "postcode",
            "city",
        ]
        for field in fields:
            setattr(waiting_list_entry, field, validated_data[field])

    @classmethod
    def get_pickup_location_ids_that_should_go_on_waiting_list(
        cls,
        pickup_location_ids: list[str],
        growing_period_id: str,
        member: Member,
        cache: dict,
    ):
        contract_start_date = BestellWizardOrderValidator.validated_growing_period_and_get_contract_start_date(
            growing_period_id=growing_period_id,
            cache=cache,
        )
        current_pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=contract_start_date
            )
        )
        return [
            pickup_location_id
            for pickup_location_id in pickup_location_ids
            if pickup_location_id != current_pickup_location_id
        ]
