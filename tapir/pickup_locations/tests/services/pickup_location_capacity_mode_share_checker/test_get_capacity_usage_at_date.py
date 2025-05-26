import datetime

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.wirgarten.models import MemberPickupLocation, Subscription, GrowingPeriod
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    MemberPickupLocationFactory,
    ProductTypeFactory,
    SubscriptionFactory,
    ProductPriceFactory,
    ProductFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetCapacityUsageAtDate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        member = MemberFactory.create()
        cls.pickup_location = PickupLocationFactory.create()
        cls.reference_date = datetime.date(year=2026, month=3, day=12)
        MemberPickupLocationFactory.create(
            pickup_location=cls.pickup_location,
            member=member,
            valid_from=cls.reference_date - datetime.timedelta(days=1),
        )
        cls.product_type = ProductTypeFactory.create()
        product = ProductFactory.create(type=cls.product_type)
        start_date = cls.reference_date - datetime.timedelta(days=1)
        end_date = cls.reference_date + datetime.timedelta(days=1)
        SubscriptionFactory.create(
            product=product,
            member=member,
            start_date=start_date,
            end_date=end_date,
            period__start_date=start_date,
            period__end_date=end_date,
            quantity=3,
        )
        ProductPriceFactory.create(
            product=product,
            size=2,
            valid_from=cls.reference_date - datetime.timedelta(days=1),
        )

    def test_getCapacityUsageAtDate_memberNotAtPickupStation_memberNotIncludedInUsage(
        self,
    ):
        MemberPickupLocation.objects.update(
            valid_from=self.reference_date + datetime.timedelta(days=1)
        )

        result = PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
            self.pickup_location, self.product_type, self.reference_date, {}
        )

        self.assertEqual(0, result)

    def test_getCapacityUsageAtDate_subscriptionNotActive_subscriptionNotIncludedInUsage(
        self,
    ):
        Subscription.objects.update(
            start_date=self.reference_date + datetime.timedelta(days=1)
        )

        result = PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
            self.pickup_location, self.product_type, self.reference_date, {}
        )

        self.assertEqual(0, result)

    def test_getCapacityUsageAtDate_default_countsCorrectly(
        self,
    ):
        result = PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
            self.pickup_location, self.product_type, self.reference_date, {}
        )

        self.assertEqual(6, result)

    def test_getCapacityUsageAtDate_subscriptionWillBeRenewed_pastSubscriptionCounted(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        current_growing_period = GrowingPeriod.objects.get()
        past_growing_period = GrowingPeriodFactory.create(
            start_date=current_growing_period.start_date - datetime.timedelta(days=2),
            end_date=current_growing_period.start_date - datetime.timedelta(days=1),
        )
        Subscription.objects.update(
            period=current_growing_period,
            start_date=past_growing_period.start_date,
            end_date=past_growing_period.end_date,
        )
        result = PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
            self.pickup_location, self.product_type, self.reference_date, {}
        )

        self.assertEqual(6, result)

    def test_getCapacityUsageAtDate_subscriptionWillNotRenewedBecauseOfParameter_pastSubscriptionNotCounted(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=False)
        current_growing_period = GrowingPeriod.objects.get()
        past_growing_period = GrowingPeriodFactory.create(
            start_date=current_growing_period.start_date - datetime.timedelta(days=2),
            end_date=current_growing_period.start_date - datetime.timedelta(days=1),
        )
        Subscription.objects.update(
            period=current_growing_period,
            start_date=past_growing_period.start_date,
            end_date=past_growing_period.end_date,
        )
        result = PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
            self.pickup_location, self.product_type, self.reference_date, {}
        )

        self.assertEqual(0, result)
