from datetime import UTC

import factory

from tapir.wirgarten.models import WaitingListEntry


class WaitingListEntryFactory(factory.django.DjangoModelFactory[WaitingListEntry]):
    class Meta:
        model = WaitingListEntry

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    phone_number = factory.Faker("phone_number")
    street = factory.Faker("street_address")
    postcode = factory.Faker("postcode")
    city = factory.Faker("city")
    country = factory.Faker("country_code")
    number_of_coop_shares = factory.Faker("pyint", min_value=0, max_value=3)
    privacy_consent = factory.Faker("date_time", tzinfo=UTC)
