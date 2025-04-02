import datetime

from tapir.pickup_locations.services.pickup_location_capacity_mode_share_checker import (
    PickupLocationCapacityModeShareChecker,
)
from tapir.wirgarten.models import MemberPickupLocation, Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    MemberPickupLocationFactory,
    ProductTypeFactory,
    SubscriptionFactory,
    ProductPriceFactory,
    ProductFactory,
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
        SubscriptionFactory.create(
            product=product,
            member=member,
            start_date=cls.reference_date - datetime.timedelta(days=1),
            end_date=cls.reference_date + datetime.timedelta(days=1),
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
            self.pickup_location, self.product_type, self.reference_date
        )

        self.assertEqual(0, result)

    def test_getCapacityUsageAtDate_subscriptionNotActive_subscriptionNotIncludedInUsage(
        self,
    ):
        Subscription.objects.update(
            start_date=self.reference_date + datetime.timedelta(days=1)
        )

        result = PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
            self.pickup_location, self.product_type, self.reference_date
        )

        self.assertEqual(0, result)

    def test_getCapacityUsageAtDate_default_countsCorrectly(
        self,
    ):
        result = PickupLocationCapacityModeShareChecker.get_capacity_usage_at_date(
            self.pickup_location, self.product_type, self.reference_date
        )

        self.assertEqual(6, result)
