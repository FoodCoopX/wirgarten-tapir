import datetime
from decimal import Decimal

from tapir.accounts.models import TapirUser
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.service.products import get_next_growing_period
from tapir.wirgarten.utils import get_now


class MemberSolidarityContributionService:
    @classmethod
    def get_member_contribution(
        cls, member_id: str, reference_date: datetime.date, cache: dict
    ):
        return TapirCache.get_member_solidarity_contribution_at_date(
            member_id=member_id, reference_date=reference_date, cache=cache
        )

    @classmethod
    def assign_contribution_to_member(
        cls,
        member_id: str,
        change_date: datetime.date,
        amount: float | Decimal,
        cache: dict,
    ):
        member_contributions = SolidarityContribution.objects.filter(
            member_id=member_id
        )
        member_contributions.filter(start_date__gte=change_date).delete()
        member_contributions.filter(end_date__gte=change_date).update(
            end_date=change_date - datetime.timedelta(days=1),
            cancellation_ts=get_now(cache=cache),
        )

        if amount == 0:
            return

        growing_period = TapirCache.get_growing_period_at_date(
            reference_date=change_date, cache=cache
        )
        if growing_period is None:
            future_growing_period = get_next_growing_period(
                reference_date=change_date, cache=cache
            )
            end_date = future_growing_period.start_date - datetime.timedelta(days=1)
        else:
            end_date = growing_period.end_date

        SolidarityContribution.objects.create(
            member_id=member_id,
            amount=amount,
            start_date=change_date,
            end_date=end_date,
        )

    @classmethod
    def is_user_allowed_to_change_contribution(
        cls,
        logged_in_user: TapirUser,
        target_member_id: str,
        new_amount: Decimal,
        change_date: datetime.date,
        cache: dict,
    ):
        if logged_in_user.has_perm(Permission.Coop.MANAGE):
            return True

        current_contribution = (
            MemberSolidarityContributionService.get_member_contribution(
                member_id=target_member_id, reference_date=change_date, cache=cache
            )
        )

        return new_amount > current_contribution
