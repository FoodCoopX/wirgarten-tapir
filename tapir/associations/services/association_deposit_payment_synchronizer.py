import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from tapir.accounts.models import TapirUser
from tapir.associations.models import (
    AssociationDepositAccount,
    AssociationMembership,
    AssociationDepositPaymentCreatedLogEntry,
)
from tapir.associations.services.association_deposit_instalment_calculator import (
    AssociationDepositInstalmentCalculator,
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
            association_deposit_account__agreed_amount__gt=0,
        )
        members = list(
            Member.objects.select_for_update(no_key=True)
            .filter(pk__in=due.values("association_deposit_account__member_id"))
            .order_by("pk")
        )
        membership_history = AssociationMembership.objects.filter(member__in=members)
        eligible_members = set(
            membership_history.filter(start_date__lte=collection_date)
            .filter(Q(end_date=None) | Q(end_date__gte=collection_date))
            .values_list("member_id", flat=True)
        )
        members = [member for member in members if member.pk in eligible_members]
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

    @classmethod
    @transaction.atomic
    def replace_unexported_payment_plan(
        cls, member: Member, actor: TapirUser, cache: dict
    ):
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        Payment.objects.filter(
            association_deposit_account__member=member,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
        ).delete()
        return cls._synchronize_pending_payment(member, actor, cache, create=True)

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
            ).order_by("due_date", "instalment_number", "pk")
        )
        pending = pending_payments[0] if pending_payments else None
        if not create and pending is None:
            return None
        account = AssociationDepositPaymentSynchronizer._get_payment_account(
            member, pending_payments, cache
        )
        remaining = (
            AssociationDepositRemainingAmountCalculator.get_remaining_deposit_amount(
                member=member, cache=cache
            )
        )
        if remaining == 0:
            for payment in pending_payments:
                payment.delete()
            return None
        if pending:
            return AssociationDepositPaymentSynchronizer._update_open_payment_plan(
                account, pending_payments, remaining, cache
            )

        if not member.sepa_consent or member.sepa_consent > get_now(cache=cache):
            raise ValidationError(
                "Für den Einzug ist eine gültige SEPA-Zustimmung erforderlich."
            )
        cache.pop(MandateReferenceProvider.CACHE_KEY, None)
        mandate = MandateReferenceProvider.get_or_create_mandate_reference(
            member=member, cache=cache
        )
        earliest = max(
            account.effective_from, get_today(cache=cache), mandate.start_ts.date()
        )
        memberships = (
            AssociationMembership.objects.filter(member=member)
            .filter(Q(end_date=None) | Q(end_date__gte=earliest))
            .order_by("start_date")
        )
        first_due = None
        for membership in memberships:
            candidate = PaymentDueDateCalculator.get_first_due_date_on_or_after(
                max(earliest, membership.start_date), cache
            )
            if membership.end_date is None or candidate <= membership.end_date:
                first_due = candidate
                break
        if first_due is None:
            raise ValidationError(
                "Für den Einzug ist eine gültige Vereinsmitgliedschaft erforderlich."
            )
        schedule = AssociationDepositInstalmentCalculator.build_payment_schedule(
            remaining,
            account.instalment_count,
            first_due,
            cache,
        )
        payments = [
            Payment.objects.create(
                association_deposit_account=account,
                mandate_ref=mandate,
                type=PAYMENT_TYPE_ASSOCIATION_DEPOSIT,
                status=Payment.PaymentStatus.DUE,
                **rate
            )
            for rate in schedule
        ]
        for payment in payments:
            AssociationDepositPaymentCreatedLogEntry().populate(
                model=payment, actor=actor, user=member
            ).save()
        return payments[0]

    @staticmethod
    def _get_payment_account(
        member: Member, pending_payments: list[Payment], cache: dict
    ):
        if not legal_status_is_association(cache=cache):
            raise ValidationError("Vereinseinlagen sind nur für Vereine vorgesehen.")
        account = AssociationDepositAccount.objects.filter(member=member).first()
        if account is None or account.agreed_amount is None:
            raise ValidationError("Zuerst muss eine Einlagenvereinbarung vorliegen.")
        if account.instalment_count == 1 and len(pending_payments) > 1:
            raise ValidationError(
                "Es bestehen mehrere offene Zahlungen ohne Ratenvereinbarung."
            )

        return account

    @staticmethod
    def _update_open_payment_plan(
        account, pending_payments: list[Payment], remaining, cache: dict
    ):
        pending = pending_payments[0]
        if account.instalment_count == 1 and len(pending_payments) == 1:
            if pending.amount != remaining:
                pending.amount = remaining
                pending.save(update_fields=["amount", "updated_at"])
            return pending
        reduction = sum(payment.amount for payment in pending_payments) - remaining
        if reduction < 0:
            raise ValidationError(
                "Der offene Ratenplan muss ausdrücklich neu vereinbart werden."
            )
        for payment in pending_payments:
            applied = min(payment.amount, reduction)
            reduction -= applied
            if applied:
                payment.amount -= applied
                if payment.amount == 0:
                    payment.delete()
                else:
                    payment.save(update_fields=["amount", "updated_at"])
        return next((payment for payment in pending_payments if payment.pk), None)
