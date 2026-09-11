from dateutil.relativedelta import relativedelta

import factory

from tapir.pickup_locations.models import PickupLocationDeliveryCharge
from tapir.wirgarten.tests.factories import PickupLocationFactory, TODAY


class PickupLocationDeliveryChargeFactory(
    factory.django.DjangoModelFactory[PickupLocationDeliveryCharge]
):
    class Meta:
        model = PickupLocationDeliveryCharge

    pickup_location = factory.SubFactory(PickupLocationFactory)
    amount = factory.Faker("pydecimal", left_digits=2, right_digits=2, positive=True)
    valid_from = TODAY - relativedelta(months=1)
