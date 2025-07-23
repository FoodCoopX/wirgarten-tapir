import datetime
from unittest.mock import Mock

from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestJokerManagementServiceCanJokerBeUsedRelativeToRestrictions(
    TapirIntegrationTest
):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_canJokerBeUsedRelativeToRestrictions_noRestrictions_returnsTrue(self):
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2022, month=5, day=1),
            end_date=datetime.date(year=2022, month=5, day=30),
            joker_restrictions="disabled",
        )

        self.assertTrue(
            JokerManagementService.can_joker_be_used_relative_to_restrictions(
                Mock(),
                reference_date=datetime.date(year=2022, month=5, day=15),
                cache={},
            )
        )

    def test_canJokerBeUsedRelativeToRestrictions_restrictionsAllowNewJoker_returnsTrue(
        self,
    ):
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
            joker_restrictions="01.08.-31.08.[2];15.02.-20.03.[3]",
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
                member, datetime.date(year=2025, month=8, day=5), cache={}
            )
        )

    def test_canJokerBeUsedRelativeToRestrictions_restrictionsDontAllowNewJoker_returnsFalse(
        self,
    ):
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
            joker_restrictions="01.08.-31.08.[2];15.02.-20.03.[3]",
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
                member, datetime.date(year=2025, month=8, day=15), cache={}
            )
        )
