import random
from datetime import date

from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member
from tapir.wirgarten.service.member import annotate_member_queryset_with_monthly_payment
from tapir.wirgarten.utils import get_today


class SolidarityContributionGenerator:
    POSSIBLE_AMOUNTS = [-20, -15, -10, -5, 5, 10, 15, 20]

    @classmethod
    def generate_solidarity_contributions(cls):
        cache = {}

        reference_date = get_today(cache=cache)
        members = annotate_member_queryset_with_monthly_payment(
            queryset=Member.objects.all(), reference_date=reference_date
        )
        contributions_to_create = []

        for member in members:
            if random.random() < 0.75:
                continue

            contributions_to_create.append(
                cls._generate_solidarity_contribution_for_member(
                    member=member, reference_date=reference_date, cache=cache
                )
            )

        SolidarityContribution.objects.bulk_create(contributions_to_create)

    @classmethod
    def _generate_solidarity_contribution_for_member(
        cls, member, reference_date: date, cache: dict
    ) -> SolidarityContribution:
        possible_amounts_for_this_member = [
            amount
            for amount in cls.POSSIBLE_AMOUNTS
            if amount > 0 or -amount <= member.monthly_payment
        ]
        possible_amounts_for_this_member.append(random.random() * 40 - 20)

        subscriptions = TapirCache.get_active_and_future_subscriptions_by_member_id(
            cache=cache, reference_date=reference_date
        ).get(member.id, [])
        if len(subscriptions) == 0:
            growing_period = TapirCache.get_growing_period_at_date(
                reference_date=reference_date, cache=cache
            )
            start_date = growing_period.start_date
            end_date = growing_period.end_date
        else:
            subscription = random.choice(subscriptions)
            start_date = subscription.start_date
            end_date = subscription.end_date

        return SolidarityContribution(
            member=member,
            amount=random.choice(possible_amounts_for_this_member),
            start_date=start_date,
            end_date=end_date,
        )
