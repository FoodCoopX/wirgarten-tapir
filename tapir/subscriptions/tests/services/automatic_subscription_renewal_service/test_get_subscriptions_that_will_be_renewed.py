import datetime

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.models import Subscription, GrowingPeriod
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import GrowingPeriodFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetSubscriptionsThatWillBeRenewed(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        previous_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
        )
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2027, month=1, day=1),
            end_date=datetime.date(year=2027, month=12, day=31),
        )
        SubscriptionFactory.create(period=previous_growing_period, cancellation_ts=None)

    def test_getSubscriptionsThatWillBeRenewed_subscriptionWillBeRenewed_subscriptionIsIncludedInResult(
        self,
    ):
        subscription = Subscription.objects.get()

        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2027, month=1, day=1), cache={}
            )
        )

        self.assertEqual(1, len(result))
        self.assertIn(subscription, result)

    def test_getSubscriptionsThatWillBeRenewed_automaticRenewalIsOff_subscriptionIsNotIncludedInResult(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=False)

        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2027, month=1, day=1), cache={}
            )
        )

        self.assertEqual(0, len(result))

    def test_getSubscriptionsThatWillBeRenewed_noCurrentGrowingPeriod_subscriptionIsNotIncludedInResult(
        self,
    ):
        GrowingPeriod.objects.filter(start_date__year=2027).delete()

        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2027, month=1, day=1), cache={}
            )
        )

        self.assertEqual(0, len(result))

    def test_getSubscriptionsThatWillBeRenewed_subscriptionOfSameProductTypeExistsInCurrentPeriod_subscriptionIsNotIncludedInResult(
        self,
    ):
        past_subscription = Subscription.objects.get()
        SubscriptionFactory.create(
            period=GrowingPeriod.objects.get(start_date__year=2027),
            product__type=past_subscription.product.type,
            member=past_subscription.member,
        )

        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2027, month=1, day=1), cache={}
            )
        )

        self.assertEqual(0, len(result))

    def test_getSubscriptionsThatWillBeRenewed_similarButNotRelevantSubscriptionExistsInCurrentPeriod_subscriptionIsIncludedInResult(
        self,
    ):
        past_subscription = Subscription.objects.get()
        SubscriptionFactory.create(
            period=GrowingPeriod.objects.get(start_date__year=2027),
            member=past_subscription.member,
        )  # different product type
        SubscriptionFactory.create(
            period=GrowingPeriod.objects.get(start_date__year=2027),
            product__type=past_subscription.product.type,
        )  # different member

        result = (
            AutomaticSubscriptionRenewalService.get_subscriptions_that_will_be_renewed(
                reference_date=datetime.date(year=2027, month=1, day=1), cache={}
            )
        )

        self.assertEqual(1, len(result))
        self.assertIn(past_subscription, result)
