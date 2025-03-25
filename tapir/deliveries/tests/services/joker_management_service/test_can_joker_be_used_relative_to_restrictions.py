import datetime
from unittest.mock import Mock

from tapir.configuration.models import TapirParameter
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestJokerManagementServiceCanJokerBeUsedRelativeToRestrictions(
    TapirIntegrationTest
):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

    def test_canJokerBeUsedRelativeToRestrictions_noRestrictions_returnsTrue(self):
        TapirParameter.objects.filter(key=Parameter.JOKERS_RESTRICTIONS).update(
            value="disabled"
        )
        self.assertTrue(
            JokerManagementService.can_joker_be_used_relative_to_restrictions(
                Mock(), Mock()
            )
        )

    def test_canJokerBeUsedRelativeToRestrictions_restrictionsAllowNewJoker_returnsTrue(
        self,
    ):
        TapirParameter.objects.filter(key=Parameter.JOKERS_RESTRICTIONS).update(
            value="01.08-31.08[2];15.02-20.03[3]"
        )
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=8, day=5)
        )
        for _ in range(3):
            Joker.objects.create(
                member=member, date=datetime.date(year=2025, month=7, day=5)
            )

        self.assertTrue(
            JokerManagementService.can_joker_be_used_relative_to_restrictions(
                member, datetime.date(year=2025, month=8, day=5)
            )
        )

    def test_canJokerBeUsedRelativeToRestrictions_restrictionsDontAllowNewJoker_returnsFalse(
        self,
    ):
        TapirParameter.objects.filter(key=Parameter.JOKERS_RESTRICTIONS).update(
            value="01.08-31.08[2];15.02-20.03[3]"
        )
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=8, day=5)
        )
        Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=8, day=10)
        )

        self.assertFalse(
            JokerManagementService.can_joker_be_used_relative_to_restrictions(
                member, datetime.date(year=2025, month=8, day=15)
            )
        )
