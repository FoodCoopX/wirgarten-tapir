from dateutil.relativedelta import relativedelta

import factory

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.tests.factories import (
    PickupLocationFactory,
    PickupLocationOpeningTimesFactory,
    TODAY,
)


class PickupLocationDeliveryChargeFactory(
    factory.django.DjangoModelFactory[PickupLocationDeliveryCharge]
):
    class Meta:
        model = PickupLocationDeliveryCharge

    pickup_location = factory.SubFactory(PickupLocationFactory)
    amount = factory.Faker("pydecimal", left_digits=2, right_digits=2, positive=True)
    valid_from = TODAY - relativedelta(months=1)


def create_pickup_location_with_opening_times(
    open_days: list[int], **kwargs
) -> PickupLocation:
    pickup_location = PickupLocationFactory.create(**kwargs)
    for day_of_week in open_days:
        PickupLocationOpeningTimesFactory.create(
            pickup_location=pickup_location, day_of_week=day_of_week
        )
    return pickup_location
