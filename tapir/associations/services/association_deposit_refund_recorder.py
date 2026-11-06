import datetime
import json
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import MaxLengthValidator
from django.db import IntegrityError, transaction

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositRefund,
    AssociationDepositRefundCreatedLogEntry,
)
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_balance_calculator import (
    AssociationDepositBalanceCalculator,
)
from tapir.log.util import freeze_for_log
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today, legal_status_is_association


class AssociationDepositRefundRecorder:
    @classmethod
    @transaction.atomic
    def record_external_refund(
        cls,
        member: Member,
        amount: Decimal,
        refunded_on: datetime.date,
        reference: str,
        note: str,
        bank_settlement_confirmed: bool,
        expected_revision: int,
        expected_committed_amount: Decimal,
        actor: TapirUser,
        cache: dict,
    ) -> AssociationDepositRefund:
        if actor is None or not actor.has_perm(Permission.Coop.MANAGE):
            raise PermissionDenied
        if not legal_status_is_association(cache=cache):
            raise ValidationError("Vereinseinlagen sind nur für Vereine vorgesehen.")
        AssociationDepositAmountValidator.validate_positive_amount(amount)
        if refunded_on > get_today(cache) or bank_settlement_confirmed is not True:
            raise ValidationError(
                "Bitte eine bereits ausgeführte und bankseitig geprüfte Rückzahlung bestätigen."
            )
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValidationError("Bitte eine gültige Vereinbarungsrevision angeben.")
        reference, note = reference.strip(), note.strip()
        if not reference or not note:
            raise ValidationError("Bitte Bank-Buchungsreferenz und Beleg angeben.")
        MaxLengthValidator(100)(reference)
        MaxLengthValidator(3000)(note)
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        existing = (
            AssociationDepositRefund.objects.select_related("account")
            .filter(reference=reference)
            .first()
        )
        if existing:
            return cls._validate_replay(existing, member, amount, refunded_on, note)
        account = AssociationDepositAccount.objects.filter(member=member).first()
        if account is None:
            raise ValidationError("Es besteht noch kein Einlagenkonto.")
        cls._validate_available_balance(
            member, account, amount, expected_revision, expected_committed_amount, cache
        )
        try:
            with transaction.atomic():
                refund = AssociationDepositRefund.objects.create(
                    account=account,
                    amount=amount,
                    refunded_on=refunded_on,
                    reference=reference,
                    note=note,
                )
        except IntegrityError:
            existing = (
                AssociationDepositRefund.objects.select_related("account")
                .filter(reference=reference)
                .first()
            )
            if existing is None:
                raise
            return cls._validate_replay(existing, member, amount, refunded_on, note)
        previous = freeze_for_log(account)
        account.refund_requires_agreement = True
        account.agreement_revision += 1
        account.save(
            update_fields=[
                "refund_requires_agreement",
                "agreement_revision",
                "updated_at",
            ]
        )
        values = freeze_for_log(refund)
        values.update(
            bank_settlement_confirmed="True",
            previous_account=json.dumps(previous, sort_keys=True),
        )
        AssociationDepositRefundCreatedLogEntry().populate(
            frozen=values, actor=actor, user=member
        ).save()
        return refund

    @staticmethod
    def _validate_replay(refund, member, amount, refunded_on, note):
        if (
            refund.account.member_id,
            refund.amount,
            refund.refunded_on,
            refund.note,
        ) != (member.pk, amount, refunded_on, note):
            raise ValidationError(
                "Diese Rückzahlungsreferenz wurde bereits mit anderen Daten verwendet."
            )
        return refund

    @staticmethod
    def _validate_available_balance(
        member,
        account,
        amount,
        expected_revision,
        expected_committed_amount,
        cache: dict,
    ):
        balance = AssociationDepositBalanceCalculator.get_balance(member, cache)
        if (
            account.agreement_revision != expected_revision
            or balance["committed_amount"] != expected_committed_amount
        ):
            raise ValidationError(
                "Vereinbarung oder verbuchter Zahlungsstand wurden inzwischen geändert. Bitte neu laden und die Rückzahlung erneut prüfen."
            )
        if amount > balance["retained_amount"]:
            raise ValidationError(
                "Die Rückzahlung überschreitet den erfassten Buchungsrest."
            )
