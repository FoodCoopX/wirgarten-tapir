import datetime

from django.db.models import QuerySet

from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.wirgarten.service.member import (
    annotate_member_queryset_with_coop_shares_total_value,
    annotate_member_queryset_with_monthly_payment,
)


class MemberSegmentProvider:
    @classmethod
    def get_member_segments(cls):
        return [
            ExportSegment(
                id="members.all",
                display_name="TEST_SEGMENT - Alle Mitglieder",
                description="TEST_SEGMENT - Alle Mitglieder, "
                "egal ob mit Abo oder nicht, solange sie Genossenschaftsanteile haben",
                get_queryset=cls.get_queryset_all_members_with_shares,
                get_available_columns=MemberColumnProvider.get_member_columns,
            ),
            ExportSegment(
                id="members.with_subscription",
                display_name="TEST_SEGMENT - Mitglieder mit Abo",
                description="TEST_SEGMENT - Alle Menschen die ein aktives Abo haben, "
                "egal ob sie Mitglied sind oder nicht ",
                get_queryset=cls.get_queryset_all_members_with_subscription,
                get_available_columns=MemberColumnProvider.get_member_columns,
            ),
        ]

    @classmethod
    def get_queryset_all_members_with_shares(cls, _) -> QuerySet:
        from tapir.wirgarten.models import Member

        members = annotate_member_queryset_with_coop_shares_total_value(
            Member.objects.all()
        )
        return members.filter(coop_shares_total_value__gt=0)

    @classmethod
    def get_queryset_all_members_with_subscription(
        cls, reference_datetime: datetime.datetime
    ) -> QuerySet:
        from tapir.wirgarten.models import Member

        members = annotate_member_queryset_with_monthly_payment(
            Member.objects.all(), reference_datetime.date()
        )
        return members.filter(monthly_payment__gt=0)
