import datetime

from django.core.exceptions import ValidationError

from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.services.global_capacity_checker import (
    GlobalCapacityChecker,
)
from tapir.subscriptions.services.single_subscription_validator import (
    SingleSubscriptionValidator,
)
from tapir.subscriptions.services.solidarity_validator_new import SolidarityValidatorNew
from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import Member, PickupLocation, ProductType
from tapir.wirgarten.service.products import get_active_subscriptions


class OrderValidator:
    @classmethod
    def validate_order_general(
        cls,
        order: TapirOrder,
        contract_start_date: datetime.date,
        cache: dict,
        member: Member | None,
        pickup_location: PickupLocation,
    ):
        if not PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
            pickup_location=pickup_location,
            ordered_products_to_quantity_map=order,
            already_registered_member=member,
            subscription_start=contract_start_date,
            cache=cache,
        ):
            raise ValidationError(
                "Dein Abholort ist leider voll. Bitte wähle einen anderen Abholort aus."
            )

        if not SolidarityValidatorNew.is_the_ordered_solidarity_allowed(
            ordered_solidarity_factor=0,  # TODO
            order=order,
            start_date=contract_start_date,
            cache=cache,
        ):
            raise ValidationError("Solidarity factor not allowed")

        product_type_ids_without_enough_capacity = GlobalCapacityChecker.get_product_type_ids_without_enough_capacity_for_order(
            order_with_all_product_types=order,
            member_id=member.id,
            subscription_start_date=contract_start_date,
            cache=cache,
        )
        if len(product_type_ids_without_enough_capacity) > 0:
            raise ValidationError(
                f"Folgende Produkt-Typen haben nicht genug Kapazität für diese Bestellung: {product_type_ids_without_enough_capacity}"
            )

        if not SingleSubscriptionValidator.are_single_subscription_products_are_ordered_at_most_once(
            order=order, cache=cache
        ):
            raise ValidationError(
                "Manche Produkte die nur einmal bestellt werden dürfen sind mehrmals in der Bestellung"
            )

    @classmethod
    def validate_cannot_reduce_size(
        cls,
        logged_in_user_is_admin: bool,
        contract_start_date: datetime.date,
        member: Member,
        order_for_a_single_product_type: TapirOrder,
        product_type: ProductType,
        cache: dict,
    ):
        if not SubscriptionChangeValidator.should_validate_cannot_reduce_size(
            logged_in_user_is_admin=logged_in_user_is_admin,
            subscription_start_date=contract_start_date,
            cache=cache,
        ):
            return

        capacity_used_by_order = GlobalCapacityChecker.calculate_global_capacity_used_by_the_ordered_products(
            order_for_a_single_product_type=order_for_a_single_product_type,
            reference_date=contract_start_date,
            cache=cache,
        )

        capacity_used_by_the_current_subscriptions = SubscriptionChangeValidator.calculate_capacity_used_by_the_current_subscriptions(
            product_type_id=product_type.id,
            member_id=member.id,
            subscription_start_date=contract_start_date,
            cache=cache,
        )

        if capacity_used_by_order < capacity_used_by_the_current_subscriptions:
            raise ValidationError(
                f"Während eine Vertrag läuft es ist nur erlaubt die Größe des Vertrags zu erhöhen. "
                f"Deiner aktueller Vertrag für diese Periode entspricht Größe {capacity_used_by_the_current_subscriptions:.2f}. "
                f"Deiner letzter Auswahl hier entsprach Größe {capacity_used_by_order:.2f}."
            )

    @classmethod
    def validate_at_least_one_change(
        cls,
        member: Member,
        contract_start_date: datetime.date,
        cache: dict,
        order: TapirOrder,
        product_type: ProductType,
    ):
        # This avoids ending a contract and creating a new one on the same growing period if there are no changes.

        current_subscriptions = get_active_subscriptions(
            reference_date=contract_start_date, cache=cache
        ).filter(member_id=member.id, product__type__id=product_type.id)
        current_product_to_quantity_map = {
            subscription.product: subscription.quantity
            for subscription in current_subscriptions
        }
        if current_product_to_quantity_map == order:
            raise ValidationError(
                "Die Bestellung muss mindestens eine Änderung zum bisherigen Vertrag haben."
            )
