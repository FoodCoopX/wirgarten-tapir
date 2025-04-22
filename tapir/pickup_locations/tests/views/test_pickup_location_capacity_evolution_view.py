import datetime

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.config import PICKING_MODE_BASKET, PICKING_MODE_SHARE
from tapir.pickup_locations.models import (
    PickupLocationBasketCapacity,
    ProductBasketSizeEquivalence,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import Member, PickupLocationCapability, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
    GrowingPeriodFactory,
    MemberPickupLocationFactory,
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestPickupLocationCapacityEvolutionView(TapirIntegrationTest):
    maxDiff = 2000

    def setUp(self) -> None:
        self.now = mock_timezone(self, datetime.datetime(year=2023, month=2, day=1))

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_pickupLocationCapacityEvolutionView_loggedInAsNormalUser_returns403(
        self,
    ):
        member = MemberFactory.create()
        self.client.force_login(member)
        pickup_location = PickupLocationFactory.create()

        url = reverse("pickup_locations:pickup_location_capacity_evolution")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 403)

    def test_pickupLocationCapacityEvolutionView_pickingModeBasket_returnsCorrectData(
        self,
    ):
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_BASKET
        )
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_BASKET_SIZES).update(
            value="small;medium;"
        )

        pickup_location = PickupLocationFactory.create()
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="small", pickup_location=pickup_location, capacity=None
        )
        PickupLocationBasketCapacity.objects.create(
            basket_size_name="medium", pickup_location=pickup_location, capacity=10
        )

        product_s = ProductFactory.create(name="S")
        product_m = ProductFactory.create(name="M", type=product_s.type)
        product_l = ProductFactory.create(name="L", type=product_s.type)

        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="small", product=product_s, quantity=1
        )
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="medium", product=product_s, quantity=0
        )
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="small", product=product_m, quantity=0
        )
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="medium", product=product_m, quantity=1
        )
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="small", product=product_l, quantity=1
        )
        ProductBasketSizeEquivalence.objects.create(
            basket_size_name="medium", product=product_l, quantity=1
        )

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        SubscriptionFactory.create(
            period=growing_period,
            product=product_s,
            quantity=2,
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        SubscriptionFactory.create(
            period=growing_period,
            product=product_l,
            quantity=3,
            start_date=datetime.date(year=2023, month=3, day=1),
            end_date=datetime.date(year=2023, month=6, day=5),
        )
        SubscriptionFactory.create(
            period=growing_period,
            product=product_m,
            quantity=1,
            start_date=datetime.date(year=2023, month=7, day=27),
            end_date=datetime.date(year=2023, month=12, day=31),
        )

        for member in Member.objects.all():
            MemberPickupLocationFactory.create(
                pickup_location=pickup_location,
                member=member,
                valid_from=growing_period.start_date,
            )

        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        url = reverse("pickup_locations:pickup_location_capacity_evolution")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 200)

        response_content = response.json()
        self.assertEqual(
            {
                "table_headers": ["small", "medium"],
                "data_points": [
                    {"date": "2023-02-01", "values": ["Unbegrenzt", "7.00"]},
                    {
                        "date": "2023-06-12",  # after the 3xl subscription is finished
                        "values": ["Unbegrenzt", "9.00"],
                    },
                ],
            },
            response_content,
        )

    def test_pickupLocationCapacityEvolutionView_pickingModeShares_returnsCorrectData(
        self,
    ):
        TapirParameter.objects.filter(key=ParameterKeys.PICKING_MODE).update(
            value=PICKING_MODE_SHARE
        )

        pickup_location = PickupLocationFactory.create()

        product_s = ProductFactory.create(name="S", type__name="Ernteanteile")
        product_m = ProductFactory.create(name="M", type=product_s.type)
        product_l = ProductFactory.create(name="L", type=product_s.type)
        product_half = ProductFactory.create(name="Halbe", type__name="Hühneranteile")
        product_full = ProductFactory.create(name="Ganze", type=product_half.type)

        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )

        ProductPriceFactory.create(
            product=product_s, size=0.66, valid_from=growing_period.start_date
        )
        ProductPriceFactory.create(
            product=product_m, size=1, valid_from=growing_period.start_date
        )
        ProductPriceFactory.create(
            product=product_l, size=1.33, valid_from=growing_period.start_date
        )
        ProductPriceFactory.create(
            product=product_half, size=0.5, valid_from=growing_period.start_date
        )
        ProductPriceFactory.create(
            product=product_full, size=1, valid_from=growing_period.start_date
        )

        SubscriptionFactory.create(
            period=growing_period,
            product=product_s,
            quantity=2,
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        SubscriptionFactory.create(
            period=growing_period,
            product=product_l,
            quantity=3,
            start_date=datetime.date(year=2023, month=3, day=1),
            end_date=datetime.date(year=2023, month=6, day=5),
        )
        SubscriptionFactory.create(
            period=growing_period,
            product=product_m,
            quantity=1,
            start_date=datetime.date(year=2023, month=7, day=27),
            end_date=datetime.date(year=2023, month=12, day=31),
        )
        SubscriptionFactory.create(
            period=growing_period,
            product=product_half,
            quantity=2,
            start_date=datetime.date(year=2023, month=7, day=27),
            end_date=datetime.date(year=2023, month=12, day=31),
        )

        PickupLocationCapability.objects.create(
            product_type=product_s.type,
            pickup_location=pickup_location,
            max_capacity=10,
        )
        PickupLocationCapability.objects.create(
            product_type=product_half.type,
            pickup_location=pickup_location,
            max_capacity=None,
        )

        for member in Member.objects.all():
            MemberPickupLocationFactory.create(
                pickup_location=pickup_location,
                member=member,
                valid_from=growing_period.start_date,
            )

        ProductType.objects.update(delivery_cycle=WEEKLY[0])

        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        url = reverse("pickup_locations:pickup_location_capacity_evolution")
        response = self.client.get(f"{url}?pickup_location_id={pickup_location.id}")

        self.assertEqual(response.status_code, 200)

        response_content = response.json()
        self.assertEqual(
            {
                "table_headers": ["Ernteanteile", "Hühneranteile"],
                "data_points": [
                    {
                        # before the 3xl subscription is finished
                        # usage: 3xL + 2xS = 3x1.33 + 2x0.66 = 5.31, free: 10-5.31 = 4.69
                        "date": "2023-02-01",
                        "values": ["4.69", "Unbegrenzt"],
                    },
                    {
                        # after the 3xl subscription is finished
                        # usage: 1xM + 2xS = 2.32, free: 10-2.32 = 7.68
                        "date": "2023-06-12",
                        "values": ["7.68", "Unbegrenzt"],
                    },
                ],
            },
            response_content,
        )
