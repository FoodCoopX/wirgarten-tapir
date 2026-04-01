import factory

from tapir.deliveries.models import DeliveryDonation, CustomCycleScheduledDeliveryWeek
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


class CustomCycleScheduledDeliveryWeekFactory(
    factory.django.DjangoModelFactory[CustomCycleScheduledDeliveryWeek]
):
    class Meta:
        model = CustomCycleScheduledDeliveryWeek

    product_type = factory.SubFactory(ProductTypeFactory)
    growing_period = factory.SubFactory(GrowingPeriodFactory)
    calendar_week = factory.Faker("pyint", min_value=1, max_value=52)
