import datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationDepositPaymentCreatedLogEntry,
)
from tapir.associations.services.association_deposit_remaining_amount_calculator import (
    AssociationDepositRemainingAmountCalculator,
)
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.payments.services.payment_due_date_calculator import PaymentDueDateCalculator
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import get_now, get_today, legal_status_is_association


class AssociationDepositPaymentSynchronizer:
    @classmethod
    @transaction.atomic
    def prepare_due_payments_for_export(
        cls, collection_date: datetime.date, cache: dict
    ) -> list[Payment]:
        due = Payment.objects.filter(
            association_deposit_account__isnull=False,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
            due_date__lte=collection_date,
        )
        members = list(
            Member.objects.select_for_update(no_key=True)
            .filter(pk__in=due.values("association_deposit_account__member_id"))
            .order_by("pk")
        )
        for member in members:
            cls.update_existing_deposit_payment(member=member, cache=cache)
        return list(
            due.filter(
                association_deposit_account__member_id__in=[
                    member.pk for member in members
                ]
            )
            .select_related("mandate_ref__member", "association_deposit_account")
            .order_by("pk")
        )

    @classmethod
    def create_regular_deposit_payment(
        cls, member: Member, actor: TapirUser | None, cache: dict
    ) -> Payment | None:
        return cls._synchronize_pending_payment(member, actor, cache, create=True)

    @classmethod
    def update_existing_deposit_payment(
        cls, member: Member, cache: dict
    ) -> Payment | None:
        return cls._synchronize_pending_payment(member, None, cache, create=False)

    @staticmethod
    @transaction.atomic
    def _synchronize_pending_payment(
        member: Member, actor: TapirUser | None, cache: dict, create: bool
    ) -> Payment | None:
        member = Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        pending_payments = list(
            Payment.objects.filter(
                association_deposit_account__member=member,
                status=Payment.PaymentStatus.DUE,
                transaction=None,
            ).order_by("pk")[:2]
        )
        if len(pending_payments) > 1:
            raise ValidationError(
                "Für diese Einlage bestehen mehrere offene Zahlungen."
            )
        pending = pending_payments[0] if pending_payments else None
        if not create and pending is None:
            return None
        if not legal_status_is_association(cache=cache):
            raise ValidationError("Vereinseinlagen sind nur für Vereine vorgesehen.")
        account = AssociationDepositAccount.objects.filter(member=member).first()
        if account is None or account.agreed_amount is None:
            raise ValidationError("Zuerst muss eine Einlagenvereinbarung vorliegen.")

        remaining = (
            AssociationDepositRemainingAmountCalculator.get_remaining_deposit_amount(
                member=member, cache=cache
            )
        )
        if remaining == 0:
            if pending:
                pending.delete()
            return None
        if pending:
            if pending.amount != remaining:
                pending.amount = remaining
                pending.save(update_fields=["amount", "updated_at"])
            return pending

        if not member.sepa_consent or member.sepa_consent > get_now(cache=cache):
            raise ValidationError(
                "Für den Einzug ist eine gültige SEPA-Zustimmung erforderlich."
            )
        cache.pop(MandateReferenceProvider.CACHE_KEY, None)
        mandate = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )
        payment = Payment.objects.create(
            association_deposit_account=account,
            amount=remaining,
            type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
            due_date=PaymentDueDateCalculator.get_first_due_date_on_or_after(
                earliest_date=max(
                    account.effective_from,
                    get_today(cache=cache),
                    mandate.start_ts.date(),
                ),
                cache=cache,
            ),
            mandate_ref=mandate,
            status=Payment.PaymentStatus.DUE,
        )
        AssociationDepositPaymentCreatedLogEntry().populate(
            model=payment, actor=actor, user=member
        ).save()
        return payment
