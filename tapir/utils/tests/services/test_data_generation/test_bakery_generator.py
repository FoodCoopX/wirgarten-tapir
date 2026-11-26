import datetime
from unittest.mock import patch

from django.test import override_settings

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    Bread,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    Ingredient,
    PreferredBread,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.bakery.services.direct_order_limit_service import DirectOrderLimitService
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.pickup_locations.tests.factories import (
    create_pickup_location_with_opening_times,
)
from tapir.utils.services.test_data_generation.bakery_generator import BakeryGenerator
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.utils.services.test_data_generation.product_generator import (
    BREAD_PRODUCT_TYPE_NAME,
    ProductGenerator,
)
from tapir.wirgarten.models import (
    Product,
    ProductType,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@override_settings(BAKERY_ENABLED=True)
class TestBakeryGenerator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._create_growing_periods()

    @staticmethod
    def _create_growing_periods():
        this_year = datetime.date.today().year
        for year in [this_year - 1, this_year, this_year + 1]:
            GrowingPeriodFactory.create(
                start_date=datetime.date(year, 1, 1),
                end_date=datetime.date(year, 12, 31),
            )

    def test_generateMasterdata_createsBreadsWithStoveLayers(self):
        BakeryGenerator.generate_masterdata()

        self.assertTrue(Bread.objects.exists())
        for bread in Bread.objects.all():
            self.assertTrue(bread.pieces_per_stove_layer)
            self.assertGreater(bread.weight, 0)

    def test_generateMasterdata_default_givesEveryBreadAMax(self):
        BakeryGenerator.generate_masterdata()

        self.assertFalse(Bread.objects.filter(max_pieces__isnull=True).exists())

    def test_generateProductsBakery_createsTheWeeklyBreadShare(self):
        ProductGenerator.generate_products_bakery()

        product_type = ProductType.objects.get(name=BREAD_PRODUCT_TYPE_NAME)
        self.assertEqual(product_type.delivery_cycle, "weekly")
        self.assertTrue(product_type.must_be_subscribed_to)
        self.assertEqual(product_type.product_set.count(), 3)

    def test_generateWeekData_coversEveryStationsOwnDeliveryDay(self):
        thursday_only = create_pickup_location_with_opening_times(
            [4, 5], name="Warenhaus"
        )
        also_monday = create_pickup_location_with_opening_times(
            [4, 5, 6, 1], name="Hofpunkt"
        )
        BakeryGenerator.generate_masterdata()

        BakeryGenerator.generate_week_data()

        cache = {}
        expected = {
            PickupLocationDeliveryDayService.get_delivery_day(
                pickup_location_id=pickup_location.id, cache=cache
            )
            for pickup_location in [thursday_only, also_monday]
        }
        self.assertEqual(expected, {4, 1})
        self.assertEqual(
            set(
                AvailableBreadsForDeliveryDay.objects.values_list(
                    "delivery_day", flat=True
                )
            ),
            expected,
        )

    def _create_bread_member(self, pickup_location, quantity: int):
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=datetime.date(2000, 1, 1),
        )
        year, week = BakeryGenerator.get_weeks_with_data()[0]
        SubscriptionFactory.create(
            member=member,
            product=Product.objects.filter(type__name=BREAD_PRODUCT_TYPE_NAME).first(),
            quantity=quantity,
            start_date=datetime.date.fromisocalendar(year, week, 1),
            end_date=datetime.date.fromisocalendar(year, week, 7),
        )
        return member

    def test_generateWeekData_assignedBreadsAreAvailableAtTheMembersStation(self):
        pickup_location = create_pickup_location_with_opening_times(
            [4], name="Hofladen"
        )
        BakeryGenerator.generate_masterdata()
        ProductGenerator.generate_products_bakery()
        self._create_bread_member(pickup_location, quantity=2)

        BakeryGenerator.generate_week_data()

        self.assertTrue(BreadDelivery.objects.exists())
        cache = {}
        for delivery in BreadDelivery.objects.select_related(
            "subscription__member", "bread"
        ):
            if delivery.bread is None:
                continue
            self.assertTrue(
                AvailableBreadsForDeliveryDay.objects.filter(
                    year=delivery.year,
                    delivery_week=delivery.delivery_week,
                    delivery_day=PickupLocationDeliveryDayService.get_delivery_day(
                        pickup_location_id=BreadDeliveryContextService.get_pickup_location_id(
                            delivery, cache=cache
                        ),
                        cache=cache,
                    ),
                    bread=delivery.bread,
                ).exists(),
            )

    def test_generateWeekData_moreSlotsThanTheLimitsAllow_staysWithinTheLimits(self):
        pickup_location = create_pickup_location_with_opening_times(
            [4], name="Hofladen"
        )
        BakeryGenerator.generate_masterdata()
        Bread.objects.update(max_pieces=1)
        ProductGenerator.generate_products_bakery()
        for _ in range(4):
            self._create_bread_member(pickup_location, quantity=3)

        BakeryGenerator.generate_week_data()

        year, week = BakeryGenerator.get_weeks_with_data()[0]
        limits = DirectOrderLimitService.get_limits_for_day(
            year=year, delivery_week=week, delivery_day=4, cache={}
        )
        self.assertEqual(
            {bread.ordered for bread in limits.breads.values()} - {0, 1}, set()
        )
        self.assertTrue(
            BreadDelivery.objects.filter(
                year=year, delivery_week=week, bread__isnull=True
            ).exists()
        )

    @patch.object(BakeryGenerator, "SHARE_OF_MEMBERS_WITH_PREFERENCES", 1.0)
    def test_generateWeekData_givesMembersFavourites(self):
        pickup_location = create_pickup_location_with_opening_times(
            [4], name="Hofladen"
        )
        BakeryGenerator.generate_masterdata()
        ProductGenerator.generate_products_bakery()

        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=datetime.date(2000, 1, 1),
        )
        year, week = BakeryGenerator.get_weeks_with_data()[0]
        SubscriptionFactory.create(
            member=member,
            product=Product.objects.filter(type__name=BREAD_PRODUCT_TYPE_NAME).first(),
            quantity=1,
            start_date=datetime.date.fromisocalendar(year, week, 1),
            end_date=datetime.date.fromisocalendar(year, week, 7),
        )

        BakeryGenerator.generate_week_data()

        preferred = PreferredBread.objects.get(member=member)
        self.assertGreaterEqual(preferred.breads.count(), 1)

    def test_clear_removesBakeryMasterdata(self):
        create_pickup_location_with_opening_times([4], name="Hofladen")
        BakeryGenerator.generate_masterdata()
        BakeryGenerator.generate_week_data()

        DataGenerator.clear()

        for model in [
            Bread,
            BreadLabel,
            Ingredient,
            BreadContent,
            AvailableBreadsForDeliveryDay,
            BreadDelivery,
        ]:
            self.assertFalse(
                model.objects.exists(), f"{model.__name__} survived clear()"
            )

    def test_clear_canBeFollowedByASecondGeneration(self):
        # Bread.name and Ingredient.name are unique.
        create_pickup_location_with_opening_times([4], name="Hofladen")
        BakeryGenerator.generate_masterdata()
        DataGenerator.clear()

        self._create_growing_periods()
        BakeryGenerator.generate_masterdata()

        self.assertTrue(Bread.objects.exists())
