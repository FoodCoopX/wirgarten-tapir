import datetime

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.wirgarten.models import (
    ProductType,
    GrowingPeriod,
    Product,
    Subscription,
    PickupLocation,
)
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    ProductPriceFactory,
    MemberPickupLocationFactory,
    ProductCapacityFactory,
    PickupLocationCapabilityFactory,
    MemberFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import (
    TapirIntegrationTest,
    mock_timezone,
)


class TestAdditionalProductForm(TapirIntegrationTest):
    def setUp(self):
        ParameterDefinitions().import_definitions()
        now = datetime.datetime(year=2023, month=6, day=12)
        mock_timezone(self, now)

    def create_member_and_login(self):
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(member=member)
        self.client.force_login(member)

        return member

    def create_additional_product(self):
        base_product = ProductFactory.create()
        base_product_type = ProductType.objects.get()
        GrowingPeriodFactory.create()
        TapirParameter.objects.filter(key=Parameter.COOP_BASE_PRODUCT_TYPE).update(
            value=base_product_type.id
        )
        additional_product: Product = ProductFactory.create()
        ProductPriceFactory.create(product=additional_product)
        ProductCapacityFactory.create(
            period=GrowingPeriod.objects.get(),
            product_type=additional_product.type,
            capacity=1000,
        )
        PickupLocationCapabilityFactory.create(
            product_type=additional_product.type,
            max_capacity=1000,
            pickup_location=PickupLocation.objects.get(),
        )

        return [base_product, additional_product]

    def try_to_order_additional_product(self, member, additional_product):
        url = (
            f"{reverse('wirgarten:member_add_subscription', args=[member.id])}"
            f"?productType={additional_product.type.name}"
        )
        data = {
            "growing_period": GrowingPeriod.objects.get().id,
            f"{additional_product.type.id}_{additional_product.name}": 3,
        }

        return self.client.post(
            url,
            data=data,
        )

    def test_additionalProductForm_memberHasBaseProductSubscriptionInSameGrowingPeriod_subscriptionCreated(
        self,
    ):
        member = self.create_member_and_login()
        [base_product, additional_product] = self.create_additional_product()
        SubscriptionFactory.create(
            member=member, period=GrowingPeriod.objects.get(), product=base_product
        )

        response = self.try_to_order_additional_product(member, additional_product)

        self.assertStatusCode(response, 200)
        new_subscription = Subscription.objects.filter(
            product=additional_product.id
        ).first()
        self.assertIsNotNone(new_subscription)
        self.assertEqual(new_subscription.quantity, 3)

    def test_additionalProductForm_memberDoesntHaveBaseProductSubscriptionInSameGrowingPeriod_subscriptionNotCreated(
        self,
    ):
        member = self.create_member_and_login()
        [_, additional_product] = self.create_additional_product()

        response = self.try_to_order_additional_product(member, additional_product)

        self.assertStatusCode(response, 200)
        new_subscription = Subscription.objects.filter(
            product=additional_product.id
        ).first()
        self.assertIsNone(new_subscription)
