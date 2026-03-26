import factory

from tapir.deliveries.models import DeliveryDonation, CustomCycleDeliveryWeeks
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductTypeFactory,
    GrowingPeriodFactory,
)


class DeliveryDonationFactory(factory.django.DjangoModelFactory[DeliveryDonation]):
    class Meta:
        model = DeliveryDonation

    member = factory.SubFactory(MemberFactory)
    date = factory.Faker("date")


class CustomCycleDeliveryWeeksFactory(
    factory.django.DjangoModelFactory[CustomCycleDeliveryWeeks]
):
    class Meta:
        model = CustomCycleDeliveryWeeks

    product_type = factory.SubFactory(ProductTypeFactory)
    growing_period = factory.SubFactory(GrowingPeriodFactory)
    calendar_week = factory.Faker("pyint", min_value=1, max_value=52)
