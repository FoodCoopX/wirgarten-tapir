import datetime

from tapir.wirgarten.models import Product
from tapir.wirgarten.service.products import get_product_price


class SubscriptionChangeValidatorNew:

    @classmethod
    def validate_total_capacity(
            cls,
            ordered_products_to_quantity_map: dict[Product, int],
            member_id: str,
            subscription_start_date: datetime.date,
            cache: dict,
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
    def calculate_global_capacity_used_by_the_ordered_products(
            cls,
            ordered_products_to_quantity_map: dict[Product, int],
            reference_date: datetime.date,
            cache: dict = None,
    ):
        total = 0.0
        for product, quantity in ordered_products_to_quantity_map:
            product_price_object = get_product_price(
                product=product, reference_date=reference_date, cache=cache
            )
            total += float(product_price_object.size) * quantity
        return total
