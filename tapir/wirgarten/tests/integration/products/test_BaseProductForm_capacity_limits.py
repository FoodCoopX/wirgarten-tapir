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
)
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests.factories import (
    ProductPriceFactory,
    ProductCapacityFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationCapabilityFactory,
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

    def create_test_data_and_login(self, capacity):
        product_capacity: ProductCapacity = ProductCapacityFactory.create(
            capacity=capacity,
            product_type__name="Ernteanteile",
            product_type__delivery_cycle=WEEKLY[0],
        )

        parameter = TapirParameter.objects.get(key=Parameter.COOP_BASE_PRODUCT_TYPE)
        parameter.value = product_capacity.product_type.id
        parameter.save()

        ProductPriceFactory.create(
            product__type=product_capacity.product_type,
            product__name="M",
            price=50,
            valid_from=datetime.date(year=2023, month=1, day=1),
        )
        ProductPriceFactory.create(
            product__type=product_capacity.product_type,
            product__name="L",
            price=75,
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

    def test_baseProductForm_enoughCapacity_allSubscriptionsCreated(self):
        self.create_test_data_and_login(capacity=200)

        member = Member.objects.get()
        url = f"{reverse('wirgarten:member_add_subscription', args=[member.id])}?productType=Ernteanteile"
        response = self.client.post(
            url,
            data={
                "growing_period": GrowingPeriod.objects.get().id,
                "base_product_M": 2,
                "base_product_L": 1,
                "solidarity_price_harvest_shares": 0.0,
            },
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(Subscription.objects.count(), 2)

        subscription_m: Subscription = Subscription.objects.get(product__name="M")
        self.assertEqual(member.id, subscription_m.member_id)
        self.assertEqual(2, subscription_m.quantity)

        subscription_l: Subscription = Subscription.objects.get(product__name="L")
        self.assertEqual(member.id, subscription_l.member_id)
        self.assertEqual(1, subscription_l.quantity)

    def test_baseProductForm_notEnoughCapacity_noSubscriptionsCreated(self):
        self.create_test_data_and_login(capacity=150)

        member = Member.objects.get()
        url = f"{reverse('wirgarten:member_add_subscription', args=[member.id])}?productType=Ernteanteile"
        response = self.client.post(
            url,
            data={
                "growing_period": GrowingPeriod.objects.get().id,
                "base_product_M": 2,
                "base_product_L": 1,
                "solidarity_price_harvest_shares": 0.0,
            },
        )

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
