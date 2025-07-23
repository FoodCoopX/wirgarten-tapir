import datetime

from tapir.subscriptions.services.subscription_cancellation_manager import (
    SubscriptionCancellationManager,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetEarliestPossibleCancellationDate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        mock_timezone(self, datetime.datetime(year=2022, month=6, day=7))

    def test_getEarliestPossibleCancellationDate_earliestSubscriptionIsInTrial_returnsTrialCancellationDate(
        self,
    ):
        member = MemberFactory.create()
        growing_period_1 = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        growing_period_2 = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2023, month=1, day=1),
            end_date=datetime.datetime(year=2023, month=12, day=31),
        )
        product = ProductFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=growing_period_1,
            product=product,
            start_date=datetime.date(year=2022, month=6, day=1),
        )
        SubscriptionFactory.create(
            member=member, period=growing_period_2, product=product
        )

        result = (
            SubscriptionCancellationManager.get_earliest_possible_cancellation_date(
                product, member, cache={}
            )
        )

        self.assertEqual(datetime.date(year=2022, month=6, day=9), result)

    def test_getEarliestPossibleCancellationDate_noSubscriptionInTrial_returnsBiggestSubscriptionEndDate(
        self,
    ):
        member = MemberFactory.create()
        growing_period_1 = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        growing_period_2 = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2023, month=1, day=1),
            end_date=datetime.datetime(year=2023, month=12, day=31),
        )
        product = ProductFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=growing_period_1,
            product=product,
            start_date=datetime.date(year=2022, month=4, day=1),
        )
        SubscriptionFactory.create(
            member=member, period=growing_period_2, product=product
        )

        result = (
            SubscriptionCancellationManager.get_earliest_possible_cancellation_date(
                product, member, cache={}
            )
        )

        self.assertEqual(datetime.date(year=2023, month=12, day=31), result)
