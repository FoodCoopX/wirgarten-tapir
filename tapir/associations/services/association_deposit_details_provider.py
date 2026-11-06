from decimal import Decimal

from django.db.models import Q

from tapir.associations.services.association_deposit_membership_coverage import (
    AssociationDepositMembershipCoverage,
)
from tapir.associations.models import AssociationDepositAccount, AssociationMembership
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.associations.services.association_deposit_balance_calculator import (
    AssociationDepositBalanceCalculator,
)
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import get_today


class AssociationDepositDetailsProvider:
    @staticmethod
    def get_deposit_details(member: Member, cache: dict) -> dict:
        account = (
            AssociationDepositAccount.objects.select_related("member")
            .filter(member=member)
            .first()
        )
        balance = AssociationDepositBalanceCalculator.get_balance(member, cache)
        has_membership = (
            AssociationMembership.objects.filter(member=member)
            .filter(Q(end_date=None) | Q(end_date__gte=get_today(cache)))
            .exists()
        )
        payments = (
            list(
                account.payments.order_by("due_date", "pk").values(
                    "id",
                    "amount",
                    "due_date",
                    "instalment_number",
                    "status",
                    "transaction_id",
                )
            )
            if account
            else []
        )
        return AssociationDepositDetailsProvider.build_details(
            account, balance, payments, has_membership, cache
        )

    @staticmethod
    def build_details(
        account, balance: dict, payments: list, has_membership: bool, cache: dict
    ) -> dict:
        settings = AssociationDepositPolicy.get_settings(cache)
        agreed = account.agreed_amount if account else None
        pending = sum(
            (
                payment["amount"]
                for payment in payments
                if payment["transaction_id"] is None
                and payment["status"] == Payment.PaymentStatus.DUE
            ),
            Decimal("0"),
        )
        state = AssociationDepositDetailsProvider._get_account_state(
            account, agreed, cache
        )
        stopped = AssociationDepositDetailsProvider._mark_stopped_payments(
            account, payments, cache
        )
        pending -= stopped
        if account and AssociationDepositMembershipCoverage.get_collection_cutoff(
            account, cache
        ):
            state = (
                "agreement_required"
                if AssociationDepositMembershipCoverage.requires_new_agreement(
                    account, cache
                )
                else "collection_stopped"
            )
        if (
            account
            and account.refund_requires_agreement
            and agreed not in (None, Decimal("0"))
        ):
            state = "agreement_required"
        return {
            "settings": settings,
            "visible": settings["enabled"] or account is not None,
            "agreed_amount": agreed,
            **balance,
            "refund_requires_agreement": bool(
                account and account.refund_requires_agreement
            ),
            "state": state,
            "payments": payments,
            "stopped_amount": stopped,
            "overpayment_credit": (
                max(Decimal("0"), balance["retained_amount"] - agreed)
                if agreed is not None
                else None
            ),
            "pending_amount": pending,
            "can_increase": AssociationDepositPolicy.can_member_increase(account, cache)
            and has_membership,
        }

    @staticmethod
    def _get_account_state(account, agreed, cache: dict):
        state = "not_agreed"
        if agreed is not None:
            if agreed == 0:
                state = "waived"
            elif account.is_individual_agreement:
                state = "individual"
            else:
                state = "regular"
        elif account and account.hardship_requested_at is not None:
            state = "pending"
        return state

    @staticmethod
    def _mark_stopped_payments(account, payments: list, cache: dict):
        stopped = Decimal("0")
        for payment in payments:
            if (
                payment["transaction_id"] is None
                and payment["status"] == Payment.PaymentStatus.DUE
                and not AssociationDepositMembershipCoverage.can_collect_on(
                    account,
                    payment["due_date"],
                    max(get_today(cache), payment["due_date"]),
                    cache,
                )
            ):
                payment["status"] = "STOPPED"
                stopped += payment["amount"]
        return stopped
