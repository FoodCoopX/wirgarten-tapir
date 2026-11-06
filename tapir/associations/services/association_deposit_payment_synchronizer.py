import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
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
from tapir.associations.services.association_deposit_due_date_provider import (
    AssociationDepositDueDateProvider,
)
from tapir.payments.config import PAYMENT_TYPE_ASSOCIATION_DEPOSIT
from tapir.payments.services.mandate_reference_provider import MandateReferenceProvider
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import legal_status_is_association, get_today


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
        candidates = list(
            due.filter(
                association_deposit_account__member_id__in=[
                    member.pk for member in members
                ]
            )
            .select_related(
                "mandate_ref__member", "association_deposit_account__member"
            )
            .order_by("pk")
        )

        return [
            payment
            for payment in candidates
            if AssociationDepositMembershipCoverage.can_collect_on(
                payment.association_deposit_account,
                payment.due_date,
                collection_date,
                cache,
            )
        ]

    @classmethod
    def create_regular_deposit_payment(
        cls,
        member: Member,
        actor: TapirUser | None,
        cache: dict,
        allow_standard_increase: bool = False,
    ) -> Payment | None:
        return cls._synchronize_pending_payment(
            member,
            actor,
            cache,
            create=True,
            allow_standard_increase=allow_standard_increase,
        )

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
        AssociationDepositMembershipCoverage.invalidate_member(member, cache)
        Payment.objects.filter(
            association_deposit_account__member=member,
            transaction=None,
            status=Payment.PaymentStatus.DUE,
        ).delete()
        return cls._synchronize_pending_payment(member, actor, cache, create=True)

    @staticmethod
    @transaction.atomic
    def _synchronize_pending_payment(
        member: Member,
        actor: TapirUser | None,
        cache: dict,
        create: bool,
        allow_standard_increase: bool = False,
    ) -> Payment | None:
        member = Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        AssociationDepositMembershipCoverage.invalidate_member(member, cache)
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
            member, pending_payments, create, cache
        )
        if account is None:
            return None
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
                account, pending_payments, remaining, allow_standard_increase, cache
            )

        first_due = AssociationDepositDueDateProvider.get_first_due_date(
            member, account, cache
        )
        schedule = AssociationDepositInstalmentCalculator.build_payment_schedule(
            remaining,
            account.instalment_count,
            first_due,
            cache,
        )
        return AssociationDepositPaymentSynchronizer._create_payment_plan(
            member, account, schedule, actor, cache
        )

    @staticmethod
    @transaction.atomic
    def create_imported_payment_plan(member, account, rates: list[dict], cache: dict):
        if not rates:
            return None
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        if account.member_id != member.pk or account.payments.exists():
            raise ValidationError(
                "Ein importierter Ratenplan darf bestehende Zahlungen nicht überschreiben."
            )
        schedule = [
            dict(
                **rate,
                instalment_number=(
                    account.instalment_count - len(rates) + index + 1
                    if account.instalment_count > 1
                    else None
                )
            )
            for index, rate in enumerate(rates)
        ]
        return AssociationDepositPaymentSynchronizer._create_payment_plan(
            member, account, schedule, None, cache
        )

    @staticmethod
    def _create_payment_plan(member, account, schedule: list[dict], actor, cache: dict):
        mandate = MandateReferenceProvider.get_or_create_mandate_reference(
            member, cache
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
        member: Member, pending_payments: list[Payment], create: bool, cache: dict
    ):
        if not legal_status_is_association(cache=cache):
            raise ValidationError("Vereinseinlagen sind nur für Vereine vorgesehen.")
        account = AssociationDepositAccount.objects.filter(member=member).first()
        if account is None or account.agreed_amount is None:
            raise ValidationError("Zuerst muss eine Einlagenvereinbarung vorliegen.")
        if account.refund_requires_agreement:
            return None
        cutoff = AssociationDepositMembershipCoverage.get_collection_cutoff(
            account, cache
        )
        if (
            create
            and cutoff
            and (
                cutoff <= get_today(cache)
                or AssociationDepositMembershipCoverage.requires_new_agreement(
                    account, cache
                )
            )
        ):
            return None
        if account.instalment_count == 1 and len(pending_payments) > 1:
            raise ValidationError(
                "Es bestehen mehrere offene Zahlungen ohne Ratenvereinbarung."
            )

        return account

    @staticmethod
    def _update_open_payment_plan(
        account,
        pending_payments: list[Payment],
        remaining,
        allow_standard_increase: bool,
        cache: dict,
    ):
        schedule = AssociationDepositInstalmentCalculator.adjust_open_payments(
            remaining,
            account.instalment_count,
            pending_payments,
            allow_standard_increase,
        )
        amounts = {rate["id"]: rate["amount"] for rate in schedule}
        for payment in pending_payments:
            if payment.pk not in amounts:
                payment.delete()
            elif payment.amount != amounts[payment.pk]:
                payment.amount = amounts[payment.pk]
                payment.save(update_fields=["amount", "updated_at"])
        return next((payment for payment in pending_payments if payment.pk), None)
