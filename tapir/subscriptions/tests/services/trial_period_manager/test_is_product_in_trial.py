import datetime
from unittest.mock import Mock

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    ProductFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestIsProductInTrial(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        self.today = mock_timezone(
            self, datetime.datetime(year=2021, month=8, day=10)
        ).date()

    def test_isProductInTrial_earliestSubscriptionIsInTrial_returnsTrue(self):
        member = MemberFactory.create()
        product = ProductFactory.create()
        growing_period_1 = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2021, month=1, day=1),
            end_date=datetime.datetime(year=2021, month=12, day=31),
        )
        growing_period_2 = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        SubscriptionFactory.create(
            member=member,
            period=growing_period_1,
            product=product,
            start_date=datetime.date(year=2021, month=8, day=1),
        )
        SubscriptionFactory.create(
            member=member, period=growing_period_2, product=product
        )
        SubscriptionFactory.create(
            member=member,
            period=growing_period_1,
            product=ProductFactory.create(),
        )

        result = TrialPeriodManager.is_product_in_trial(product, member, cache={})

        self.assertTrue(result)

    def test_isProductInTrial_noSubscriptionInTrial_returnsFalse(self):
        member = MemberFactory.create()
        product = ProductFactory.create()
        growing_period_1 = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2021, month=1, day=1),
            end_date=datetime.datetime(year=2021, month=12, day=31),
        )
        growing_period_2 = GrowingPeriodFactory.create(
            start_date=datetime.datetime(year=2022, month=1, day=1),
            end_date=datetime.datetime(year=2022, month=12, day=31),
        )
        SubscriptionFactory.create(
            member=member,
            period=growing_period_1,
            product=product,
            start_date=datetime.date(year=2021, month=6, day=1),
        )
        SubscriptionFactory.create(
            member=member, period=growing_period_2, product=product
        )
        SubscriptionFactory.create(
            member=member,
            period=growing_period_1,
            product=ProductFactory.create(),
        )

        result = TrialPeriodManager.is_product_in_trial(product, member, cache={})

        self.assertFalse(result)

    def test_isProductInTrial_trialsAreDisabled_returnsFalse(self):
        TapirParameter.objects.filter(key=ParameterKeys.TRIAL_PERIOD_ENABLED).update(
            value=False
        )
        member = Mock()
        product = Mock()

        result = TrialPeriodManager.is_product_in_trial(product, member, cache={})

        self.assertFalse(result)
