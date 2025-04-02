import datetime

from tapir.configuration.models import TapirParameter
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import MemberFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCanJokerBeUsedRelativeToMaxAmountPerGrowingPeriod(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()
        mock_timezone(self, factories.NOW)

    def test_canJokerBeUsedRelativeToMaxAmountPerGrowingPeriod_noGrowingPeriod_returnsFalse(
        self,
    ):
        self.assertFalse(
            JokerManagementService.can_joker_be_used_relative_to_max_amount_per_growing_period(
                MemberFactory.create(), datetime.date.today()
            )
        )

    def test_canJokerBeUsedRelativeToMaxAmountPerGrowingPeriod_fewEnoughJokerUsed_returnsTrue(
        self,
    ):
        growing_period = GrowingPeriodFactory.create()
        member = MemberFactory.create()
        TapirParameter.objects.filter(
            key=ParameterKeys.JOKERS_AMOUNT_PER_CONTRACT
        ).update(value="3")
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
                member, growing_period.start_date + datetime.timedelta(days=1)
            )
        )

    def test_canJokerBeUsedRelativeToMaxAmountPerGrowingPeriod_tooManyJokerUsed_returnsFalse(
        self,
    ):
        growing_period = GrowingPeriodFactory.create()
        member = MemberFactory.create()
        TapirParameter.objects.filter(
            key=ParameterKeys.JOKERS_AMOUNT_PER_CONTRACT
        ).update(value="2")
        Joker.objects.create(
            member=member, date=growing_period.start_date + datetime.timedelta(days=1)
        )
        Joker.objects.create(
            member=member, date=growing_period.start_date + datetime.timedelta(days=2)
        )

        self.assertFalse(
            JokerManagementService.can_joker_be_used_relative_to_max_amount_per_growing_period(
                member, growing_period.start_date + datetime.timedelta(days=1)
            )
        )
