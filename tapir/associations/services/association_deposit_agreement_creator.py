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
    ) -> AssociationDepositAccount:
        if not legal_status_is_association(cache=cache):
            raise ValidationError("Vereinseinlagen sind nur für Vereine vorgesehen.")
        AssociationDepositAmountValidator.validate_positive_amount(amount)
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        account, _ = AssociationDepositAccount.objects.get_or_create(member=member)
        if account.agreed_amount is not None:
            if (
                account.agreed_amount != amount
                or account.effective_from != effective_from
            ):
                raise ValidationError(
                    "Es besteht bereits eine abweichende Einlagenvereinbarung."
                )
            return account

        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            amount, cache=cache
        )
        if effective_from < get_today(cache=cache):
            raise ValidationError(
                "Eine neue reguläre Vereinbarung darf nicht rückdatiert werden."
            )

        account.agreed_amount = amount
        account.effective_from = effective_from
        account.save(update_fields=["agreed_amount", "effective_from", "updated_at"])
        AssociationDepositAgreementCreatedLogEntry().populate(
            model=account, actor=actor, user=member
        ).save()
        return account
