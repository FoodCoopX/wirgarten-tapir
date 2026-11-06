from decimal import Decimal

from django.core.exceptions import ValidationError

from tapir.associations.models import AssociationDepositAccount
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_association


class AssociationDepositPolicy:
    @classmethod
    def can_member_increase(
        cls, account: AssociationDepositAccount | None, cache: dict
    ) -> bool:
        settings = cls.get_settings(cache)
        return bool(
            settings["enabled"]
            and settings["allow_member_increase"]
            and account is not None
            and account.agreed_amount is not None
            and account.agreed_amount > 0
            and not account.is_individual_agreement
            and account.instalment_count == 1
        )

    @staticmethod
    def is_enabled(cache: dict) -> bool:
        return legal_status_is_association(cache=cache) and get_parameter_value(
            ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, cache=cache
        )

    @classmethod
    def get_settings(cls, cache: dict) -> dict:
        return {
            "enabled": cls.is_enabled(cache),
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
                ParameterKeys.ASSOCIATION_DEPOSIT_SUPPORTING_MEMBERS_REQUIRED,
                cache=cache,
            ),
            "allow_larger_signup": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_LARGER_SIGNUP, cache=cache
            ),
            "allow_member_increase": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_ALLOW_MEMBER_INCREASE, cache=cache
            ),
        }

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
