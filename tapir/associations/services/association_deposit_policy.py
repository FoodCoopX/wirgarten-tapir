from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationDepositPaymentOption

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
            "signup_text": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_SIGNUP_TEXT, cache=cache
            ),
            "name": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_NAME, cache=cache
            ),
            "minimum": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, cache=cache
            ),
            "increment": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_INCREMENT, cache=cache
            ),
            "deposit_required_for_supporting_members": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_MUST_DEPOSIT,
                cache=cache,
            ),
            "allow_larger_signup": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP, cache=cache
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

    @staticmethod
    def is_deposit_required(has_products: bool, cache: dict) -> bool:
        return association_deposits_enabled(cache) and (
            has_products
            or get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_MUST_DEPOSIT,
                cache=cache,
            )
        )

    @classmethod
    def validate_registration_selection(
        cls,
        amount: Decimal,
        has_products: bool,
        cache: dict,
        payment_option: str,
    ) -> None:
        if not cls.is_deposit_required(has_products=has_products, cache=cache):
            return

        if payment_option == AssociationDepositPaymentOption.INDIVIDUAL_AGREEMENT:
            if not get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_SIGNUP_WITHOUT_DEPOSIT,
                cache=cache,
            ):
                raise ValidationError(
                    "Anfragen für individuelle Einlagenvereinbarungen sind nicht aktiviert."
                )

            if amount != 0:
                raise ValidationError(
                    "Bei einer offenen Vereinbarung darf kein Einlagenbetrag angenommen werden."
                )

            return

        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            amount=amount, cache=cache
        )

        if amount > get_parameter_value(
            ParameterKeys.ASSOCIATION_DEPOSIT_MINIMUM, cache=cache
        ) and not get_parameter_value(
            ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP, cache=cache
        ):
            raise ValidationError(
                "Bei der Anmeldung ist nur die Mindesteinlage erlaubt."
            )
