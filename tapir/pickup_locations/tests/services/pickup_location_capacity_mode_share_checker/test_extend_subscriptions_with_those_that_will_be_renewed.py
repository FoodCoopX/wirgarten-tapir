import datetime

from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.wirgarten.models import Subscription, ProductType, Member, Product
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    SubscriptionFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExtendSubscriptionsWithThoseThatWillBeRenewed(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        cls.past_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        cls.current_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1),
            end_date=datetime.date(year=2024, month=12, day=31),
        )
        cls.past_subscription = SubscriptionFactory.create(
            period=cls.past_growing_period
        )

    def test_extendSubscriptionsWithThoseThatWillBeRenewed_renewalWillHappen_returnsExtendedQuerySet(
        self,
    ):
        result = PickupLocationCapacityModeShareChecker.extend_subscriptions_with_those_that_will_be_renewed(
            subscriptions_active_at_reference_date=Subscription.objects.none(),
            reference_date=datetime.date(year=2024, month=1, day=1),
            product_type=ProductType.objects.get(),
            members_at_pickup_location=Member.objects.all(),
            cache=None,
        )

        self.assertEqual(1, result.count())

    def test_extendSubscriptionsWithThoseThatWillBeRenewed_subscriptionCancelled_dontExtendQuerySet(
        self,
    ):
        Subscription.objects.update(
            cancellation_ts=datetime.datetime(year=2024, month=1, day=1)
        )
        result = PickupLocationCapacityModeShareChecker.extend_subscriptions_with_those_that_will_be_renewed(
            subscriptions_active_at_reference_date=Subscription.objects.none(),
            reference_date=datetime.date(year=2024, month=1, day=1),
            product_type=ProductType.objects.get(),
            members_at_pickup_location=Member.objects.all(),
            cache=None,
        )

        self.assertEqual(0, result.count())

    def test_extendSubscriptionsWithThoseThatWillBeRenewed_subscriptionIsAlreadyRenewed_dontExtendQuerySet(
        self,
    ):
        current_subscription = SubscriptionFactory.create(
            period=self.current_growing_period,
            member=Member.objects.get(),
            product=Product.objects.get(),
        )
        result = PickupLocationCapacityModeShareChecker.extend_subscriptions_with_those_that_will_be_renewed(
            subscriptions_active_at_reference_date=Subscription.objects.filter(
                period=self.current_growing_period
            ),
            reference_date=datetime.date(year=2024, month=1, day=1),
            product_type=ProductType.objects.get(),
            members_at_pickup_location=Member.objects.all(),
            cache=None,
        )

        self.assertEqual(1, result.count())
        self.assertNotIn(self.past_subscription, result)
        self.assertIn(current_subscription, result)

    def test_extendSubscriptionsWithThoseThatWillBeRenewed_renewedSubscriptionHasOtherProductType_dontExtendQuerySet(
        self,
    ):
        result = PickupLocationCapacityModeShareChecker.extend_subscriptions_with_those_that_will_be_renewed(
            subscriptions_active_at_reference_date=Subscription.objects.none(),
            reference_date=datetime.date(year=2024, month=1, day=1),
            product_type=ProductTypeFactory.create(),
            members_at_pickup_location=Member.objects.all(),
            cache=None,
        )

        self.assertEqual(0, result.count())
