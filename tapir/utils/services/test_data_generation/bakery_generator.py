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
from tapir.bakery.services.breaddelivery_service import BreadDeliveryService
from tapir.configuration.models import TapirParameter
from tapir.pickup_locations.services.pickup_location_delivery_day_service import (
    PickupLocationDeliveryDayService,
)
from tapir.wirgarten.models import Member, PickupLocation, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import get_today

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
    NUMBER_OF_WEEKS_WITH_DATA = 6
    CAPACITY_PER_BREAD_AND_STATION = 25
    SHARE_OF_MEMBERS_WITH_PREFERENCES = 0.6

    @classmethod
    def generate_masterdata(cls):
        print("Creating bakery masterdata...")
        cls.generate_breads()
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
    def enable_bakery_parameters(cls):
        for key in [
            ParameterKeys.BAKERY_ENABLED,
            ParameterKeys.BAKERY_MEMBERS_CAN_CHOOSE_BREAD_SORTS,
            ParameterKeys.BAKERY_MEMBERS_CAN_REDUCE_BREAD_SHARES,
            ParameterKeys.BAKERY_PICKUP_LOCATIONS_CAN_BE_CHOSEN_PER_SHARE,
        ]:
            TapirParameter.objects.filter(key=key).update(value="True")

    @classmethod
    def generate_week_data(cls):
        print("Creating bakery capacities...")
        weeks = cls.get_weeks_with_data()
        cls.generate_capacities(weeks)
        cls.generate_available_breads_per_delivery_day(weeks)
        print("Creating bread deliveries...")
        cls.generate_bread_deliveries()
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
    def generate_bread_deliveries(cls):
        cache = {}
        member_ids = Subscription.objects.values_list("member_id", flat=True).distinct()
        for member in Member.objects.filter(id__in=list(member_ids)):
            BreadDeliveryService.ensure_bread_deliveries_for_member(member, cache=cache)

    @classmethod
    def assign_breads_to_deliveries(cls, weeks: list[tuple[int, int]]):
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
