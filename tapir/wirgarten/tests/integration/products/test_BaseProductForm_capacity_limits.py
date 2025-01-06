import datetime

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import (
    ProductCapacity,
    Subscription,
    MemberPickupLocation,
    Member,
    GrowingPeriod,
    Product,
    ProductType,
    PickupLocationCapability,
)
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.factories import (
    ProductPriceFactory,
    ProductCapacityFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationCapabilityFactory,
    GrowingPeriodFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    mock_timezone,
)


class TestBaseProductFormCapacityLimits(TapirIntegrationTest):
    def setUp(self):
        ParameterDefinitions().import_definitions()
        now = datetime.datetime(year=2023, month=6, day=12)
        mock_timezone(self, now)
        configure_mail_module()

    def create_test_data_and_login(self, capacity):
        product_capacity: ProductCapacity = ProductCapacityFactory.create(
            capacity=capacity,
            product_type__name="Ernteanteile",
            product_type__delivery_cycle=WEEKLY[0],
        )
        growing_period = GrowingPeriod.objects.get()
        growing_period.start_date = datetime.date(year=2023, month=1, day=1)
        growing_period.end_date = datetime.date(year=2023, month=12, day=31)
        growing_period.save()

        parameter = TapirParameter.objects.get(key=Parameter.COOP_BASE_PRODUCT_TYPE)
        parameter.value = product_capacity.product_type.id
        parameter.save()

        ProductPriceFactory.create(
            product__type=product_capacity.product_type,
            product__name="M",
            size=1,
            valid_from=datetime.date(year=2023, month=1, day=1),
        )
        ProductPriceFactory.create(
            product__type=product_capacity.product_type,
            product__name="L",
            size=1.25,
            valid_from=datetime.date(year=2023, month=1, day=1),
        )

        member = MemberFactory.create()
        member_pickup_location: MemberPickupLocation = (
            MemberPickupLocationFactory.create(member=member)
        )
        PickupLocationCapabilityFactory.create(
            product_type=product_capacity.product_type,
            pickup_location=member_pickup_location.pickup_location,
        )

        self.client.force_login(member)

    def send_add_subscription_request(
        self,
        nb_m_shares,
        nb_l_shares,
        growing_period=None,
        solidarity_price_factor=0.0,
        member=None,
    ):
        if growing_period is None:
            growing_period = GrowingPeriod.objects.get()

        member = member or Member.objects.get()
        url = f"{reverse('wirgarten:member_add_subscription', args=[member.id])}?productType=Ernteanteile"
        return self.client.post(
            url,
            data={
                "growing_period": growing_period.id,
                "base_product_M": nb_m_shares,
                "base_product_L": nb_l_shares,
                "solidarity_price_harvest_shares": solidarity_price_factor,
            },
        )

    def test_baseProductForm_enoughCapacity_allSubscriptionsCreated(self):
        self.create_test_data_and_login(capacity=200)

        response = self.send_add_subscription_request(2, 1)

        self.assertStatusCode(response, 200)
        self.assertEqual(Subscription.objects.count(), 2)

        member = Member.objects.get()
        subscription_m: Subscription = Subscription.objects.get(product__name="M")
        self.assertEqual(member.id, subscription_m.member_id)
        self.assertEqual(2, subscription_m.quantity)

        subscription_l: Subscription = Subscription.objects.get(product__name="L")
        self.assertEqual(member.id, subscription_l.member_id)
        self.assertEqual(1, subscription_l.quantity)

    def test_baseProductForm_notEnoughCapacity_noSubscriptionsCreated(self):
        self.create_test_data_and_login(capacity=3)

        response = self.send_add_subscription_request(2, 1)

        self.assertStatusCode(response, 200)
        self.assertNotEqual(
            Subscription.objects.count(),
            1,
            "Even though there would be enough space for the S-product subscription, "
            "if there is not enough space for all subscriptions to be created then "
            "no subscription should be created",
        )
        self.assertFalse(
            Subscription.objects.exists(), "No subscription should have been created"
        )

    def test_baseProductForm_priceChangesBetweenNowAndContractStart_newPriceIsUsedForCalculations(
        self,
    ):
        self.create_test_data_and_login(capacity=1.1)

        ProductPriceFactory.create(
            product=Product.objects.get(name="M"),
            size=1.2,
            valid_from=datetime.date(year=2023, month=6, day=15),
        )

        response = self.send_add_subscription_request(1, 0)

        self.assertStatusCode(response, 200)
        self.assertFalse(
            Subscription.objects.exists(), "No subscription should have been created"
        )

    def test_baseProductForm_severalGrowingPeriods_theCapacityOfTheChosenGrowingPeriodGetsChecked(
        self,
    ):
        self.create_test_data_and_login(capacity=2)
        current_growing_period = GrowingPeriod.objects.get()

        future_growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1)
        )
        ProductCapacityFactory.create(
            period=future_growing_period,
            capacity=5,
            product_type=ProductType.objects.get(),
        )

        response = self.send_add_subscription_request(3, 0, current_growing_period)

        self.assertStatusCode(response, 200)
        self.assertFalse(
            Subscription.objects.exists(),
            "No subscription should have been created",
        )

        response = self.send_add_subscription_request(3, 0, future_growing_period)

        self.assertStatusCode(response, 200)
        self.assertEqual(Subscription.objects.count(), 1)

    def test_baseProductForm_notEnoughSolidarityAvailable_cantAddSubscriptionWithSolidarity(
        self,
    ):
        self.create_test_data_and_login(capacity=500)
        member = Member.objects.get()
        current_growing_period = GrowingPeriod.objects.get()
        SubscriptionFactory.create(
            solidarity_price=0.05, product=Product.objects.get(name="M"), quantity=1
        )

        response = self.send_add_subscription_request(
            1, 0, current_growing_period, -0.15, member
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            1,
            Subscription.objects.count(),
            "No subscription should have been created",
        )

    def test_baseProductForm_enoughSolidarityAvailable_canAddSubscriptionWithSolidarity(
        self,
    ):
        self.create_test_data_and_login(capacity=500)
        member = Member.objects.get()
        current_growing_period = GrowingPeriod.objects.get()
        SubscriptionFactory.create(
            solidarity_price=0.25, product=Product.objects.get(name="M"), quantity=1
        )

        response = self.send_add_subscription_request(
            1, 0, current_growing_period, -0.15, member
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(2, Subscription.objects.count())

    def test_baseProductForm_notEnoughCapacityInPickupLocation_noSubscriptionsCreated(
        self,
    ):
        self.create_test_data_and_login(capacity=150)

        pickup_location_capability: PickupLocationCapability = (
            PickupLocationCapability.objects.get()
        )
        pickup_location_capability.max_capacity = 1
        pickup_location_capability.save()

        response = self.send_add_subscription_request(0, 1)

        self.assertStatusCode(response, 200)
        self.assertFalse(
            Subscription.objects.exists(), "No subscription should have been created"
        )

    def test_baseProductForm_memberHasActiveSubscriptionsAndOrdersWithinCapacity_sizeOfCurrentSubscriptionsTakenIntoAccountForValidation(
        self,
    ):
        self.create_test_data_and_login(capacity=3)

        member = Member.objects.get()
        SubscriptionFactory.create(
            member=member,
            period=GrowingPeriod.objects.get(),
            quantity=2,
            product=Product.objects.get(name="M"),
        )

        response = self.send_add_subscription_request(3, 0)

        self.assertStatusCode(response, 200)

        subscription: Subscription = Subscription.objects.get(
            start_date=datetime.date(year=2023, month=7, day=1)
        )
        self.assertEqual(member.id, subscription.member_id)
        self.assertEqual(3, subscription.quantity)

    def test_baseProductForm_memberHasActiveSubscriptionsAndOrdersOverCapacity_sizeOfCurrentSubscriptionsTakenIntoAccountForValidation2(
        self,
    ):
        self.create_test_data_and_login(capacity=3)

        member = Member.objects.get()
        SubscriptionFactory.create(
            member=member,
            period=GrowingPeriod.objects.get(),
            quantity=2,
            product=Product.objects.get(name="M"),
        )

        response = self.send_add_subscription_request(4, 0)

        self.assertStatusCode(response, 200)

        self.assertEqual(1, Subscription.objects.count())
        subscription: Subscription = Subscription.objects.get()
        self.assertEqual(member.id, subscription.member_id)
        self.assertEqual(2, subscription.quantity)
