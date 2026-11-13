from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_settings import (
    association_deposits_enabled,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys


class AssociationDepositPolicy:
    @classmethod
    def get_settings(cls, cache: dict) -> dict:
        return {
            "enabled": association_deposits_enabled(cache),
            "name": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_NAME, cache=cache
            ),
            "minimum": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, cache=cache
            ),
            "increment": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, cache=cache
            ),
            "supporting_members_required": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_MUST_DEPOSIT,
                cache=cache,
            ),
            "allow_larger_signup": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP, cache=cache
            ),
            "allow_member_increase": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, cache=cache
            ),
            "allow_signup_without_deposit": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_SIGNUP_WITHOUT_DEPOSIT,
                cache=cache,
            ),
            "signup_without_deposit_label": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_SIGNUP_WITHOUT_DEPOSIT_LABEL,
                cache=cache,
            ),
        }

    @classmethod
    def validate_signup_selection(
        cls,
        amount: Decimal | None,
        has_products: bool,
        cache: dict,
        payment_option: str = "once",
    ) -> None:
        if payment_option not in ("once", "individual_agreement"):
            raise ValidationError("Bitte eine gültige Einlagenauswahl angeben.")
        if payment_option == "individual_agreement":
            if not association_deposits_enabled(cache) or not get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_SIGNUP_WITHOUT_DEPOSIT,
                cache=cache,
            ):
                raise ValidationError(
                    "Anfragen für individuelle Einlagenvereinbarungen sind nicht aktiviert."
                )
            if amount is not None:
                raise ValidationError(
                    "Bei einer offenen Vereinbarung darf kein Einlagenbetrag angenommen werden."
                )
            return None
        cls.validate_signup_amount(amount, has_products, cache)

    @classmethod
    def validate_signup_amount(
        cls, amount: Decimal | None, has_products: bool, cache: dict
    ):
        settings = cls.get_settings(cache)
        if not settings["enabled"]:
            if amount not in (None, Decimal("0")):
                raise ValidationError("Vereinseinlagen sind nicht aktiviert.")
            return
        required = has_products or settings["supporting_members_required"]
        if amount in (None, Decimal("0")) and not required:
            return
        if amount is None:
            raise ValidationError("Bitte die Vereinseinlage auswählen.")
        AssociationDepositAmountValidator.validate_regular_deposit_amount(amount, cache)
        if amount > settings["minimum"] and not settings["allow_larger_signup"]:
            raise ValidationError(
                "Bei der Anmeldung ist nur die Mindesteinlage erlaubt."
            )
