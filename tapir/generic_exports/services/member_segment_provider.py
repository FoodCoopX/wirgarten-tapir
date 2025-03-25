import datetime

from django.db.models import QuerySet

from tapir.deliveries.models import Joker
from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.wirgarten.service.member import (
    annotate_member_queryset_with_coop_shares_total_value,
    annotate_member_queryset_with_monthly_payment,
)
from tapir.wirgarten.service.products import get_current_growing_period


class MemberSegmentProvider:
    @classmethod
    def get_member_segments(cls):
        return [
            ExportSegment(
                id="members.all",
                display_name="Alle Mitglieder",
                description="Alle Mitglieder, "
                "egal ob mit Abo oder nicht, solange sie Genossenschaftsanteile haben",
                get_queryset=cls.get_queryset_all_members_with_shares,
                get_available_columns=MemberColumnProvider.get_member_columns,
            ),
            ExportSegment(
                id="members.with_subscription",
                display_name="Mitglieder mit Abo",
                description="Alle Menschen die ein aktives Abo haben, "
                "egal ob sie Mitglied sind oder nicht ",
                get_queryset=cls.get_queryset_all_members_with_subscription,
                get_available_columns=MemberColumnProvider.get_member_columns,
            ),
            ExportSegment(
                id="members.with_used_joker",
                display_name="Mitglieder mit Joker",
                description="Alle Mitglieder die in dem angegebenen Jahr mindestens ein Joker eingesetzt haben",
                get_queryset=cls.get_queryset_members_with_joker_used,
                get_available_columns=MemberColumnProvider.get_member_columns,
            ),
        ]

    @classmethod
    def get_queryset_all_members_with_shares(cls, _) -> QuerySet:
        from tapir.wirgarten.models import Member

        members = annotate_member_queryset_with_coop_shares_total_value(
            Member.objects.all()
        )
        return members.filter(coop_shares_total_value__gt=0).order_by("member_no")

    @classmethod
    def get_queryset_all_members_with_subscription(
        cls, reference_datetime: datetime.datetime
    ) -> QuerySet:
        from tapir.wirgarten.models import Member

        members = annotate_member_queryset_with_monthly_payment(
            Member.objects.all(), reference_datetime.date()
        )
        return members.filter(monthly_payment__gt=0).order_by("member_no")

    @classmethod
    def get_queryset_members_with_joker_used(
        cls, reference_datetime: datetime.datetime
    ) -> QuerySet:
        from tapir.wirgarten.models import Member

        growing_period = get_current_growing_period(reference_datetime)
        member_ids = Joker.objects.filter(
            date__gte=growing_period.start_date,
            date__lte=reference_datetime.date(),
        ).values_list("member_id")

        return Member.objects.filter(id__in=member_ids).distinct()
