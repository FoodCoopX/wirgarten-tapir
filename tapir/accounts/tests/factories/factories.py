import factory

from tapir.accounts.models import TapirUser
from tapir.accounts.tests.factories.user_data_factory import UserDataFactory


class TapirUserFactory(UserDataFactory):
    class Meta:
        model = TapirUser

    username = factory.LazyAttribute(lambda o: f"{o.first_name}.{o.last_name}")
