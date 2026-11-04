import datetime
import math
from decimal import Decimal
from typing import Iterable

from django.core.exceptions import ValidationError

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.core.exceptions import TapirImproperlyConfigured
from tapir.subscriptions import config
from tapir.subscriptions.config import (
    SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED,
    SOLIDARITY_MODE_ONLY_POSITIVE,
)
from tapir.subscriptions.services.automatic_solidarity_contribution_renewal_service import (
    AutomaticSolidarityContributionRenewalService,
)
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Product
from tapir.wirgarten.parameter_keys import ParameterKeys


class SolidarityValidator:
    @classmethod
    def is_the_ordered_solidarity_allowed(
        cls,
        amount: float,
        start_date: datetime.date,
        order: TapirOrder,
        cache: dict,
    ) -> bool:
        product_minimum = cls.get_product_solidarity_minimum(order.keys())
        if product_minimum is not None and amount < product_minimum:
            return False

        if amount >= 0:
            return True

        minimum = cls.get_solidarity_contribution_minimum(
            reference_date=start_date, cache=cache
        )
        if amount < minimum:
            return False

        solidarity_mode = get_parameter_value(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        match solidarity_mode:
            case config.SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED:
                return True
            case config.SOLIDARITY_MODE_ONLY_POSITIVE:
                return False
            case config.SOLIDARITY_MODE_NEGATIVE_ALLOWED_IF_ENOUGH_POSITIVE:
                excess_solidarity = cls.get_solidarity_excess(
                    reference_date=start_date, cache=cache
                )
                amount_of_used_solidarity_in_euros = -amount
                return amount_of_used_solidarity_in_euros < excess_solidarity
            case _:
                raise TapirImproperlyConfigured(
                    f"Unknown solidarity mode: '{solidarity_mode}'"
                )

    @classmethod
    def get_solidarity_excess(
        cls,
        reference_date: datetime.date,
        cache: dict,
    ) -> Decimal:
        relevant_contributions = AutomaticSolidarityContributionRenewalService.get_current_and_renewed_solidarity_contributions_at_date(
            reference_date=reference_date, cache=cache
        )
        return sum(
            [contribution.amount for contribution in relevant_contributions],
            start=Decimal(0),
        )

    @classmethod
    def get_solidarity_contribution_minimum(
        cls, reference_date: datetime.date, cache: dict
    ) -> float:
        enabled = get_parameter_value(
            key=ParameterKeys.HARVEST_NEGATIVE_SOLIPRICE_ENABLED, cache=cache
        )
        if enabled == SOLIDARITY_MODE_ONLY_POSITIVE:
            return 0.0

        configured_minimum = float(
            get_parameter_value(key=ParameterKeys.SOLIDARITY_MINIMUM, cache=cache)
        )
        if enabled == SOLIDARITY_MODE_NEGATIVE_ALWAYS_ALLOWED:
            return configured_minimum

        minimum_from_solidarity_excess = min(
            0.0,
            -float(
                cls.get_solidarity_excess(
                    reference_date=reference_date, cache=cache
                ).quantize(Decimal("0.01"))
            ),
        )
        return max(configured_minimum, minimum_from_solidarity_excess)

    @classmethod
    def get_solidarity_dropdown_values(
        cls, parameter_value: str | None = None, cache: dict | None = None
    ):
        if parameter_value is None:
            parameter_value = get_parameter_value(
                ParameterKeys.SOLIDARITY_CHOICES, cache=cache
            )

        values: list[float | str] = cls.parse_solidarity_choices(parameter_value)

        if 0 not in values:
            values.append(0)

        if "custom" not in values:
            values.append("custom")

        return {value: cls.get_value_display(value=value) for value in values}

    @classmethod
    def parse_solidarity_choices(cls, value: str) -> list[float]:
        if value.strip() == "":
            return []
        choices = [float(choice.strip()) for choice in value.split(",")]
        for choice in choices:
            if not math.isfinite(choice):
                # Filters out values like inf or NaN
                raise ValueError(f"'{choice}' ist keine gültige Zahl")
        return choices

    @classmethod
    def get_product_solidarity_choices(cls, products: Iterable[Product]) -> set[float]:
        choices = set()
        for product in products:
            choices.update(cls.parse_solidarity_choices(product.solidarity_choices))
        return choices

    @classmethod
    def get_product_solidarity_minimum(
        cls, products: Iterable[Product]
    ) -> float | None:
        choices = cls.get_product_solidarity_choices(products)
        if len(choices) == 0:
            return None
        return min(choices)

    @classmethod
    def get_product_solidarity_minimum_for_member(
        cls, member_id: str, reference_date: datetime.date, cache: dict
    ) -> float | None:
        products = {
            subscription.product
            for subscription in TapirCache.get_all_subscriptions_for_member(
                member_id=member_id, cache=cache
            )
            if subscription.end_date >= reference_date
        }
        return cls.get_product_solidarity_minimum(products)

    @classmethod
    def get_violated_product_minimum(
        cls,
        logged_in_user: TapirUser,
        target_member_id: str,
        new_amount: Decimal,
        change_date: datetime.date,
        cache: dict,
    ) -> float | None:
        if logged_in_user.has_perm(Permission.Coop.MANAGE):
            return None

        minimum = cls.get_product_solidarity_minimum_for_member(
            member_id=target_member_id, reference_date=change_date, cache=cache
        )
        if minimum is None or new_amount >= Decimal(str(minimum)):
            return None

        return minimum

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
            raise ValidationError(f"Ungültiger Solidarbeitrag-Wert: {e}")
