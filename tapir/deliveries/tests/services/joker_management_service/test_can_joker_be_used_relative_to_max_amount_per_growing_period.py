import datetime

from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import MemberFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCanJokerBeUsedRelativeToMaxAmountPerGrowingPeriod(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def setUp(self) -> None:
        mock_timezone(self, factories.NOW)

    def test_canJokerBeUsedRelativeToMaxAmountPerGrowingPeriod_noGrowingPeriod_returnsFalse(
        self,
    ):
        self.assertFalse(
            JokerManagementService.can_joker_be_used_relative_to_max_amount_per_growing_period(
                MemberFactory.create(), datetime.date.today(), cache={}
            )
        )

    def test_canJokerBeUsedRelativeToMaxAmountPerGrowingPeriod_fewEnoughJokerUsed_returnsTrue(
        self,
    ):
        growing_period = GrowingPeriodFactory.create(max_jokers_per_member=3)
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=growing_period.start_date + datetime.timedelta(days=1)
        )
        Joker.objects.create(
            member=member, date=growing_period.start_date + datetime.timedelta(days=2)
        )
        Joker.objects.create(
            member=member, date=growing_period.start_date - datetime.timedelta(days=1)
        )

        self.assertTrue(
            JokerManagementService.can_joker_be_used_relative_to_max_amount_per_growing_period(
                member, growing_period.start_date + datetime.timedelta(days=1), cache={}
            )
        )

    def test_canJokerBeUsedRelativeToMaxAmountPerGrowingPeriod_tooManyJokerUsed_returnsFalse(
        self,
    ):
        growing_period = GrowingPeriodFactory.create(max_jokers_per_member=2)
        member = MemberFactory.create()
        Joker.objects.create(
            member=member, date=growing_period.start_date + datetime.timedelta(days=1)
        )
        Joker.objects.create(
            member=member, date=growing_period.start_date + datetime.timedelta(days=2)
        )

        self.assertFalse(
            JokerManagementService.can_joker_be_used_relative_to_max_amount_per_growing_period(
                member, growing_period.start_date + datetime.timedelta(days=1), cache={}
            )
        )
