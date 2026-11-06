from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositIncreasedLogEntry,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.associations.services.association_deposit_increase_preview import (
    AssociationDepositIncreasePreview,
)
from tapir.log.util import freeze_for_log
from tapir.wirgarten.models import Member


class AssociationDepositIncreaseRecorder:
    @staticmethod
    @transaction.atomic
    def increase_agreed_deposit(
        member: Member,
        total_amount: Decimal,
        actor: TapirUser,
        cache: dict,
        confirmation: str | None = None,
    ):
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        AssociationDepositMembershipCoverage.invalidate_member(member, cache)
        account = AssociationDepositPolicy.get_increasable_account(member, cache)
        AssociationDepositPolicy.validate_increase_amount(account, total_amount, cache)
        if total_amount == account.agreed_amount:
            return account
        if account.instalment_count != 1 and confirmation is None:
            raise ValidationError(
                "Bitte den neuen Ratenplan zuerst prüfen und bestätigen."
            )
        if confirmation is not None:
            AssociationDepositIncreasePreview.validate_confirmation(
                member, total_amount, confirmation, cache
            )
        old = freeze_for_log(account)
        account.agreement_revision += 1
        account.agreed_amount = total_amount
        account.save(
            update_fields=["agreed_amount", "agreement_revision", "updated_at"]
        )
        AssociationDepositIncreasedLogEntry().populate(
            old_frozen=old, new_model=account, actor=actor, user=member
        ).save()
        AssociationDepositPaymentSynchronizer.create_regular_deposit_payment(
            member, actor, cache, allow_standard_increase=account.instalment_count != 1
        )
        return account
