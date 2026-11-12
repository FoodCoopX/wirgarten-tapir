from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum

from tapir.associations.models import AssociationMembership
from tapir.associations.services.association_deposit_amount_validator import (
    AssociationDepositAmountValidator,
)
from tapir.associations.services.association_deposit_payment_creator import (
    AssociationDepositPaymentCreator,
)
from tapir.associations.services.association_deposit_policy import (
    AssociationDepositPolicy,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.utils import get_today, legal_status_is_association


class AssociationDepositMemberService:
    @staticmethod
    def _get_membership(member, cache: dict):
        today = get_today(cache=cache)
        return (
            AssociationMembership.objects.filter(member=member, deposits__isnull=False)
            .filter(Q(end_date=None) | Q(end_date__gte=today))
            .order_by("-start_date", "-pk")
            .first()
        )

    @staticmethod
    def _get_amount(membership) -> Decimal:
        if membership is None:
            return Decimal("0")
        return membership.deposits.aggregate(
            amount=Sum("payment__amount", default=Decimal("0"))
        )["amount"]

    @classmethod
    def get_details(cls, member, cache: dict) -> dict:
        settings = AssociationDepositPolicy.get_settings(cache)
        if not legal_status_is_association(cache=cache):
            return {
                "visible": False,
                "name": settings["name"],
                "amount": 0,
                "agreement_requested": False,
                "can_increase": False,
                "minimum": settings["minimum"],
                "increment": settings["increment"],
            }
        membership = cls._get_membership(member, cache)
        amount = cls._get_amount(membership)
        return {
            "visible": settings["enabled"] or membership is not None,
            "name": settings["name"],
            "amount": amount,
            "agreement_requested": bool(
                membership and membership.deposits.filter(payment=None).exists()
            ),
            "can_increase": bool(
                amount and settings["enabled"] and settings["allow_member_increase"]
            ),
            "minimum": settings["minimum"],
            "increment": settings["increment"],
        }

    @classmethod
    @transaction.atomic
    def increase(
        cls, member, total_amount: Decimal, previous_amount: Decimal, actor, cache: dict
    ):
        Member.objects.select_for_update(no_key=True).get(pk=member.pk)
        settings = AssociationDepositPolicy.get_settings(cache)
        if not settings["enabled"] or not settings["allow_member_increase"]:
            raise ValidationError("Einlagenerhöhungen sind nicht aktiviert.")
        membership = cls._get_membership(member, cache)
        current = cls._get_amount(membership)
        if current <= 0 or total_amount < current:
            raise ValidationError(
                "Eine bestehende Einlage kann hier nur erhöht werden."
            )
        if total_amount == current:
            return
        if current != previous_amount:
            raise ValidationError(
                "Die Einlage hat sich geändert. Bitte lade die Seite neu."
            )
        AssociationDepositAmountValidator.validate_regular_deposit_amount(
            total_amount, cache
        )
        AssociationDepositPaymentCreator.create_agreed_debit(
            membership, total_amount - current, actor, cache
        )
