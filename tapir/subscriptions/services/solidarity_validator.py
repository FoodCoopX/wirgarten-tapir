import datetime
from decimal import Decimal
from functools import cmp_to_key

from django.core.exceptions import ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.config import (
    SOLIDARITY_MODE_ONLY_POSITIVE,
    SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_subscriptions,
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

        values_as_string = parameter_value.split(",")
        values: list[float | str] = [float(value.strip()) for value in values_as_string]

        if 0 not in values:
            values.append(0)

        if "custom" not in values:
            values.append("custom")

        return {value: cls.get_value_display(value=value) for value in values}

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
    def get_value_display(cls, value):
        if value == 0:
            return "0€"
        if value == "custom":
            return "Ich möchte einen anderen Betrag zahlen"

        return f"{value:+g}€"

    @classmethod
    def validate_solidarity_dropdown_values(cls, solidarity_values_as_string: str):
        try:
            cls.get_solidarity_dropdown_values(solidarity_values_as_string, cache={})
        except Exception as e:
            raise ValidationError(f"Invalid solidarity values: {e}")

    @classmethod
    def validate_solidarity_price(cls, form, start_date: datetime.date, cache: dict):
        solidarity_fields = form.build_solidarity_fields()

        solidarity_price_absolute = solidarity_fields.get(
            "solidarity_price_absolute", None
        )
        if solidarity_price_absolute is None:
            return

        if solidarity_price_absolute >= 0:
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

        amount_of_used_solidarity = -solidarity_price_absolute

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
    ) -> Decimal:
        return sum(
            [
                cls.get_solidarity_factor_of_subscription(
                    subscription=subscription,
                    reference_date=reference_date,
                    cache=cache,
                )
                for subscription in get_active_subscriptions(
                    reference_date=reference_date, cache=cache
                ).select_related("product")
            ],
            Decimal(0),
        )

    @classmethod
    def get_solidarity_factor_of_subscription(
        cls, subscription: Subscription, reference_date: datetime.date, cache: dict
    ) -> Decimal:
        return subscription.solidarity_price_absolute or 0

    @classmethod
    def get_solidarity_contribution_minimum(
        cls, reference_date: datetime.date, cache: dict
    ) -> float | None:
        enabled = get_parameter_value(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        if enabled == SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED:
            return None
        if enabled == SOLIDARITY_MODE_ONLY_POSITIVE:
            return 0.0

        return min(
            0.0,
            -float(
                cls.get_solidarity_excess(
                    reference_date=reference_date, cache=cache
                ).quantize(Decimal("0.01"))
            ),
        )
