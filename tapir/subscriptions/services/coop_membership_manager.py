import datetime

from tapir.wirgarten.utils import get_today


class CoopMembershipManager:
    @staticmethod
    def can_member_cancel_coop_membership(
        member, reference_date: datetime.date | None = None
    ):
        if reference_date is None:
            reference_date = get_today()

        return (
            member.coop_entry_date is not None
            and member.coop_entry_date > reference_date
        )
