import datetime

import factory

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    BreadsToBakePerWeek,
    Bread,
    BreadCapacityPickupLocation,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    BreadSpecificsPerDeliveryDay,
    BreadsPerPickupLocationPerWeek,
    Ingredient,
    PreferredBread,
    StoveSession,
)
from tapir.deliveries.models import Joker
from tapir.wirgarten.models import MemberPickupLocation
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    ProductFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.utils.shortcuts import week_to_monday


class BreadProductTypeFactory(ProductTypeFactory):
    """A product type the bakery actually acts on."""

    delivery_cycle = "weekly"
    is_bread = True


class BreadSubscriptionFactory(SubscriptionFactory):
    """
    Use this instead of SubscriptionFactory in bakery tests: the bakery only
    syncs and reads subscriptions whose product type is marked as bread.
    """

    product = factory.SubFactory(
        ProductFactory, type=factory.SubFactory(BreadProductTypeFactory)
    )


class BreadLabelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BreadLabel

    name = factory.Faker("word")
    is_active = True


BREAD_NAMES = [
    "Roggenbrot",
    "Dinkelkruste",
    "Vollkornbrot",
    "Sauerteigbrot",
    "Weizenmischbrot",
    "Kürbiskernbrot",
]


class BreadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Bread

    # Bread.name is unique, so draw deterministically instead of randomly:
    # a random pick from a fixed list collides as soon as a test builds
    # more breads than the list is long (and often well before that).
    name = factory.Sequence(
        lambda n: BREAD_NAMES[n % len(BREAD_NAMES)]
        + (f" {n // len(BREAD_NAMES)}" if n >= len(BREAD_NAMES) else "")
    )
    weight = factory.Faker("pydecimal", min_value=200, max_value=1500, right_digits=2)
    description = factory.Faker("sentence")
    is_active = True


class IngredientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ingredient

    name = factory.Faker("word")
    description = factory.Faker("sentence")
    is_organic = factory.Faker("boolean")
    is_active = True


class BreadContentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BreadContent

    bread = factory.SubFactory(BreadFactory)
    ingredient = factory.SubFactory(IngredientFactory)
    amount = factory.Faker("pydecimal", min_value=1, max_value=500, right_digits=2)
    sort_order = factory.Sequence(lambda n: n)


class BreadCapacityPickupLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BreadCapacityPickupLocation

    year = 2026
    delivery_week = factory.Faker("random_int", min=1, max=53)
    pickup_location = factory.SubFactory(PickupLocationFactory)
    bread = factory.SubFactory(BreadFactory)
    capacity = factory.Faker("random_int", min=5, max=50)


class AvailableBreadsForDeliveryDayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AvailableBreadsForDeliveryDay

    year = 2026
    delivery_week = factory.Faker("random_int", min=1, max=53)
    delivery_day = factory.Faker("random_int", min=0, max=6)
    bread = factory.SubFactory(BreadFactory)


class BreadDeliveryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BreadDelivery

    year = 2026
    delivery_week = factory.Faker("random_int", min=1, max=53)
    subscription = factory.SubFactory(BreadSubscriptionFactory)
    slot_number = factory.Sequence(lambda n: n + 1)
    bread = factory.SubFactory(BreadFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Translates two arguments into the state a delivery derives them from,
        since it carries neither as a field:

        - pickup_location registers the delivery's member at that station,
        - joker_taken=True gives the member a joker in the delivery's week.
        """
        pickup_location = kwargs.pop("pickup_location", None)
        joker_taken = kwargs.pop("joker_taken", False)

        obj = model_class(*args, **kwargs)
        obj.save()

        member = obj.subscription.member
        if pickup_location is not None:
            existing = MemberPickupLocation.objects.filter(member=member).first()
            if existing is None:
                MemberPickupLocationFactory.create(
                    member=member,
                    pickup_location=pickup_location,
                    # Far enough back that any delivery week resolves to it.
                    valid_from=datetime.date(2000, 1, 1),
                )
            elif existing.pickup_location_id != pickup_location.id:
                raise ValueError(
                    f"{member} is already registered at {existing.pickup_location}. "
                    "A delivery no longer carries its own station - it belongs to "
                    "wherever its member is registered that week - so two stations "
                    "in one week need two members."
                )

        if joker_taken:
            joker_date = week_to_monday(obj.year, obj.delivery_week)
            if not Joker.objects.filter(member=member, date=joker_date).exists():
                Joker.objects.create(member=member, date=joker_date)

        return obj


class PreferredBreadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PreferredBread

    member = factory.SubFactory(MemberFactory)


class BreadsPerPickupLocationPerWeekFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BreadsPerPickupLocationPerWeek

    year = 2026
    delivery_week = factory.Faker("random_int", min=1, max=53)
    pickup_location = factory.SubFactory(PickupLocationFactory)
    bread = factory.SubFactory(BreadFactory)
    count = factory.Faker("random_int", min=1, max=30)


class BreadsToBakePerWeekFactory(factory.django.DjangoModelFactory):
    """
    What the solver decided to bake. Written together with the stove sessions
    in one transaction, so tests that build a baking plan need both.
    """

    class Meta:
        model = BreadsToBakePerWeek

    year = 2026
    delivery_week = factory.Faker("random_int", min=1, max=53)
    delivery_day = factory.Faker("random_int", min=0, max=6)
    bread = factory.SubFactory(BreadFactory)
    quantity = factory.Faker("random_int", min=1, max=40)
    remaining = 0


class StoveSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StoveSession

    year = 2026
    delivery_week = factory.Faker("random_int", min=1, max=53)
    delivery_day = factory.Faker("random_int", min=0, max=6)
    session_number = 1
    layer_number = factory.Sequence(lambda n: n + 1)
    bread = factory.SubFactory(BreadFactory)
    quantity = factory.Faker("random_int", min=1, max=24)


class BreadSpecificsPerDeliveryDayFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BreadSpecificsPerDeliveryDay

    year = 2026
    delivery_week = factory.Faker("random_int", min=1, max=53)
    delivery_day = factory.Faker("random_int", min=0, max=6)
    bread = factory.SubFactory(BreadFactory)


def enable_bakery():
    """
    Switch the bakery on for a test. The delivery sync is a no-op while
    BAKERY_A_ENABLED is False, so any test that expects bread deliveries to be
    written has to opt in.
    """
    from tapir.configuration.models import TapirParameter, TapirParameterDatatype
    from tapir.configuration.parameter import parameter_definition
    from tapir.wirgarten.parameter_keys import ParameterKeys

    # Ensure the row exists...
    parameter_definition(
        key=ParameterKeys.BAKERY_A_ENABLED,
        label="Bäckerei aktiviert",
        datatype=TapirParameterDatatype.BOOLEAN,
        initial_value=True,
        description="Test",
        category="Test",
    )
    # ...then force the value: initial_value only applies on creation, and a
    # test class that imported the parameter definitions already made it False.
    TapirParameter.objects.filter(key=ParameterKeys.BAKERY_A_ENABLED).update(
        value="True"
    )
