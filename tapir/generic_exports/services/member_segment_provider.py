import datetime

from django.db.models import QuerySet
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.deliveries.models import Joker
from tapir.generic_exports.services.export_segment_manager import ExportSegment
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.utils.services.tapir_cache import TapirCache
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
            ExportSegment(
                id="members.with_too_few_coop_shares",
                display_name="Mitglieder die nicht genug Geno-Anteile haben",
                description="Mitglieder die nicht genug Geno-Anteile haben relativ zu der aus der Konfig minimum an Anteile und ggbf zu den minimum Geno-Anteile pro Produkt-Anteil",
                get_queryset=cls.get_queryset_members_with_too_few_coop_shares,
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

        growing_period = get_current_growing_period(reference_datetime.date())
        member_ids = Joker.objects.filter(
            date__gte=growing_period.start_date,
            date__lte=reference_datetime.date(),
        ).values_list("member_id")

        return Member.objects.filter(id__in=member_ids).order_by("member_no").distinct()

    @classmethod
    def get_queryset_members_with_too_few_coop_shares(
        cls, reference_datetime: datetime.datetime
    ) -> QuerySet:
        from tapir.wirgarten.models import Member

        cache = {}
        active_subscriptions = TapirCache.get_subscriptions_active_at_date(
            cache=cache, reference_date=reference_datetime.date()
        )
        active_subscriptions_by_member_id = {}
        for subscription in active_subscriptions:
            if subscription.member_id not in active_subscriptions_by_member_id.keys():
                active_subscriptions_by_member_id[subscription.member_id] = []
            active_subscriptions_by_member_id[subscription.member_id].append(
                subscription
            )

        member_ids_to_include = []
        for member in Member.objects.filter(is_student=False):
            current_number_of_shares = (
                TapirCache.get_number_of_shares_for_member_id_at_date(
                    cache=cache,
                    member_id=member.id,
                    reference_date=reference_datetime.date(),
                )
            )

            member_subscriptions = active_subscriptions_by_member_id.get(member.id, [])
            if len(member_subscriptions) == 0 and current_number_of_shares == 0:
                # that person is not a member
                continue

            minimum_number_of_shares = (
                MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_order(
                    ordered_products_id_to_quantity_map={
                        subscription.product_id: subscription.quantity
                        for subscription in member_subscriptions
                    },
                    cache=cache,
                )
            )

            if minimum_number_of_shares > current_number_of_shares:
                member_ids_to_include.append(member.id)

        return (
            Member.objects.filter(id__in=member_ids_to_include)
            .order_by("member_no")
            .distinct()
        )
