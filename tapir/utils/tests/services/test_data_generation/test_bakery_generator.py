import datetime

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    Bread,
    BreadCapacityPickupLocation,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    Ingredient,
    PreferredBread,
)
from tapir.bakery.services.bread_delivery_context_service import (
    BreadDeliveryContextService,
)
from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.utils.services.test_data_generation.bakery_generator import (
    BREAD_PRODUCT_TYPE_NAME,
    BakeryGenerator,
)
from tapir.utils.services.test_data_generation.data_generator import DataGenerator
from tapir.wirgarten.models import (
    PickupLocationOpeningTime,
    Product,
    ProductType,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak


class TestBakeryGenerator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        set_bypass_keycloak()
        self._create_growing_periods()

    @staticmethod
    def _create_growing_periods():
        # Three of them, as generate_all makes: the product prices are dated
        # off the first and the last, so a single period collides on itself.
        this_year = datetime.date.today().year
        for year in [this_year - 1, this_year, this_year + 1]:
            GrowingPeriodFactory.create(
                start_date=datetime.date(year, 1, 1),
                end_date=datetime.date(year, 12, 31),
            )

    @staticmethod
    def _pickup_location_with_days(name, days):
        pickup_location = PickupLocationFactory.create(name=name)
        for day_of_week in days:
            PickupLocationOpeningTime.objects.create(
                pickup_location=pickup_location,
                day_of_week=day_of_week,
                open_time=datetime.time(8),
                close_time=datetime.time(18),
            )
        return pickup_location

    # ── masterdata ────────────────────────────────────────────────────

    def test_generateMasterdata_createsBreadsWithStoveLayers(self):
        BakeryGenerator.generate_masterdata()

        self.assertTrue(Bread.objects.exists())
        for bread in Bread.objects.all():
            # Without pieces_per_stove_layer the solver aborts the run.
            self.assertTrue(bread.pieces_per_stove_layer)
            self.assertGreater(bread.weight, 0)

    def test_generateMasterdata_switchesTheBakeryOn(self):
        BakeryGenerator.generate_masterdata()

        self.assertEqual(
            TapirParameter.objects.get(key=ParameterKeys.BAKERY_A_ENABLED).value,
            "True",
        )

    def test_generateMasterdata_breadShareIsAWeeklyBreadProductType(self):
        BakeryGenerator.generate_masterdata()

        product_type = ProductType.objects.get(name=BREAD_PRODUCT_TYPE_NAME)
        self.assertTrue(product_type.is_bread)
        self.assertEqual(product_type.delivery_cycle, "weekly")
        # Share sizes, not bread varieties: the variety is chosen per week.
        self.assertEqual(product_type.product_set.count(), 3)

    # ── week data ─────────────────────────────────────────────────────

    def test_generateWeekData_capacityForEveryStationWeekAndBread(self):
        self._pickup_location_with_days("Hofladen", [4])
        BakeryGenerator.generate_masterdata()

        BakeryGenerator.generate_week_data()

        self.assertEqual(
            BreadCapacityPickupLocation.objects.count(),
            Bread.objects.count() * BakeryGenerator.NUMBER_OF_WEEKS_WITH_DATA,
        )

    def test_generateWeekData_coversEveryStationsOwnDeliveryDay(self):
        # The Hofpunkt case: it opens Monday morning as well as Thursday, so
        # its delivery day is Monday. Generating for Thursday alone would make
        # every delivery there invisible to the solver.
        thursday_only = self._pickup_location_with_days("Warenhaus", [4, 5])
        also_monday = self._pickup_location_with_days("Hofpunkt", [4, 5, 6, 1])
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

    def test_generateWeekData_assignedBreadsAreAvailableAtTheMembersStation(self):
        # The one non-negotiable ordering edge: capacities before assignment.
        pickup_location = self._pickup_location_with_days("Hofladen", [4])
        BakeryGenerator.generate_masterdata()

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
            quantity=2,
            start_date=datetime.date.fromisocalendar(year, week, 1),
            end_date=datetime.date.fromisocalendar(year, week, 7),
        )
        self.assertTrue(BreadDelivery.objects.exists())

        BakeryGenerator.generate_week_data()

        cache = {}
        for delivery in BreadDelivery.objects.select_related(
            "subscription__member", "bread"
        ):
            if delivery.bread is None:
                continue
            self.assertTrue(
                BreadCapacityPickupLocation.objects.filter(
                    year=delivery.year,
                    delivery_week=delivery.delivery_week,
                    bread=delivery.bread,
                    pickup_location_id=BreadDeliveryContextService.get_pickup_location_id(
                        delivery, cache=cache
                    ),
                ).exists(),
                "a chosen bread must have a capacity row at that station",
            )

    def test_generateWeekData_givesMembersFavourites(self):
        # Without these the solver reports "no preference data found" and its
        # whole reason for existing is never exercised on test data.
        pickup_location = self._pickup_location_with_days("Hofladen", [4])
        BakeryGenerator.generate_masterdata()

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

        BakeryGenerator.SHARE_OF_MEMBERS_WITH_PREFERENCES = 1.0
        try:
            BakeryGenerator.generate_week_data()
        finally:
            BakeryGenerator.SHARE_OF_MEMBERS_WITH_PREFERENCES = 0.6

        preferred = PreferredBread.objects.get(member=member)
        self.assertGreaterEqual(preferred.breads.count(), 1)

    # ── clear ─────────────────────────────────────────────────────────

    def test_clear_removesBakeryMasterdata(self):
        self._pickup_location_with_days("Hofladen", [4])
        BakeryGenerator.generate_masterdata()
        BakeryGenerator.generate_week_data()

        DataGenerator.clear()

        for model in [
            Bread,
            BreadLabel,
            Ingredient,
            BreadContent,
            BreadCapacityPickupLocation,
            AvailableBreadsForDeliveryDay,
            BreadDelivery,
        ]:
            self.assertFalse(
                model.objects.exists(), f"{model.__name__} survived clear()"
            )

    def test_clear_canBeFollowedByASecondGeneration(self):
        # Bread.name and Ingredient.name are unique, so clear() has to remove
        # them or a second --reset_all fails with an IntegrityError.
        self._pickup_location_with_days("Hofladen", [4])
        BakeryGenerator.generate_masterdata()
        DataGenerator.clear()

        self._create_growing_periods()
        BakeryGenerator.generate_masterdata()

        self.assertTrue(Bread.objects.exists())
