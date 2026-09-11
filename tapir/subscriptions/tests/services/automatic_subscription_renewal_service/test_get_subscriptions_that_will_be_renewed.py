import datetime

from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.models import GrowingPeriod, ProductCapacity, Product
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    ProductCapacityFactory,
    GrowingPeriodFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetSubscriptionsThatWillBeRenewed(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, value=True)

        cls.product = ProductFactory.create()
        cls.new_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1)
        )
        ProductCapacityFactory(
            period=cls.new_growing_period, product_type=cls.product.type
        )

    def setUp(self) -> None:
        super().setUp()
        self.subscription = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2024, month=1, day=1),
            product=self.product,
        )

    def test_getSubscriptionsThatWillBeRenewed_subscriptionShouldBeRenewed_subscriptionReturned(
        self,
    ):
        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2025, month=1, day=1), cache={}
            )
        )

        self.assertEqual({self.subscription}, result)

    def test_getSubscriptionsThatWillBeRenewed_automaticRenewalDisabled_subscriptionNotReturned(
        self,
    ):
        self._set_parameter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, value=False
        )
        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2025, month=1, day=1), cache={}
            )
        )

        self.assertEqual(set(), result)

    def test_getSubscriptionsThatWillBeRenewed_noCurrentGrowingPeriod_subscriptionNotReturned(
        self,
    ):
        GrowingPeriod.objects.order_by("start_date").last().delete()
        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2025, month=1, day=1), cache={}
            )
        )

        self.assertEqual(set(), result)

    def test_getSubscriptionsThatWillBeRenewed_memberAlreadyHasASubscriptionForTheSameProduct_subscriptionNotReturned(
        self,
    ):
        SubscriptionFactory.create(
            member=self.subscription.member,
            product=self.subscription.product,
            period=self.new_growing_period,
        )
        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2025, month=1, day=1), cache={}
            )
        )

        self.assertEqual(set(), result)

    def test_getSubscriptionsThatWillBeRenewed_futureGrowingPeriodHasNoDefinedCapacity_subscriptionNotReturned(
        self,
    ):
        ProductCapacity.objects.all().delete()

        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2025, month=1, day=1), cache={}
            )
        )

        self.assertEqual(set(), result)

    def test_getSubscriptionsThatWillBeRenewed_futureGrowingPeriodHasNotEnoughCapacity_subscriptionReturned(
        self,
    ):
        # This is to make sure that the subscription gets renewed even if there is not enough capacity, as compared with
        # test_getSubscriptionsThatWillBeRenewed_futureGrowingPeriodHasNoDefinedCapacity_subscriptionNotReturned
        # where no capacity is defined at all
        ProductCapacity.objects.update(capacity=-10)

        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2025, month=1, day=1), cache={}
            )
        )

        self.assertEqual({self.subscription}, result)

    def test_getSubscriptionsThatWillBeRenewed_productMarkedAsDeleted_subscriptionNotReturned(
        self,
    ):
        Product.objects.update(deleted=True)

        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2025, month=1, day=1), cache={}
            )
        )

        self.assertEqual(set(), result)
