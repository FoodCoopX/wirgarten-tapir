import datetime

from tapir.pickup_locations.services.pickup_location_capacity_mode_basket_checker import (
    PickupLocationCapacityModeBasketChecker,
)
from tapir.wirgarten.models import Subscription, Member, Product
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    SubscriptionFactory,
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
        reference_date = datetime.date(year=2024, month=1, day=1)

        result = PickupLocationCapacityModeBasketChecker.extend_subscriptions_with_those_that_will_be_renewed(
            subscriptions=set(),
            reference_date=reference_date,
            members_at_pickup_location=Member.objects.all(),
            cache={},
        )

        self.assertEqual(1, len(result))

    def test_extendSubscriptionsWithThoseThatWillBeRenewed_subscriptionCancelled_dontExtendQuerySet(
        self,
    ):
        reference_date = datetime.date(year=2024, month=1, day=1)

        Subscription.objects.update(cancellation_ts=reference_date)

        result = PickupLocationCapacityModeBasketChecker.extend_subscriptions_with_those_that_will_be_renewed(
            subscriptions=set(),
            reference_date=reference_date,
            members_at_pickup_location=Member.objects.all(),
            cache={},
        )

        self.assertEqual(0, len(result))

    def test_extendSubscriptionsWithThoseThatWillBeRenewed_subscriptionIsAlreadyRenewed_dontExtendQuerySet(
        self,
    ):
        current_subscription = SubscriptionFactory.create(
            period=self.current_growing_period,
            member=Member.objects.get(),
            product=Product.objects.get(),
        )

        reference_date = datetime.date(year=2024, month=1, day=1)

        result = PickupLocationCapacityModeBasketChecker.extend_subscriptions_with_those_that_will_be_renewed(
            subscriptions=set(
                Subscription.objects.filter(period=self.current_growing_period)
            ),
            reference_date=reference_date,
            members_at_pickup_location=Member.objects.all(),
            cache={},
        )

        self.assertEqual(1, len(result))
        self.assertNotIn(self.past_subscription, result)
        self.assertIn(current_subscription, result)
