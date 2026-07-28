from decimal import Decimal

from django.db.models import (
    QuerySet,
    OuterRef,
    Subquery,
    F,
    Sum,
    DecimalField,
    DateField,
)
from django.db.models.expressions import Case, When
from django.db.models.functions import Coalesce

from tapir.wirgarten.models import Member, CoopShareTransaction


class CooperativeEntryDateAnnotater:
    ANNOTATION_COOP_ENTRY_DATE = "coop_entry_date"
    ANNOTATION_COOP_EXIT_DATE = "coop_exit_date"

    @classmethod
    def annotate_member_queryset_with_coop_entry_date(cls, queryset: QuerySet[Member]):
        earliest_coop_share_transaction = (
            CoopShareTransaction.objects.filter(member_id=OuterRef("id"))
            .order_by("valid_at")
            .values("valid_at")[:1]
        )

        return queryset.annotate(
            **{
                cls.ANNOTATION_COOP_ENTRY_DATE: Subquery(
                    earliest_coop_share_transaction
                )
            }
        )

    @classmethod
    def annotate_member_queryset_with_coop_exit_date(cls, queryset: QuerySet[Member]):
        date_of_latest_coop_share_transaction = (
            CoopShareTransaction.objects.filter(member_id=OuterRef("id"))
            .order_by("-valid_at")
            .values("valid_at")[:1]
        )

        queryset = queryset.annotate(
            date_of_latest_coop_share_transaction=Subquery(
                date_of_latest_coop_share_transaction
            )
        )

        queryset = queryset.annotate(
            coop_shares_total_value=Coalesce(
                Subquery(
                    CoopShareTransaction.objects.filter(
                        member_id=OuterRef("id"),
                        valid_at__lte=OuterRef("date_of_latest_coop_share_transaction"),
                    )
                    .values("member_id")
                    .annotate(total_value=Sum(F("quantity") * F("share_price")))
                    .values("total_value"),
                    output_field=DecimalField(),
                ),
                Decimal(0.0),
            )
        )

        return queryset.annotate(
            **{
                cls.ANNOTATION_COOP_EXIT_DATE: Case(
                    When(
                        coop_shares_total_value__lte=0,
                        then=F("date_of_latest_coop_share_transaction"),
                    ),
                    default=None,
                    output_field=DateField(null=True),
                )
            }
        )
