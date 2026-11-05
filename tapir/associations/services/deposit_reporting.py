from decimal import Decimal
import locale

from django.db.models import (
    Case,
    DecimalField,
    F,
    OuterRef,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Greatest

from tapir.associations.models import AssociationDepositBooking
from tapir.associations.services.deposit_configuration import DepositConfiguration
from tapir.wirgarten.models import Member, Payment
from tapir.wirgarten.utils import get_today


class DepositReporting:
    @classmethod
    def annotate_members(cls, queryset, cache: dict, reference_date=None):
        date = reference_date or get_today(cache)
        money = DecimalField(max_digits=14, decimal_places=2)
        zero = Value(Decimal(0), output_field=money)

        def total(query, field="amount"):
            return Coalesce(
                Subquery(
                    query.order_by()
                    .values(
                        "association_deposit__member_id"
                        if query.model == Payment
                        else "deposit__member_id"
                    )
                    .annotate(total=Sum(field))
                    .values("total"),
                    output_field=money,
                ),
                zero,
            )

        payments = Payment.objects.filter(association_deposit__member_id=OuterRef("pk"))
        bookings = AssociationDepositBooking.objects.filter(
            deposit__member_id=OuterRef("pk"), date__lte=date
        )
        queryset = queryset.annotate(
            deposit_received=total(
                payments.filter(status=Payment.PaymentStatus.PAID, due_date__lte=date)
            )
            + total(bookings.filter(kind__in=["receipt", "import"]))
            - total(bookings.filter(kind="reversal")),
            deposit_refunded=total(bookings.filter(kind="refund")),
            deposit_pending=total(
                payments.filter(status=Payment.PaymentStatus.DUE, transaction=None)
            ),
            deposit_agreed=F("associationdeposit__agreed_amount"),
            deposit_hardship=F("associationdeposit__hardship_pending"),
            deposit_exception=F("associationdeposit__exception_authorized"),
            deposit_end=F("associationdeposit__cancellation_date"),
        ).annotate(deposit_balance=F("deposit_received") - F("deposit_refunded"))
        return queryset.annotate(
            deposit_refundable=Greatest(
                zero,
                Case(
                    When(deposit_end__lte=date, then=F("deposit_balance")),
                    When(deposit_agreed__isnull=True, then=zero),
                    default=F("deposit_balance") - Coalesce(F("deposit_agreed"), zero),
                    output_field=money,
                ),
            )
        )

    @staticmethod
    def status(member):
        if member.deposit_end:
            return "Gekündigt; Rückzahlung prüfen"
        if member.deposit_agreed is None:
            return (
                "Individuelle Vereinbarung offen"
                if member.deposit_hardship is not None
                else "Keine Einlage vereinbart"
            )
        if member.deposit_agreed == 0 and member.deposit_exception:
            return "Befreiung vereinbart – abgeschlossen"
        if member.deposit_exception:
            return "Individuelle Vereinbarung dokumentiert"
        return "Einlage vereinbart"

    @classmethod
    def filter_members(cls, queryset, value, cache: dict):
        queryset = cls.annotate_members(queryset, cache)
        if value == "pending":
            return queryset.filter(
                deposit_end__isnull=True,
                associationdeposit__isnull=False,
                deposit_agreed__isnull=True,
            )
        if value == "below_minimum":
            return queryset.filter(
                deposit_balance__lt=DepositConfiguration.get(cache)["minimum"]
            )
        if value == "instalments":
            return queryset.filter(deposit_pending__gt=0)
        if value == "exempt":
            return queryset.filter(deposit_agreed=0, deposit_exception=True)
        if value == "reduced":
            return queryset.filter(
                deposit_agreed__gt=0,
                deposit_agreed__lt=DepositConfiguration.get(cache)["minimum"],
                deposit_exception=True,
            )
        return queryset

    @classmethod
    def refundable_members(cls, reference_datetime):
        return (
            cls.annotate_members(Member.objects.all(), {}, reference_datetime.date())
            .filter(
                deposit_end__lte=reference_datetime.date(), deposit_refundable__gt=0
            )
            .order_by("deposit_end", "member_no")
        )

    @classmethod
    def export_value(cls, member, reference_datetime, cache: dict, attribute):
        key = ("deposit_export_members", reference_datetime.date())
        if key not in cache:
            cache[key] = {
                m.pk: m
                for m in cls.annotate_members(
                    Member.objects.all(), cache, reference_datetime.date()
                )
            }
        annotated = cache[key][member.pk]
        value = (
            cls.status(annotated)
            if attribute == "status"
            else getattr(annotated, attribute)
        )
        return (
            locale.format_string("%.2f", value) if isinstance(value, Decimal) else value
        )

    @classmethod
    def dashboard(cls, cache: dict):
        members = cls.annotate_members(
            Member.objects.filter(associationdeposit__isnull=False), cache
        )
        cohorts = {}
        for member in members:
            if member.deposit_end and member.deposit_balance > 0:
                year = member.deposit_end.year
                cohorts[year] = cohorts.get(year, Decimal(0)) + member.deposit_balance
        return {
            "total": sum((m.deposit_balance for m in members), Decimal(0)),
            "pending_cases": sum(
                m.deposit_agreed is None and m.deposit_end is None for m in members
            ),
            "cohorts": sorted(cohorts.items()),
        }
