from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositHardshipRequestedLogEntry,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.associations.services.association_deposit_hardship_notifier import (
    AssociationDepositHardshipNotifier,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_now


class AssociationDepositHardshipRequestRecorder:
    @staticmethod
    @transaction.atomic
    def record_request(
        member: Member, actor: TapirUser | None, cache: dict
    ) -> AssociationDepositAccount:
        if not AssociationDepositPolicy.is_enabled(cache):
            raise ValidationError("Vereinseinlagen sind nicht aktiviert.")
        if not get_parameter_value(
            ParameterKeys.ASSOCIATION_DEPOSIT_HARDSHIP_ENABLED, cache=cache
        ):
            raise ValidationError(
                "Anfragen für individuelle Einlagenvereinbarungen sind nicht aktiviert."
            )
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        account, _ = AssociationDepositAccount.objects.get_or_create(member=member)
        if account.agreed_amount is not None:
            raise ValidationError("Es besteht bereits eine Einlagenvereinbarung.")
        if account.payments.filter(
            transaction=None, status=Payment.PaymentStatus.DUE
        ).exists():
            raise ValidationError("Offene Zahlungen müssen zuerst geprüft werden.")
        if account.hardship_requested_at is not None:
            return account
        account.hardship_requested_at = get_now(cache)
        account.agreement_revision += 1
        account.save(
            update_fields=["hardship_requested_at", "agreement_revision", "updated_at"]
        )
        AssociationDepositHardshipRequestedLogEntry().populate(
            model=account, actor=actor, user=member
        ).save()
        AssociationDepositHardshipNotifier.notify_administration(member, cache)
        return account
