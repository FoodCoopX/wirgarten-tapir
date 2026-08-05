import datetime

from tapir.pickup_locations.config import PICKING_MODE_SHARE, PICKING_MODE_BASKET
from tapir.pickup_locations.models import ProductBasketSizeEquivalence
from tapir.pickup_locations.services.location_route_column_provider import (
    LocationRouteColumnProvider,
)
from tapir.wirgarten.constants import WEEKLY, NO_DELIVERY
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    LocationRouteFactory,
    PickupLocationFactory,
    SubscriptionFactory,
    MemberFactory,
    GrowingPeriodFactory,
    MemberPickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestLocationRouteColumnProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getValueRouteName_default_returnsName(self):
        route = LocationRouteFactory.build(name="test_name")

        result = LocationRouteColumnProvider.get_value_route_name(route, None, None)

        self.assertEqual("test_name", result)

    def test_getValueRouteName_routeIsNone_returnsEmptyString(self):
        result = LocationRouteColumnProvider.get_value_route_name(None, None, None)

        self.assertEqual("", result)

    def test_getValuePickupLocation_default_returnsCorrectBaseData(self):
        route = LocationRouteFactory.create()
        location_a = PickupLocationFactory.create(
            name="pl_a",
            street="street_a",
            street_2="street_2_a",
            postcode="postcode_a",
            city="city_a",
            route_info="route_info_a",
            location_route=route,
        )
        location_b = PickupLocationFactory.create(
            name="pl_b",
            street="street_b",
            street_2="street_2_b",
            postcode="postcode_b",
            city="city_b",
            route_info="route_info_b",
            location_route=route,
        )
        PickupLocationFactory.create(location_route=LocationRouteFactory.create())
        PickupLocationFactory.create(location_route=None)

        result = LocationRouteColumnProvider.get_value_pickup_locations(
            route=route,
            reference_datetime=datetime.datetime(
                year=2026, month=7, day=29, hour=12, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertEqual(2, len(result))

        data_location_a = result[0]
        self.assertEqual(location_a.id, data_location_a["id"])
        self.assertEqual("pl_a", data_location_a["name"])
        self.assertEqual("street_a", data_location_a["street"])
        self.assertEqual("street_2_a", data_location_a["street_2"])
        self.assertEqual("postcode_a", data_location_a["postcode"])
        self.assertEqual("city_a", data_location_a["city"])
        self.assertEqual("route_info_a", data_location_a["route_info"])
        self.assertEqual(31, data_location_a["calendar_week"])

        data_location_b = result[1]
        self.assertEqual(location_b.id, data_location_b["id"])
        self.assertEqual("pl_b", data_location_b["name"])
        self.assertEqual("street_b", data_location_b["street"])
        self.assertEqual("street_2_b", data_location_b["street_2"])
        self.assertEqual("postcode_b", data_location_b["postcode"])
        self.assertEqual("city_b", data_location_b["city"])
        self.assertEqual("route_info_b", data_location_b["route_info"])
        self.assertEqual(31, data_location_b["calendar_week"])

    def test_getValuePickupLocation_pickingModeShare_returnsCorrectSubscriptionData(
        self,
    ):
        self._set_parameter(key=ParameterKeys.PICKING_MODE, value=PICKING_MODE_SHARE)

        pickup_location = PickupLocationFactory.create()

        member_1 = MemberFactory.create(
            member_no=123, first_name="John", last_name="Xi"
        )
        period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1)
        )
        MemberPickupLocationFactory.create(
            member=member_1,
            pickup_location=pickup_location,
            valid_from=period.start_date,
        )

        subscription_1 = SubscriptionFactory.create(
            quantity=2,
            product__type__delivery_cycle=WEEKLY[0],
            product__type__order_in_bestellwizard=1,
            member=member_1,
            period=period,
        )
        subscription_2 = SubscriptionFactory.create(
            member=member_1,
            quantity=1,
            product__type__delivery_cycle=WEEKLY[0],
            product__type__order_in_bestellwizard=2,
            period=period,
        )
        member_2 = MemberFactory.create(
            member_no=456, first_name="Jane", last_name="Mustermensch"
        )
        MemberPickupLocationFactory.create(
            member=member_2,
            pickup_location=pickup_location,
            valid_from=period.start_date,
        )
        SubscriptionFactory.create(
            quantity=3,
            product=subscription_1.product,
            member=member_2,
            period=period,
        )
        undelivered_subscription = SubscriptionFactory.create(
            quantity=7,
            product__type__delivery_cycle=NO_DELIVERY[0],
            period=period,
        )

        result = LocationRouteColumnProvider.get_value_pickup_locations(
            route=None,
            reference_datetime=datetime.datetime(
                year=2026, month=7, day=29, hour=12, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertEqual(1, len(result))
        data = result[0]
        self.assertEqual(
            [subscription_1.product.id, subscription_2.product.id], data["headers"]
        )
        self.assertEqual(
            {
                subscription_1.product.id: subscription_1.product.name,
                subscription_2.product.id: subscription_2.product.name,
                undelivered_subscription.product.id: undelivered_subscription.product.name,
            },
            data["product_name_by_id"],
        )
        self.assertTrue(data["convert_headers"])
        self.assertEqual(
            {
                subscription_1.product.id: 5,
                subscription_2.product.id: 1,
            },
            data["global_values"],
        )
        self.assertEqual(
            [
                {
                    "member_no": 456,
                    "first_name": "Jane",
                    "last_name": "Mu",
                    "member_values": {
                        subscription_1.product.id: 3,
                        subscription_2.product.id: 0,
                    },
                },
                {
                    "member_no": 123,
                    "first_name": "John",
                    "last_name": "Xi",
                    "member_values": {
                        subscription_1.product.id: 2,
                        subscription_2.product.id: 1,
                    },
                },
            ],
            data["members"],
        )

    def test_getValuePickupLocation_pickingModeBasket_returnsCorrectSubscriptionData(
        self,
    ):
        self._set_parameter(key=ParameterKeys.PICKING_MODE, value=PICKING_MODE_BASKET)
        self._set_parameter(
            key=ParameterKeys.PICKING_BASKET_SIZES, value="small;normal"
        )

        pickup_location = PickupLocationFactory.create()
        period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1)
        )
        member_1 = MemberFactory.create(
            member_no=123, first_name="John", last_name="Xi"
        )
        MemberPickupLocationFactory.create(
            member=member_1,
            pickup_location=pickup_location,
            valid_from=period.start_date,
        )

        subscription_1 = SubscriptionFactory.create(
            quantity=2,
            product__type__delivery_cycle=WEEKLY[0],
            product__type__order_in_bestellwizard=1,
            member=member_1,
            period=period,
        )
        subscription_2 = SubscriptionFactory.create(
            member=member_1,
            quantity=1,
            product__type__delivery_cycle=WEEKLY[0],
            product__type__order_in_bestellwizard=2,
            period=period,
        )
        member_2 = MemberFactory.create(
            member_no=456, first_name="Jane", last_name="Mustermensch"
        )
        MemberPickupLocationFactory.create(
            member=member_2,
            pickup_location=pickup_location,
            valid_from=period.start_date,
        )
        SubscriptionFactory.create(
            quantity=3,
            product=subscription_1.product,
            member=member_2,
            period=period,
        )
        SubscriptionFactory.create(
            quantity=7,
            product__type__delivery_cycle=NO_DELIVERY[0],
            period=period,
        )

        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="small", product=subscription_1.product, quantity=1
        )
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="normal", product=subscription_1.product, quantity=1
        )
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="small", product=subscription_2.product, quantity=1
        )

        result = LocationRouteColumnProvider.get_value_pickup_locations(
            route=None,
            reference_datetime=datetime.datetime(
                year=2026, month=7, day=29, hour=12, tzinfo=datetime.timezone.utc
            ),
            cache={},
        )

        self.assertEqual(1, len(result))
        data = result[0]
        self.assertEqual(["small", "normal"], data["headers"])
        self.assertFalse(data["convert_headers"])
        self.assertEqual(
            {
                "small": 6,
                "normal": 5,
            },
            data["global_values"],
        )
        self.assertEqual(
            [
                {
                    "member_no": 456,
                    "first_name": "Jane",
                    "last_name": "Mu",
                    "member_values": {
                        "small": 3,
                        "normal": 3,
                    },
                },
                {
                    "member_no": 123,
                    "first_name": "John",
                    "last_name": "Xi",
                    "member_values": {
                        "small": 3,
                        "normal": 2,
                    },
                },
            ],
            data["members"],
        )
