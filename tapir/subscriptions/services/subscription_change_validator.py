import datetime
from typing import Dict

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.forms import Form
from django.utils.translation import gettext_lazy as _

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, PickupLocation, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_current_growing_period,
    get_product_price,
    get_active_subscriptions,
    get_free_product_capacity,
)
from tapir.wirgarten.utils import get_today


class SubscriptionChangeValidator:
    @classmethod
    def validate_cannot_reduce_size(
        cls,
        logged_in_user_is_admin: bool,
        subscription_start_date: datetime.date,
        member_id: str,
        form: Form,
        field_prefix: str,
        product_type_id: str,
        cache: Dict,
    ):
        if not cls.should_validate_cannot_reduce_size(
            logged_in_user_is_admin=logged_in_user_is_admin,
            subscription_start_date=subscription_start_date,
            cache=cache,
        ):
            return

        capacity_used_by_the_ordered_products = (
            cls.calculate_capacity_used_by_the_ordered_products(
                form=form,
                return_capacity_in_euros=False,
                field_prefix=field_prefix,
                cache=cache,
            )
        )

        capacity_used_by_the_current_subscriptions = (
            cls.calculate_capacity_used_by_the_current_subscriptions(
                product_type_id=product_type_id,
                member_id=member_id,
                subscription_start_date=subscription_start_date,
                cache=cache,
            )
        )

        if (
            capacity_used_by_the_ordered_products
            < capacity_used_by_the_current_subscriptions
        ):
            raise ValidationError(
                _(
                    f"Während eine Vertrag läuft es ist nur erlaubt die Größe des Vertrags zu erhöhen. "
                    f"Deiner aktueller Vertrag für diese Periode entspricht Größe {capacity_used_by_the_current_subscriptions:.2f}. "
                    f"Deiner letzter Auswahl hier entsprach Größe {capacity_used_by_the_ordered_products:.2f}."
                )
            )

    @classmethod
    def should_validate_cannot_reduce_size(
        cls,
        logged_in_user_is_admin: bool,
        subscription_start_date: datetime.date,
        cache: Dict,
    ):
        if logged_in_user_is_admin:
            return False

        # Members cannot reduce the size of their subscriptions for the currently ongoing growing period.
        growing_period = get_current_growing_period(
            subscription_start_date, cache=cache
        )

        if not growing_period:
            return False
        if growing_period.start_date > get_today(cache=cache):
            return False

        return True

    @classmethod
    def calculate_capacity_used_by_the_ordered_products(
        cls,
        form: Form,
        return_capacity_in_euros: bool,
        field_prefix: str,
        cache: Dict = None,
    ):
        total = 0.0
        for key, quantity in form.cleaned_data.items():
            if not key.startswith(field_prefix) or not quantity:
                continue
            next_month = get_today(cache=cache) + relativedelta(months=1, day=1)
            product = TapirCache.get_product_by_name_iexact(
                cache, key.replace(field_prefix, "")
            )
            product_price_object = get_product_price(product, next_month, cache=cache)
            relevant_value = getattr(
                product_price_object, "price" if return_capacity_in_euros else "size"
            )
            total += float(relevant_value) * quantity
        return total

    @classmethod
    def calculate_capacity_used_by_the_current_subscriptions(
        cls,
        product_type_id: str,
        member_id: str,
        subscription_start_date: datetime.date,
        cache: Dict,
    ):
        current_subscriptions = get_active_subscriptions(
            subscription_start_date, cache=cache
        ).filter(member_id=member_id, product__type_id=product_type_id)
        return sum(
            [
                subscription.get_used_capacity(cache=cache)
                for subscription in current_subscriptions
            ]
        )

    @classmethod
    def validate_total_capacity(
        cls,
        form: Form,
        field_prefix: str,
        product_type_id: str,
        member_id: str,
        subscription_start_date: datetime.date,
        cache: Dict,
    ):
        free_capacity = get_free_product_capacity(
            product_type_id=product_type_id,
            reference_date=subscription_start_date,
            cache=cache,
        )
        capacity_used_by_the_ordered_products = (
            cls.calculate_capacity_used_by_the_ordered_products(
                form=form,
                return_capacity_in_euros=False,
                field_prefix=field_prefix,
                cache=cache,
            )
        )

        capacity_used_by_the_current_subscriptions = (
            cls.calculate_capacity_used_by_the_current_subscriptions(
                product_type_id=product_type_id,
                member_id=member_id,
                subscription_start_date=subscription_start_date,
                cache=cache,
            )
        )

        if free_capacity < (
            capacity_used_by_the_ordered_products
            - float(capacity_used_by_the_current_subscriptions)
        ):
            raise ValidationError(
                f"Die ausgewählte Ernteanteile sind größer als die verfügbare Kapazität! Verfügbar: {round(free_capacity, 2)}"
            )

    @classmethod
    def validate_pickup_location_capacity(
        cls,
        pickup_location: PickupLocation,
        form: Form,
        field_prefix: str,
        subscription_start_date: datetime.date,
        member: Member,
        cache: Dict,
    ):
        ordered_products_to_quantity_map = {}
        for key, quantity in form.cleaned_data.items():
            if not key.startswith(field_prefix):
                continue
            product = TapirCache.get_product_by_name_iexact(
                cache, key.replace(field_prefix, "")
            )
            ordered_products_to_quantity_map[product] = quantity

        if not PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
            pickup_location=pickup_location,
            ordered_products_to_quantity_map=ordered_products_to_quantity_map,
            already_registered_member=member,
            subscription_start=subscription_start_date,
            cache=cache,
        ):
            raise ValidationError(
                _(
                    "Dein Abholort ist leider voll. Bitte wähle einen anderen Abholort aus."
                )
            )

    @classmethod
    def validate_must_be_subscribed_to(
        cls,
        form: Form,
        field_prefix: str,
        product_type: ProductType,
        cache: Dict,
    ):
        if not product_type.must_be_subscribed_to:
            return

        capacity_used_by_the_ordered_products = (
            cls.calculate_capacity_used_by_the_ordered_products(
                form=form,
                return_capacity_in_euros=False,
                field_prefix=field_prefix,
                cache=cache,
            )
        )

        if capacity_used_by_the_ordered_products <= 0:
            raise ValidationError(_("Dieses Produkt ist Pflicht."))

    @classmethod
    def validate_single_subscription(
        cls,
        form: Form,
        field_prefix: str,
        product_type: ProductType,
    ):
        if not product_type.single_subscription_only:
            return

        nb_checked = 0
        for key, checked in form.cleaned_data.items():
            if not key.startswith(field_prefix) or not checked:
                continue
            nb_checked += 1

        if nb_checked > 1:
            raise ValidationError(
                _(f"{product_type.name} dürfen nur einmal ausgewählt werden.")
            )

    @classmethod
    def validate_soliprice_change(
        cls,
        form,
        field_prefix: str,
        member_id: str,
        logged_in_user_is_admin: bool,
        subscription_start_date: datetime.date,
        cache: Dict,
    ):
        if logged_in_user_is_admin:
            return

        if get_parameter_value(
            ParameterKeys.HARVEST_MEMBERS_ARE_ALLOWED_TO_CHANGE_SOLIPRICE, cache=cache
        ):
            return

        solidarity_fields = form.build_solidarity_fields()
        if "solidarity_price_absolute" not in solidarity_fields:
            solidarity_fields["solidarity_price_absolute"] = None
        else:
            solidarity_fields["solidarity_price_absolute"] = float(
                solidarity_fields["solidarity_price_absolute"]
            )

        growing_period = get_current_growing_period(
            reference_date=subscription_start_date, cache=cache
        )
        if growing_period and growing_period.start_date > get_today(cache=cache):
            return

        for key in form.cleaned_data.keys():
            if not key.startswith(field_prefix):
                continue
            product = TapirCache.get_product_by_name_iexact(
                cache, key.replace(field_prefix, "")
            )

            subscription_to_same_product = (
                get_active_subscriptions(
                    reference_date=subscription_start_date, cache=cache
                )
                .filter(member_id=member_id, product=product)
                .first()
            )
            if subscription_to_same_product is None:
                continue

            if (
                subscription_to_same_product.solidarity_price_absolute
                != solidarity_fields["solidarity_price_absolute"]
                or subscription_to_same_product.solidarity_price
                != float(solidarity_fields["solidarity_price"])
            ):
                raise ValidationError(
                    "Der Solidarbeitrag darf nicht während ein Vertrag läuft geändert werden."
                )

    @classmethod
    def validate_at_least_one_change(
        cls,
        form,
        field_prefix: str,
        member_id: str,
        subscription_start_date: datetime.date,
        cache: Dict,
    ):
        subscribed_product_ids = set(
            get_active_subscriptions(
                reference_date=subscription_start_date, cache=cache
            )
            .filter(member_id=member_id)
            .values_list("product_id", flat=True)
        )
        ordered_product_ids = set()

        solidarity_fields = form.build_solidarity_fields()
        if "solidarity_price_absolute" not in solidarity_fields:
            solidarity_fields["solidarity_price_absolute"] = None
        else:
            solidarity_fields["solidarity_price_absolute"] = float(
                solidarity_fields["solidarity_price_absolute"]
            )

        for key, quantity in form.cleaned_data.items():
            if not key.startswith(field_prefix):
                continue

            product = TapirCache.get_product_by_name_iexact(
                cache, key.replace(field_prefix, "")
            )
            if quantity == 0:
                continue
            ordered_product_ids.add(product.id)

            if product.id not in subscribed_product_ids:
                return

            subscription_to_same_product = (
                get_active_subscriptions(
                    reference_date=subscription_start_date, cache=cache
                )
                .filter(member_id=member_id, product=product)
                .first()
            )
            if subscription_to_same_product is None:
                return

            if subscription_to_same_product.quantity != quantity:
                return

            if (
                subscription_to_same_product.solidarity_price_absolute
                != solidarity_fields["solidarity_price_absolute"]
                or subscription_to_same_product.solidarity_price
                != float(solidarity_fields["solidarity_price"])
            ):
                return

        if subscribed_product_ids != ordered_product_ids:
            return

        raise ValidationError(
            "Die Bestellung muss mindestens eine Änderung zum bisherigen Vertrag haben."
        )
