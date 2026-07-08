from django.db.models import QuerySet, OuterRef, Subquery

from tapir.wirgarten.models import Member, CoopShareTransaction


class CooperativeEntryDateAnnotater:
    ANNOTATION_COOP_ENTRY_DATE = "coop_entry_date"

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
