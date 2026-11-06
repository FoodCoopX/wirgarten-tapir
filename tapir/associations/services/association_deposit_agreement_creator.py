import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositAgreementCreatedLogEntry,
)
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today, legal_status_is_association


class AssociationDepositAgreementCreator:
    @staticmethod
    @transaction.atomic
    def create_regular_agreement(
        member: Member,
        amount: Decimal,
        effective_from: datetime.date,
        actor: TapirUser | None,
        cache: dict,
        instalment_count: int = 1,
    ) -> AssociationDepositAccount:
        if not legal_status_is_association(cache=cache):
            raise ValidationError("Vereinseinlagen sind nur für Vereine vorgesehen.")
        AssociationDepositAmountValidator.validate_positive_amount(amount)
        AssociationDepositInstalmentCalculator.validate_instalment_count(
            instalment_count
        )
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        account, _ = AssociationDepositAccount.objects.get_or_create(member=member)
        if account.refund_requires_agreement:
            raise ValidationError(
                "Nach einer Rückzahlung ist eine neue dokumentierte Verwaltungsvereinbarung erforderlich."
            )
        if account.hardship_requested_at is not None and account.agreed_amount is None:
            raise ValidationError(
                "Zuerst muss eine dokumentierte individuelle Vereinbarung vorliegen."
            )
        if account.agreed_amount is not None:
            if (
                account.agreed_amount != amount
                or account.effective_from != effective_from
                or account.instalment_count != instalment_count
                or account.is_individual_agreement
            ):
                raise ValidationError(
                    "Es besteht bereits eine abweichende Einlagenvereinbarung."
                )
            return account

        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            amount, cache=cache
        )
        if instalment_count != 1 and (
            not get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENTS_ENABLED, cache=cache
            )
            or instalment_count
            != get_parameter_value(
                ParameterKeys.ASSOCIATION_DEPOSIT_INSTALMENT_COUNT, cache=cache
            )
        ):
            raise ValidationError("Dieser Standard-Ratenplan ist nicht freigegeben.")
        if effective_from < get_today(cache=cache):
            raise ValidationError(
                "Eine neue reguläre Vereinbarung darf nicht rückdatiert werden."
            )

        account.agreement_revision += 1
        account.agreed_amount = amount
        account.effective_from = effective_from
        account.instalment_count = instalment_count
        account.is_individual_agreement = False
        account.save(
            update_fields=[
                "agreed_amount",
                "effective_from",
                "instalment_count",
                "is_individual_agreement",
                "agreement_revision",
                "updated_at",
            ]
        )
        AssociationDepositAgreementCreatedLogEntry().populate(
            model=account, actor=actor, user=member
        ).save()
        return account
