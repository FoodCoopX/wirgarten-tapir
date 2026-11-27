import datetime

from django.db.models import Q, QuerySet

from tapir.associations.models import AssociationMembership
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.models import CoopShareTransaction, Member
from tapir.wirgarten.service.products import get_active_and_future_subscriptions


class ActiveMemberProvider:
    @staticmethod
    def get_active_members(
        reference_datetime: datetime.datetime, cache: dict
    ) -> QuerySet[Member]:
        reference_date = reference_datetime.date()
        member_ids_with_active_shares = set(
            Member.objects.with_shares(reference_date=reference_date).values_list(
                "id", flat=True
            )
        )
        member_ids_with_shares_in_the_future = set(
            CoopShareTransaction.objects.filter(
                transaction_type__in=[
                    CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN,
                    CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                ],
                valid_at__gte=reference_date,
            ).values_list("member_id", flat=True)
        )
        member_ids_with_active_or_future_subscriptions = set(
            get_active_and_future_subscriptions(
                reference_date=reference_date, cache=cache
            ).values_list("member_id", flat=True)
        )
        member_ids_with_active_or_future_association_membership = (
            AssociationMembership.objects.filter(
                Q(end_date=None) | Q(end_date__gte=reference_date)
            ).values_list("member_id", flat=True)
        )
        member_ids_with_active_or_future_solidarity_contribution = (
            SolidarityContribution.objects.filter(
                amount__gt=0, end_date__gte=reference_date
            ).values_list("member_id", flat=True)
        )

        return Member.objects.filter(
            id__in=member_ids_with_active_shares.union(
                member_ids_with_shares_in_the_future,
                member_ids_with_active_or_future_subscriptions,
                member_ids_with_active_or_future_association_membership,
                member_ids_with_active_or_future_solidarity_contribution,
            )
        )
