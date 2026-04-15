import datetime

from tapir.pickup_locations.services.pickup_location_column_provider import (
    PickupLocationColumnProvider,
)
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS
from tapir.wirgarten.models import MemberPickupLocation
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PickupLocationFactory,
    SubscriptionFactory,
    ProductTypeFactory,
    ProductFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPickupLocationColumnProvider(TapirIntegrationTest):
    maxDiff = 2000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getValuePickupLocationName_default_returnsLocationName(self):
        pickup_location = PickupLocationFactory.build(name="Test Location")

        result = PickupLocationColumnProvider.get_value_pickup_location_name(
            pickup_location, None, {}
        )

        self.assertEqual("Test Location", result)

    def test_getValuePickupLocationDeliveriesCurrentWeek_default_correctDeliveries(
        self,
    ):
        target_pickup_location = PickupLocationFactory.create()
        other_pickup_location = PickupLocationFactory.create()

        product_type_weekly = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        product = ProductFactory.create(type=product_type_weekly)
        ProductPriceFactory.create(
            product=product, valid_from=datetime.date(year=2009, month=1, day=1)
        )
        subscription_valid_1 = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2009, month=1, day=1),
            product=product,
            member__last_name="Roger",
        )
        MemberPickupLocation.objects.create(
            member=subscription_valid_1.member,
            valid_from=datetime.date(year=2009, month=1, day=1),
            pickup_location=target_pickup_location,
        )
        subscription_valid_2 = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2009, month=1, day=1),
            product=product,
            member__last_name="Albert",
        )
        MemberPickupLocation.objects.create(
            member=subscription_valid_2.member,
            valid_from=datetime.date(year=2009, month=1, day=1),
            pickup_location=target_pickup_location,
        )

        subscription_at_other_location = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2009, month=1, day=1), product=product
        )
        MemberPickupLocation.objects.create(
            member=subscription_at_other_location.member,
            valid_from=datetime.date(year=2009, month=1, day=1),
            pickup_location=other_pickup_location,
        )
        subscription_not_delivered = SubscriptionFactory.create(
            period__start_date=datetime.date(year=2009, month=1, day=1),
            product__type__delivery_cycle=EVEN_WEEKS[0],  # given week is week 19
        )
        ProductPriceFactory.create(
            product=subscription_not_delivered.product,
            valid_from=datetime.date(year=2009, month=1, day=1),
        )
        MemberPickupLocation.objects.create(
            member=subscription_not_delivered.member,
            valid_from=datetime.date(year=2009, month=1, day=1),
            pickup_location=target_pickup_location,
        )

        result = PickupLocationColumnProvider.get_value_pickup_location_deliveries_current_week(
            target_pickup_location, datetime.datetime(year=2009, month=5, day=7), {}
        )

        self.assertEqual(
            [
                {
                    "last_name": "Albert",
                    "first_name": subscription_valid_2.member.first_name,
                    "phone_number": subscription_valid_2.member.phone_number,
                    "email": subscription_valid_2.member.email,
                    "product_name": product.name,
                    "product_type_name": product_type_weekly.name,
                    "quantity": subscription_valid_2.quantity,
                },
                {
                    "last_name": "Roger",
                    "first_name": subscription_valid_1.member.first_name,
                    "phone_number": subscription_valid_1.member.phone_number,
                    "email": subscription_valid_1.member.email,
                    "product_name": product.name,
                    "product_type_name": product_type_weekly.name,
                    "quantity": subscription_valid_1.quantity,
                },
            ],
            result,
        )
