import datetime

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import (
    GrowingPeriod,
    Member,
    ProductCapacity,
    MemberPickupLocation,
    Subscription,
    ProductType,
    Product,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import configure_mail_module
from tapir.wirgarten.tests.factories import (
    ProductCapacityFactory,
    ProductPriceFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationCapabilityFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMemberAddSubscription(TapirIntegrationTest):
    def setUp(self):
        now = datetime.datetime(year=2023, month=6, day=12)
        mock_timezone(self, now)
        configure_mail_module()

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        product_capacity_base: ProductCapacity = ProductCapacityFactory.create(
            capacity=100,
            product_type__name="Ernteanteile",
            product_type__delivery_cycle=WEEKLY[0],
        )
        product_capacity_additional: ProductCapacity = ProductCapacityFactory.create(
            capacity=100,
            product_type__name="Hühneranteile",
            product_type__delivery_cycle=WEEKLY[0],
            period=GrowingPeriod.objects.get(),
        )
        growing_period = GrowingPeriod.objects.get()
        growing_period.start_date = datetime.date(year=2023, month=1, day=1)
        growing_period.end_date = datetime.date(year=2023, month=12, day=31)
        growing_period.save()

        TapirParameter.objects.filter(key=ParameterKeys.COOP_BASE_PRODUCT_TYPE).update(
            value=product_capacity_base.product_type.id
        )

        ProductPriceFactory.create(
            product__type=product_capacity_base.product_type,
            product__name="M",
            size=1,
            valid_from=datetime.date(year=2023, month=1, day=1),
        )
        ProductPriceFactory.create(
            product__type=product_capacity_additional.product_type,
            product__name="Ganz",
            size=1,
            valid_from=datetime.date(year=2023, month=1, day=1),
        )

        member = MemberFactory.create()
        member_pickup_location: MemberPickupLocation = (
            MemberPickupLocationFactory.create(member=member)
        )
        PickupLocationCapabilityFactory.create(
            product_type=product_capacity_base.product_type,
            pickup_location=member_pickup_location.pickup_location,
        )
        PickupLocationCapabilityFactory.create(
            product_type=product_capacity_additional.product_type,
            pickup_location=member_pickup_location.pickup_location,
        )

    def send_add_subscription_request(self, product_type_name: str, post_data_key: str):
        growing_period = GrowingPeriod.objects.get()
        member = Member.objects.get()
        self.client.force_login(member)
        url = f"{reverse('wirgarten:member_add_subscription', args=[member.id])}?productType={product_type_name}"
        return self.client.post(
            url,
            data={
                "growing_period": growing_period.id,
                post_data_key: 1,
                "solidarity_price_choice": 0.0,
            },
        )

    def test_memberAddSubscription_baseProductAndAutoRenewOff_subscriptionNoticePeriodSetToNone(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=False)

        self.send_add_subscription_request(
            product_type_name="Ernteanteile", post_data_key="base_product_M"
        )

        self.assertEqual(1, Subscription.objects.count())
        subscription = Subscription.objects.get()
        self.assertIsNone(subscription.notice_period_duration)

    def test_memberAddSubscription_baseProductAndAutoRenewOn_subscriptionNoticePeriodSetToCorrectValue(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=2)

        self.send_add_subscription_request(
            product_type_name="Ernteanteile", post_data_key="base_product_M"
        )

        self.assertEqual(1, Subscription.objects.count())
        subscription = Subscription.objects.get()
        self.assertEqual(2, subscription.notice_period_duration)

    def test_memberAddSubscription_additionalProductAndAutoRenewOff_subscriptionNoticePeriodSetToNone(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=False)
        base_product_subscription = SubscriptionFactory.create(
            member=Member.objects.get(),
            product=Product.objects.get(name="M"),
            period=GrowingPeriod.objects.get(),
        )

        product_type = ProductType.objects.get(name="Hühneranteile")
        product = Product.objects.get(type=product_type)
        post_data_key = f"{product_type.id}_{product.name}"
        self.send_add_subscription_request(
            product_type_name="Hühneranteile", post_data_key=post_data_key
        )

        self.assertEqual(2, Subscription.objects.count())
        subscription = Subscription.objects.exclude(
            id=base_product_subscription.id
        ).get()
        self.assertIsNone(subscription.notice_period_duration)

    def test_memberAddSubscription_additionalProductAndAutoRenewOn_subscriptionNoticePeriodSetToCorrectValue(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_DEFAULT_NOTICE_PERIOD
        ).update(value=2)
        base_product_subscription = SubscriptionFactory.create(
            member=Member.objects.get(),
            product=Product.objects.get(name="M"),
            period=GrowingPeriod.objects.get(),
        )

        product_type = ProductType.objects.get(name="Hühneranteile")
        product = Product.objects.get(type=product_type)
        post_data_key = f"{product_type.id}_{product.name}"
        self.send_add_subscription_request(
            product_type_name="Hühneranteile", post_data_key=post_data_key
        )

        self.assertEqual(2, Subscription.objects.count())
        subscription = Subscription.objects.exclude(
            id=base_product_subscription.id
        ).get()
        self.assertEqual(2, subscription.notice_period_duration)
