import factory

from tapir.bakery.models import (
    AvailableBreadsForDeliveryDay,
    Bread,
    BreadCapacityPickupLocation,
    BreadContent,
    BreadDelivery,
    BreadLabel,
    BreadSpecificsPerDeliveryDay,
    BreadsPerPickupLocationPerWeek,
    Ingredient,
    PreferredBread,
    PreferredLabel,
    StoveSession,
)
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    SubscriptionFactory,
)


class BreadLabelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BreadLabel

    name = factory.Faker("word")
    is_active = True


class BreadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Bread

    name = factory.Faker(
        "random_element",
        elements=[
            "Roggenbrot",
            "Dinkelkruste",
            "Vollkornbrot",
            "Sauerteigbrot",
            "Weizenmischbrot",
            "Kürbiskernbrot",
        ],
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


class PreferredLabelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PreferredLabel

    member = factory.SubFactory(MemberFactory)


class BreadDeliveryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BreadDelivery

    year = 2026
    delivery_week = factory.Faker("random_int", min=1, max=53)
    subscription = factory.SubFactory(SubscriptionFactory)
    slot_number = factory.Sequence(lambda n: n + 1)
    pickup_location = factory.SubFactory(PickupLocationFactory)
    bread = factory.SubFactory(BreadFactory)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override create to skip capacity validation in tests."""
        obj = model_class(*args, **kwargs)
        obj.save(skip_validation=True)
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
