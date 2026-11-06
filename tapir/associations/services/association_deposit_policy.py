from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q

from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.associations.models import AssociationDepositAccount, AssociationMembership
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_association, get_today
from tapir.wirgarten.models import Member


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
            and AssociationDepositMembershipCoverage.get_collection_cutoff(
                account, cache
            )
            is None
            and not account.refund_requires_agreement
            and not account.is_individual_agreement
            and (account.instalment_count == 1 or settings["instalments_enabled"])
        )

    @classmethod
    def get_increasable_account(
        cls, member: Member, cache: dict
    ) -> AssociationDepositAccount:
        settings = cls.get_settings(cache)
        if not settings["enabled"] or not settings["allow_member_increase"]:
            raise ValidationError(
                "Einlagenerhöhungen im Mitgliederbereich sind nicht aktiviert."
            )
        account = AssociationDepositAccount.objects.filter(member=member).first()
        if account is None or account.agreed_amount is None:
            raise ValidationError("Es besteht noch keine Einlagenvereinbarung.")
        if not cls.can_member_increase(account, cache):
            raise ValidationError(
                "Diese Einlage kann nur durch eine dokumentierte Verwaltungsvereinbarung geändert werden."
            )
        if (
            not AssociationMembership.objects.filter(member=member)
            .filter(Q(end_date=None) | Q(end_date__gte=get_today(cache)))
            .exists()
        ):
            raise ValidationError(
                "Für eine Erhöhung ist eine bestehende Vereinsmitgliedschaft erforderlich."
            )
        return account

    @staticmethod
    def validate_increase_amount(
        account: AssociationDepositAccount, amount: Decimal, cache: dict
    ):
        AssociationDepositAmountValidator.validate_positive_amount(amount)
        if amount < account.agreed_amount:
            raise ValidationError(
                "Die vereinbarte Einlage darf hier nur erhöht werden."
            )
        if amount != account.agreed_amount:
            AssociationDepositAmountValidator.validate_regular_deposit_amount(
                amount, cache
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
            "instalments_enabled": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, cache=cache
            ),
            "instalment_count": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT, cache=cache
            ),
            "hardship_enabled": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, cache=cache
            ),
            "hardship_label": get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_LABEL, cache=cache
            ),
        }

    @classmethod
    def validate_signup_selection(
        cls,
        amount: Decimal | None,
        has_products: bool,
        cache: dict,
        payment_option: str = "once",
        expected_instalments: int | None = None,
    ) -> int | None:
        if payment_option not in ("once", "standard_instalments", "hardship"):
            raise ValidationError("Bitte eine gültige Einlagenauswahl angeben.")
        if payment_option == "hardship":
            if not cls.is_enabled(cache) or not get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, cache=cache
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
        if payment_option == "once":
            return 1
        if (
            not cls.is_enabled(cache)
            or not amount
            or not get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, cache=cache
            )
        ):
            raise ValidationError("Standardraten sind nicht freigegeben.")
        count = get_parameter_value(
            ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT, cache=cache
        )
        AssociationDepositInstalmentCalculator.validate_payment_schedule_amount(
            amount, count
        )
        if expected_instalments != count:
            raise ValidationError(
                "Die Standard-Ratenzahl wurde geändert oder noch nicht bestätigt. Bitte die aktuellen Einstellungen neu laden."
            )
        return count

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
