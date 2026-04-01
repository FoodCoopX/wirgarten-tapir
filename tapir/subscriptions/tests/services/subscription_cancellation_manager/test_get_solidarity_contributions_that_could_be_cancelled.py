import datetime

from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetSolidarityContributionsThatCouldBeCancelled(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getSolidarityContributionsThatCouldBeCancelled_default_returnsFutureContributionsSortedByEndDate(
        self,
    ):
        mock_timezone(test=self, now=datetime.datetime(year=2035, month=7, day=22))
        member = MemberFactory.create()

        SolidarityContributionFactory.create(
            member=member, end_date=datetime.date(year=2030, month=12, day=31)
        )
        solidarity_2 = SolidarityContributionFactory.create(
            member=member, end_date=datetime.date(year=2036, month=1, day=1)
        )
        solidarity_3 = SolidarityContributionFactory.create(
            member=member, end_date=datetime.date(year=2035, month=8, day=12)
        )

        result = SubscriptionCancellationManager.get_solidarity_contributions_that_could_be_cancelled(
            member=member, cache={}
        )

        self.assertEqual([solidarity_3, solidarity_2], list(result))
