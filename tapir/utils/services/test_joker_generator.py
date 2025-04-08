import datetime
import random

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.models import GrowingPeriod, Member
from tapir.wirgarten.parameters import Parameter
from tapir.wirgarten.utils import get_today


class TestJokerGenerator:
    @classmethod
    def generate_jokers(cls):
        if not get_parameter_value(Parameter.JOKERS_ENABLED):
            return

        for growing_period in GrowingPeriod.objects.filter(start_date__lte=get_today()):
            for member in Member.objects.all().prefetch_related("subscription_set"):
                subscriptions = [
                    subscription
                    for subscription in member.subscription_set.all()
                    if subscription.period_id == growing_period.id
                ]
                if not subscriptions:
                    continue
                subscriptions.sort(key=lambda subscription: subscription.start_date)
                start_date = subscriptions[0].start_date
                end_date = subscriptions[-1].end_date
                nb_jokers = random.randint(
                    0, get_parameter_value(Parameter.JOKERS_AMOUNT_PER_CONTRACT)
                )
                for _ in range(nb_jokers):
                    random_date = start_date + datetime.timedelta(
                        days=random.randint(0, (end_date - start_date).days)
                    )
                    if JokerManagementService.does_member_have_a_joker_in_week(
                        member, random_date
                    ) or not JokerManagementService.can_joker_be_used_relative_to_restrictions(
                        member, random_date
                    ):
                        continue
                    Joker.objects.create(member=member, date=random_date)
