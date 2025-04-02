import datetime
import random

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.models import GrowingPeriod, Member, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today


class TestJokerGenerator:
    @classmethod
    def generate_jokers(cls):
        if not get_parameter_value(ParameterKeys.JOKERS_ENABLED):
            return

        for growing_period in GrowingPeriod.objects.filter(start_date__lte=get_today()):
            for member in Member.objects.all():
                subscriptions = Subscription.objects.filter(
                    member=member, period=growing_period
                )
                if not subscriptions.exists():
                    continue

                start_date = subscriptions.order_by("start_date").first().start_date
                end_date = subscriptions.order_by("end_date").last().end_date
                nb_jokers = random.randint(
                    0, get_parameter_value(ParameterKeys.JOKERS_AMOUNT_PER_CONTRACT)
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
