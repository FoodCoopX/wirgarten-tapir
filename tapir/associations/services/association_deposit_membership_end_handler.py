import datetime
from collections.abc import Iterable, Iterator

from tapir.associations.models import AssociationDeposit, AssociationMembership


def iter_continuous_memberships(
    memberships: Iterable[AssociationMembership], covered_until: datetime.date
) -> Iterator[AssociationMembership]:
    for membership in memberships:
        if (membership.start_date - covered_until).days > 1:
            break
        yield membership
        if membership.end_date is None:
            break
        covered_until = max(covered_until, membership.end_date)


class AssociationDepositMembershipEndHandler:
    @staticmethod
    def preserve_deposits(
        membership: AssociationMembership,
        end_date: datetime.date,
        *,
        removes_future=False
    ):
        if membership.end_date is None or end_date > membership.end_date:
            return
        if end_date == membership.end_date and not removes_future:
            return

        covered_until = membership.end_date
        following = (
            AssociationMembership.objects.filter(
                member_id=membership.member_id, start_date__gt=covered_until
            )
            .select_for_update()
            .order_by("start_date", "pk")
        )
        for next_membership in iter_continuous_memberships(following, covered_until):
            if AssociationDeposit.objects.filter(membership=next_membership).update(
                membership=membership
            ):
                break
