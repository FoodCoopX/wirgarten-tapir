import factory

from tapir.deliveries.models import DeliveryDonation
from tapir.wirgarten.tests.factories import MemberFactory


class DeliveryDonationFactory(factory.django.DjangoModelFactory[DeliveryDonation]):
    class Meta:
        model = DeliveryDonation

    member = factory.SubFactory(MemberFactory)
    date = factory.Faker("date")
