from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositIncreasedLogEntry,
    AssociationMembership,
)
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.log.util import freeze_for_log
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today


class AssociationDepositIncreaseRecorder:
    @staticmethod
    @transaction.atomic
    def increase_agreed_deposit(
        member: Member, total_amount: Decimal, actor: TapirUser, cache: dict
    ):
        settings = AssociationDepositPolicy.get_settings(cache)
        if not settings["enabled"] or not settings["allow_member_increase"]:
            raise ValidationError(
                "Einlagenerhöhungen im Mitgliederbereich sind nicht aktiviert."
            )
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        account = AssociationDepositAccount.objects.filter(member=member).first()
        if account is None or account.agreed_amount is None:
            raise ValidationError("Es besteht noch keine Einlagenvereinbarung.")
        if (
            not AssociationMembership.objects.filter(member=member)
            .filter(Q(end_date=None) | Q(end_date__gte=get_today(cache)))
            .exists()
        ):
            raise ValidationError(
                "Für eine Erhöhung ist eine bestehende Vereinsmitgliedschaft erforderlich."
            )
        AssociationDepositAmountValidator.validate_positive_amount(total_amount)
        if total_amount == account.agreed_amount:
            return account
        if total_amount < account.agreed_amount:
            raise ValidationError(
                "Die vereinbarte Einlage darf hier nur erhöht werden."
            )
        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            total_amount, cache
        )
        old = freeze_for_log(account)
        account.agreed_amount = total_amount
        account.save(update_fields=["agreed_amount", "updated_at"])
        AssociationDepositIncreasedLogEntry().populate(
            old_frozen=old, new_model=account, actor=actor, user=member
        ).save()
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            member, actor, cache
        )
        return account
