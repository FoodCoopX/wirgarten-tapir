import datetime

from tapir.configuration.models import TapirParameter
from tapir.deliveries.models import Joker
from tapir.deliveries.services.get_deliveries_service import GetDeliveriesService
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetDeliveriesServiceIsJokerUsedInWeek(TapirIntegrationTest):
    def setUp(self):
        ParameterDefinitions().import_definitions()

    def test_isJokerUsedInWeek_noJokerInWeek_returnsFalse(self):
        target_member = MemberFactory.create()
        other_member = MemberFactory.create()

        # Those jokers are all from other members or not in the given week
        Joker.objects.create(
            member=target_member, date=datetime.date(year=2025, month=3, day=2)
        )
        Joker.objects.create(
            member=other_member, date=datetime.date(year=2025, month=3, day=4)
        )
        Joker.objects.create(
            member=target_member, date=datetime.date(year=2025, month=3, day=13)
        )

        for weekday in range(7):
            self.assertFalse(
                GetDeliveriesService.is_joker_used_in_week(
                    target_member,
                    datetime.date(year=2025, month=3, day=3 + weekday),
                    cache={},
                )
            )

    def test_isJokerUsedInWeek_hasJokerInWeek_returnsTrue(self):
        target_member = MemberFactory.create()

        Joker.objects.create(
            member=target_member, date=datetime.date(year=2025, month=3, day=6)
        )

        for weekday in range(7):
            self.assertTrue(
                GetDeliveriesService.is_joker_used_in_week(
                    target_member,
                    datetime.date(year=2025, month=3, day=3 + weekday),
                    cache={},
                )
            )

    def test_isJokerUsedInWeek_hasJokerInWeekButFeatureIsDisabled_returnsFalse(self):
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value="False"
        )
        target_member = MemberFactory.create()

        Joker.objects.create(
            member=target_member, date=datetime.date(year=2025, month=3, day=6)
        )

        for weekday in range(7):
            self.assertFalse(
                GetDeliveriesService.is_joker_used_in_week(
                    target_member,
                    datetime.date(year=2025, month=3, day=3 + weekday),
                    cache={},
                )
            )
