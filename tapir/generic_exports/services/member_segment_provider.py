import datetime

from django.db.models import QuerySet

from tapir.deliveries.models import Joker
from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.service.member import (
    annotate_member_queryset_with_coop_shares_total_value,
    annotate_member_queryset_with_monthly_payment,
)
from tapir.wirgarten.utils import get_now, get_today


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
            ExportSegment(
                id="members.with_contract_since_more_than_one_year_but_no_coop_share",
                display_name="Mitglieder die ein Vertrag seit über einem Jahr haben aber noch kein Geno-Anteil",
                description="",
                get_queryset=cls.get_queryset_members_with_contract_since_more_than_one_year_but_no_coop_share,
                get_available_columns=MemberColumnProvider.get_member_columns,
            ),
            ExportSegment(
                id="members.with_cancelled_shares_in_previous_year",
                display_name="Mitglieder mit gekündigte Anteile im Vorjahr",
                description="",
                get_queryset=cls.get_queryset_members_with_cancelled_shares_in_previous_year,
                get_available_columns=MemberColumnProvider.get_member_columns,
            ),
        ]

    @classmethod
    def get_queryset_all_members_with_shares(
        cls, reference_datetime: datetime.datetime
    ) -> QuerySet:
        from tapir.wirgarten.models import Member

        members = annotate_member_queryset_with_coop_shares_total_value(
            Member.objects.all(), reference_date=reference_datetime.date()
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

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=reference_datetime.date(), cache={}
        )
        member_ids = Joker.objects.filter(
            date__gte=growing_period.start_date,
            date__lte=reference_datetime.date(),
        ).values_list("member_id")

        return Member.objects.filter(id__in=member_ids).order_by("member_no").distinct()

    @classmethod
    def get_queryset_members_with_contract_since_more_than_one_year_but_no_coop_share(
        cls, reference_datetime: datetime.datetime | None = None
    ):
        from tapir.wirgarten.models import Member

        cache = {}

        if reference_datetime is None:
            reference_datetime = get_now(cache=cache)

        members = annotate_member_queryset_with_coop_shares_total_value(
            queryset=Member.objects.all(),
            reference_date=reference_datetime.date(),
            cache=cache,
        )

        members_without_share = members.filter(coop_shares_total_value=0)

        today = get_today(cache=cache)
        one_year_ago = today.replace(year=today.year - 1)
        subscriptions_older_than_a_year = Subscription.objects.filter(
            start_date__lt=one_year_ago
        )

        members_without_share_and_with_an_old_subscription = (
            members_without_share.filter(
                id__in=set(
                    subscriptions_older_than_a_year.values_list("member_id", flat=True)
                )
            ).distinct()
        )

        members_with_an_active_subscription = (
            annotate_member_queryset_with_monthly_payment(
                queryset=Member.objects.all(), reference_date=reference_datetime.date()
            ).filter(monthly_payment__gt=0)
        )

        return Member.objects.filter(
            id__in=set(
                members_without_share_and_with_an_old_subscription.values_list(
                    "id", flat=True
                )
            )
        ).filter(
            id__in=set(members_with_an_active_subscription.values_list("id", flat=True))
        )

    @classmethod
    def get_queryset_members_with_cancelled_shares_in_previous_year(
        cls, reference_datetime: datetime.datetime
    ):
        from tapir.wirgarten.models import CoopShareTransaction, Member

        year = reference_datetime.year
        timerange = (
            datetime.datetime(year - 1, 1, 1),
            datetime.datetime(year, 1, 1) - datetime.timedelta(milliseconds=1),
        )
        return Member.objects.filter(
            coopsharetransaction__transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
            coopsharetransaction__valid_at__range=timerange,
        )
