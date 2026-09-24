import datetime
from datetime import date
from typing import Any

from tapir.pickup_locations.services.member_pickup_location_cleaner import (
    MemberPickupLocationCleaner,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.waiting_list.services.waiting_list_entry_confirmation_applier import (
    WaitingListEntryConfirmationApplier,
)
from tapir.wirgarten.models import (
    WaitingListEntry,
    Product,
    PickupLocation,
    Member,
)


class CanBeFulFilledChecker:
    @classmethod
    def check_if_entry_can_be_fulfilled(cls, entry: WaitingListEntry, cache: dict):
        has_pickup_location_wishes = entry.pickup_location_wishes.exists()
        has_product_wishes = entry.product_wishes.exists()

        if not has_pickup_location_wishes and not has_product_wishes:
            return False

        order: TapirOrder = TapirOrderBuilder.build_tapir_order_from_waiting_list_entry(
            entry
        )

        subscription_start = (
            WaitingListEntryConfirmationApplier.get_contract_start_date(
                waiting_list_entry=entry, cache=cache
            )
        )

        if has_product_wishes and not cls._check_product_wishes_capacity(
            order=order, entry=entry, subscription_start=subscription_start, cache=cache
        ):
            return False

        return cls._check_pickup_location_capacity(
            has_pickup_location_wishes=has_pickup_location_wishes,
            entry=entry,
            order=order,
            subscription_start=subscription_start,
            cache=cache,
        )

    @classmethod
    def _check_pickup_location_capacity(
        cls,
        has_pickup_location_wishes: bool,
        entry: WaitingListEntry,
        order: dict[Product, int],
        subscription_start: date,
        cache: dict[Any, Any],
    ) -> bool:
        if not cls._is_pickup_location_required(
            order=order,
            member=entry.member,
            subscription_start=subscription_start,
            cache=cache,
        ):
            return True

        pickup_locations = cls._get_pickup_locations(
            cache, entry, has_pickup_location_wishes, subscription_start
        )

        if len(pickup_locations) == 0:
            return False

        if len(order) == 0 and entry.member is not None:
            subscriptions = TapirCache.get_active_and_future_subscriptions_by_member_id(
                reference_date=subscription_start, cache=cache
            ).get(entry.member_id, [])
            order = {
                subscription.product: subscription.quantity
                for subscription in subscriptions
            }

        return any(
            PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                pickup_location=pickup_location,
                order=order,
                already_registered_member=entry.member,
                subscription_start=subscription_start,
                cache=cache,
                check_waiting_list_entries=False,
            )
            for pickup_location in pickup_locations
        )

    @classmethod
    def _is_pickup_location_required(
        cls,
        order: TapirOrder,
        member: Member | None,
        subscription_start: datetime.date,
        cache: dict,
    ):
        if OrderValidator.does_order_need_a_pickup_location(order=order, cache=cache):
            return True

        if member is None:
            return False

        return MemberPickupLocationCleaner.does_member_have_at_least_one_delivered_subscription(
            reference_date=subscription_start, member=member, cache=cache
        )

    @classmethod
    def _get_pickup_locations(
        cls,
        cache: dict[Any, Any],
        entry: WaitingListEntry,
        has_pickup_location_wishes: bool,
        subscription_start: date,
    ) -> list[PickupLocation]:
        if has_pickup_location_wishes:
            pickup_locations = [
                pickup_location_wish.pickup_location
                for pickup_location_wish in entry.pickup_location_wishes.all()
            ]
        else:
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=entry.member_id,
                    reference_date=subscription_start,
                    cache=cache,
                )
            )
            if pickup_location_id is None:
                pickup_locations = []
            else:
                pickup_locations = [
                    TapirCache.get_pickup_location_by_id(
                        cache=cache, pickup_location_id=pickup_location_id
                    )
                ]
        return pickup_locations

    @classmethod
    def _check_product_wishes_capacity(
        cls,
        order: TapirOrder,
        entry: WaitingListEntry,
        subscription_start: datetime.date,
        cache: dict,
    ):
        product_type_ids_without_enough_capacity = GlobalCapacityChecker.get_product_type_ids_without_enough_capacity_for_order(
            order_with_all_product_types=order,
            member_id=str(entry.member_id) if entry.member else None,
            subscription_start_date=subscription_start,
            cache=cache,
            check_waiting_list_entries=False,
        )

        if product_type_ids_without_enough_capacity:
            return False

        return all(
            ProductCapacityChecker.does_product_have_enough_free_capacity_to_add_order(
                member_id=str(entry.member_id) if entry.member else None,
                product=product,
                ordered_quantity=quantity,
                subscription_start_date=subscription_start,
                cache=cache,
            )
            for product, quantity in order.items()
        )
