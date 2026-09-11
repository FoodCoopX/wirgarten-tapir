import datetime
import random

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
from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.utils.services.test_data_generation.product_generator import ProductGenerator
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.models import (
    GrowingPeriod,
    PickupLocation,
    ProductType,
    TaxRate,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today

BREAD_PRODUCT_TYPE_NAME = "Brotanteil"

# name -> (weight in grams, pieces that fit on one stove layer)
BREADS = {
    "Roggenbrot": (1000, [10, 11, 12]),
    "Dinkelkruste": (750, [12, 14]),
    "Vollkornbrot": (1000, [10, 12]),
    "Sauerteigbrot": (1250, [8, 9]),
    "Weizenmischbrot": (750, [12, 14, 16]),
    "Kürbiskernbrot": (500, [16, 18]),
}

LABELS = ["Vollkorn", "Sauerteig", "Dinkel", "Roggen"]

# ingredient -> is_organic
INGREDIENTS = {
    "Roggenmehl": True,
    "Weizenmehl": True,
    "Dinkelmehl": True,
    "Wasser": False,
    "Salz": False,
    "Sauerteig": True,
    "Kürbiskerne": True,
}


class BakeryGenerator:
    """
    Test data for the bakery, layered on top of an organization's data.

    Split in two because of one hard ordering rule: the capacities for a
    (station, week, bread) have to exist before any bread can be put on a
    delivery - BreadDelivery.clean() rejects a bread that is not available at
    the member's station that week.
    """

    NUMBER_OF_WEEKS_WITH_DATA = 6
    CAPACITY_PER_BREAD_AND_STATION = 25
    SHARE_OF_MEMBERS_WITH_PREFERENCES = 0.6

    # ── before the members ────────────────────────────────────────────

    @classmethod
    def generate_masterdata(cls):
        """Breads, labels and ingredients, plus the bread share to subscribe to."""
        print("Creating bakery masterdata...")
        cls.generate_breads()
        cls.generate_bread_product_type()
        cls.enable_bakery_parameters()

    @classmethod
    def generate_breads(cls):
        labels = {
            name: BreadLabel.objects.create(name=name, is_active=True)
            for name in LABELS
        }
        ingredients = {
            name: Ingredient.objects.create(
                name=name, is_organic=is_organic, is_active=True
            )
            for name, is_organic in INGREDIENTS.items()
        }

        for name, (weight, pieces_per_stove_layer) in BREADS.items():
            bread = Bread.objects.create(
                name=name,
                weight=weight,
                description=f"{name} aus der Hofbäckerei.",
                # Without this the solver has no way to fill a stove layer and
                # aborts the run.
                pieces_per_stove_layer=pieces_per_stove_layer,
                is_active=True,
            )
            bread.labels.set(
                [label for label_name, label in labels.items() if label_name in name]
                or [labels["Sauerteig"]]
            )
            for sort_order, ingredient_name in enumerate(
                random.sample(sorted(ingredients), k=4)
            ):
                BreadContent.objects.create(
                    bread=bread,
                    ingredient=ingredients[ingredient_name],
                    amount=random.choice([50, 100, 250, 500]),
                    sort_order=sort_order,
                )

    @classmethod
    def generate_bread_product_type(cls):
        """
        The products are share sizes, not bread varieties: which bread a member
        gets is chosen per week on the BreadDelivery, and the subscription
        quantity is how many loaves a week they get.
        """
        product_type = ProductType.objects.create(
            name=BREAD_PRODUCT_TYPE_NAME,
            delivery_cycle=WEEKLY[0],
            is_affected_by_jokers=True,
            is_bread=True,
            order_in_bestellwizard=3,
        )
        TaxRate.objects.create(
            product_type=product_type,
            tax_rate=0.07,
            valid_from=GrowingPeriod.objects.order_by("start_date").first().start_date,
        )

        for name, base_price, size, base in [
            ("Ein Brot", 12.5, 1, True),
            ("Zwei Brote", 24.0, 2, False),
            ("Drei Brote", 34.5, 3, False),
        ]:
            ProductGenerator.generate_product(
                product_type=product_type,
                name=name,
                base_price=base_price,
                size=size,
                base=base,
                min_coop_shares=0,
                description_in_bestellwizard=f"{name} pro Woche",
            )

        ProductGenerator.generate_product_capacities_for_product_type(product_type)

    @classmethod
    def enable_bakery_parameters(cls):
        for key in [
            ParameterKeys.BAKERY_A_ENABLED,
            ParameterKeys.BAKERY_MEMBERS_CAN_CHOOSE_BREAD_SORTS,
            ParameterKeys.BAKERY_PSEUDONYM_ENABLED,
        ]:
            TapirParameter.objects.filter(key=key).update(value="True")

    # ── after the members ─────────────────────────────────────────────

    @classmethod
    def generate_week_data(cls):
        """Capacities and per-day availability, then some chosen breads."""
        print("Creating bakery capacities...")
        weeks = cls.get_weeks_with_data()
        cls.generate_capacities(weeks)
        cls.generate_available_breads_per_delivery_day(weeks)
        print("Choosing breads for some deliveries...")
        cls.assign_breads_to_deliveries(weeks)
        cls.generate_preferred_breads()

    @classmethod
    def get_weeks_with_data(cls) -> list[tuple[int, int]]:
        monday = get_today() - datetime.timedelta(days=get_today().weekday())
        weeks = []
        for offset in range(cls.NUMBER_OF_WEEKS_WITH_DATA):
            iso = (monday + datetime.timedelta(weeks=offset)).isocalendar()
            weeks.append((iso[0], iso[1]))
        return weeks

    @classmethod
    def generate_capacities(cls, weeks: list[tuple[int, int]]):
        breads = list(Bread.objects.all())
        capacities = []
        for pickup_location in PickupLocation.objects.all():
            for year, week in weeks:
                for bread in breads:
                    capacities.append(
                        BreadCapacityPickupLocation(
                            year=year,
                            delivery_week=week,
                            pickup_location=pickup_location,
                            bread=bread,
                            capacity=cls.CAPACITY_PER_BREAD_AND_STATION,
                        )
                    )
        BreadCapacityPickupLocation.objects.bulk_create(capacities)

    @classmethod
    def generate_available_breads_per_delivery_day(cls, weeks: list[tuple[int, int]]):
        """
        One row per weekday that any station is actually delivered on.

        Not a hard-coded day: on BIOTOP ten stations resolve to Thursday but
        Biotop-Hofpunkt resolves to Monday, because it opens Monday morning.
        Generating for Thursday alone would make every Hofpunkt delivery
        invisible to the solver - and Hofpunkt is one of the stations the user
        generator deliberately fills.
        """
        cache = {}
        delivery_days = {
            day
            for day in (
                PickupLocationDeliveryDayService.get_delivery_day(
                    pickup_location_id=pickup_location.id, cache=cache
                )
                for pickup_location in PickupLocation.objects.all()
            )
            if day is not None
        }

        breads = list(Bread.objects.all())
        available = []
        for year, week in weeks:
            for delivery_day in sorted(delivery_days):
                for bread in breads:
                    available.append(
                        AvailableBreadsForDeliveryDay(
                            year=year,
                            delivery_week=week,
                            delivery_day=delivery_day,
                            bread=bread,
                        )
                    )
        AvailableBreadsForDeliveryDay.objects.bulk_create(available)

    @classmethod
    def assign_breads_to_deliveries(cls, weeks: list[tuple[int, int]]):
        """
        Leaves roughly a third of the slots unchosen, which is what the solver
        is there to fill.
        """
        breads = list(Bread.objects.all())
        if not breads:
            return

        for year, week in weeks:
            deliveries = list(
                BreadDelivery.objects.filter(year=year, delivery_week=week)
            )
            for delivery in deliveries:
                if random.random() < 0.35:
                    continue
                delivery.bread = random.choice(breads)
            BreadDelivery.objects.bulk_update(deliveries, ["bread"])

    @classmethod
    def generate_preferred_breads(cls):
        """
        Favourites for most members with a bread delivery.

        Without these the solver reports "no preference data found" and falls
        back to a distribution that ignores what members actually want, so the
        feature the solver exists for is never exercised on test data.
        """
        breads = list(Bread.objects.all())
        member_ids = set(
            BreadDelivery.objects.values_list("subscription__member_id", flat=True)
        )
        if not breads or not member_ids:
            return

        for member_id in member_ids:
            if random.random() > cls.SHARE_OF_MEMBERS_WITH_PREFERENCES:
                continue
            preferred, _ = PreferredBread.objects.get_or_create(member_id=member_id)
            preferred.breads.set(random.sample(breads, k=random.randint(1, 3)))
