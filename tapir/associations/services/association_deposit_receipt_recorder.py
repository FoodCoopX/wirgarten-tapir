import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum

from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositReceipt,
    AssociationDepositReceiptCreatedLogEntry,
)
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_payment_synchronizer import (
    AssociationDepositPaymentSynchronizer,
)
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import get_today, legal_status_is_association


class AssociationDepositReceiptRecorder:
    @classmethod
    @transaction.atomic
    def record_received_deposit(
        cls,
        member: Member,
        amount: Decimal,
        received_on: datetime.date,
        reference: str,
        note: str,
        actor: TapirUser | None,
        cache: dict,
        expected_committed_amount: Decimal | None = None,
    ) -> AssociationDepositReceipt:
        if not legal_status_is_association(cache=cache):
            raise ValidationError("Vereinseinlagen sind nur für Vereine vorgesehen.")
        AssociationDepositAmountValidator.validate_positive_amount(amount)
        if received_on > get_today(cache=cache):
            raise ValidationError(
                "Ein Zahlungseingang darf nicht in der Zukunft liegen."
            )
        reference, note = reference.strip(), note.strip()
        if not reference or not note:
            raise ValidationError(
                "Bitte eine Buchungsreferenz und einen Belegtext angeben."
            )
        MaxLengthValidator(100)(reference)

        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        AssociationDepositMembershipCoverage.invalidate_member(member, cache)
        existing = (
            AssociationDepositReceipt.objects.select_related("account")
            .filter(reference=reference)
            .first()
        )
        if existing:
            return cls._validate_repeated_receipt(
                existing, member, amount, received_on, note
            )

        if expected_committed_amount is not None:
            totals = (
                Payment.objects.filter(association_deposit_account__member=member)
                .filter(
                    Q(transaction__isnull=False) | Q(status=Payment.PaymentStatus.PAID)
                )
                .aggregate(total=Sum("amount"))
            )
            committed = totals["total"] or Decimal("0")
            if committed != expected_committed_amount:
                raise ValidationError(
                    "Seit dem Öffnen wurden weitere Zahlungen verbucht oder exportiert. Bitte den Fall neu laden und den Zahlungseingang erneut bestätigen."
                )

        account, _ = AssociationDepositAccount.objects.get_or_create(member=member)
        try:
            with transaction.atomic():
                receipt = AssociationDepositReceipt.objects.create(
                    account=account,
                    reference=reference,
                    amount=amount,
                    received_on=received_on,
                    note=note,
                )
        except IntegrityError:
            existing = (
                AssociationDepositReceipt.objects.select_related("account")
                .filter(reference=reference)
                .first()
            )
            if existing is None:
                raise
            return cls._validate_repeated_receipt(
                existing, member, amount, received_on, note
            )

        AssociationDepositReceiptCreatedLogEntry().populate(
            model=receipt, actor=actor, user=member
        ).save()
        AssociationDepositPaymentSynchronizer.update_existing_deposit_payment(
            member=member, cache=cache
        )
        return receipt

    @staticmethod
    def _validate_repeated_receipt(
        receipt: AssociationDepositReceipt,
        member: Member,
        amount: Decimal,
        received_on: datetime.date,
        note: str,
    ) -> AssociationDepositReceipt:
        if (
            receipt.account.member_id != member.pk
            or receipt.amount != amount
            or receipt.received_on != received_on
            or receipt.note != note
        ):
            raise ValidationError(
                "Diese Buchungsreferenz wurde bereits mit abweichenden Daten verwendet."
            )
        return receipt
