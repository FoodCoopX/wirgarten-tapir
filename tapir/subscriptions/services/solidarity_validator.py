import datetime
from functools import cmp_to_key

from django.core.exceptions import ValidationError
from environ import ImproperlyConfigured

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.config import (
    SOLIDARITY_UNIT_PERCENT,
    SOLIDARITY_UNIT_ABSOLUTE,
    SOLIDARITY_MODE_ONLY_POSITIVE,
    SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED,
)
from tapir.subscriptions.services.subscription_change_validator import (
    SubscriptionChangeValidator,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_product_price,
    get_active_and_future_subscriptions,
)


class SolidarityValidator:
    @classmethod
    def get_solidarity_dropdown_values(
        cls, parameter_value: str = None, cache: dict = None
    ):
        if parameter_value is None:
            parameter_value = get_parameter_value(
                ParameterKeys.SOLIDARITY_CHOICES, cache=cache
            )
            unit = get_parameter_value(ParameterKeys.SOLIDARITY_UNIT, cache=cache)
        else:
            unit = SOLIDARITY_UNIT_PERCENT

        values_as_string = parameter_value.split(",")
        values: list[float | str] = [float(value.strip()) for value in values_as_string]

        if 0 not in values:
            values.append(0)

        if "custom" not in values:
            values.append("custom")

        return {
            value: cls.get_value_display(value=value, unit=unit) for value in values
        }

    @classmethod
    def get_solidarity_dropdown_value_as_sorted_tuples(cls, cache: dict):
        solidarity_choices = [
            (value, display)
            for value, display in cls.get_solidarity_dropdown_values(
                cache=cache
            ).items()
        ]

        def compare_options(a, b):
            if a[0] == 0:
                return -1
            if b[0] == 0:
                return 1

            if a[0] == "custom":
                return 1
            if b[0] == "custom":
                return -1

            return b[0] - a[0]

        solidarity_choices.sort(key=cmp_to_key(compare_options))

        return solidarity_choices

    @classmethod
    def get_value_display(cls, value, unit):
        if value == 0:
            return "Ich möchte den Richtpreis zahlen"
        if value == "custom":
            return "Ich möchte einen anderen Betrag zahlen  ⟶"

        if unit == SOLIDARITY_UNIT_ABSOLUTE:
            return f"{value:+g}€"
        if unit == SOLIDARITY_UNIT_PERCENT:
            return f"{value:+g}%"

        raise ImproperlyConfigured(
            f"Unknown value for parameter {ParameterKeys.SOLIDARITY_UNIT}: '{unit}'"
        )

    @classmethod
    def validate_solidarity_dropdown_values(cls, solidarity_values_as_string: str):
        try:
            cls.get_solidarity_dropdown_values(solidarity_values_as_string, cache={})
        except Exception as e:
            raise ValidationError(f"Invalid solidarity values: {e}")

    @classmethod
    def validate_solidarity_price(
        cls, form, start_date: datetime.date, field_prefix: str, cache: dict
    ):
        solidarity_fields = form.build_solidarity_fields()

        solidarity_price_percentage = solidarity_fields.get(
            "solidarity_price_percentage", None
        )
        solidarity_price_absolute = solidarity_fields.get(
            "solidarity_price_absolute", None
        )
        if solidarity_price_percentage is None and solidarity_price_absolute is None:
            return

        ordered_solidarity_factor = (
            solidarity_price_percentage
            if solidarity_price_percentage is not None
            else solidarity_price_absolute
        )
        if ordered_solidarity_factor >= 0:
            return

        solidarity_mode = get_parameter_value(
            ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        if solidarity_mode == SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED:
            return

        if solidarity_mode == SOLIDARITY_MODE_ONLY_POSITIVE:
            raise ValidationError("Negative Solidarbeiträge sind nicht erlaubt")

        excess_solidarity = cls.get_solidarity_excess(
            reference_date=start_date, cache=cache
        )

        if (
            get_parameter_value(ParameterKeys.SOLIDARITY_UNIT, cache=cache)
            == SOLIDARITY_UNIT_ABSOLUTE
        ):
            amount_of_used_solidarity = -ordered_solidarity_factor
        else:
            total_price_of_order = SubscriptionChangeValidator.calculate_capacity_used_by_the_ordered_products(
                form=form,
                return_capacity_in_euros=True,
                field_prefix=field_prefix,
                cache=cache,
            )
            amount_of_used_solidarity = total_price_of_order * -(
                ordered_solidarity_factor
            )

        if amount_of_used_solidarity > excess_solidarity:
            raise ValidationError(
                {
                    "solidarity_price_choice": "Der Solidartopf ist leider nicht ausreichend ausgefüllt.",
                    "solidarity_price_custom": "Der Solidartopf ist leider nicht ausreichend ausgefüllt.",
                }
            )

    @classmethod
    def get_solidarity_excess(
        cls,
        reference_date: datetime.date,
        cache: dict,
    ) -> float:
        return sum(
            [
                cls.get_solidarity_factor_of_subscription(
                    subscription=subscription,
                    reference_date=reference_date,
                    cache=cache,
                )
                for subscription in get_active_and_future_subscriptions(
                    reference_date=reference_date, cache=cache
                ).select_related("product")
            ]
        )

    @classmethod
    def get_solidarity_factor_of_subscription(
        cls, subscription: Subscription, reference_date: datetime.date, cache: dict
    ) -> float:
        if subscription.solidarity_price_absolute is not None:
            return float(subscription.solidarity_price_absolute)

        if subscription.solidarity_price_percentage is None:
            return 0

        product_price = get_product_price(
            product=subscription.product, reference_date=reference_date, cache=cache
        ).price
        total_subscription_price_without_solidarity = (
            float(product_price) * subscription.quantity
        )
        return (
            total_subscription_price_without_solidarity
            * subscription.solidarity_price_percentage
        )
