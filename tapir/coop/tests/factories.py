import factory

from tapir.accounts.tests.factories.user_data_factory import UserDataFactory
from tapir.coop.models import (
    ShareOwnership,
    ShareOwner,
    DraftUser,
    COOP_SHARE_PRICE,
    COOP_MINIMUM_SHARES,
)


class ShareOwnershipFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ShareOwnership

    start_date = factory.Faker("date")
    amount_paid = factory.Faker("pydecimal", min_value=0, max_value=COOP_SHARE_PRICE)


class PaymentDataFactoryMixin(factory.django.DjangoModelFactory):
    class Meta:
        abstract = True
        exclude = ("ATTRIBUTES",)

    ATTRIBUTES = ["account_owner", "iban", "bic"]

    account_owner = factory.LazyAttribute(lambda o: f"{o.first_name} {o.last_name}")
    iban = factory.Faker("iban")
    bic = factory.Faker("swift")


class ShareOwnerFactory(UserDataFactory, PaymentDataFactoryMixin):
    class Meta:
        model = ShareOwner

    ATTRIBUTES = (
        UserDataFactory.ATTRIBUTES
        + PaymentDataFactoryMixin.ATTRIBUTES
        + ["is_investing"]
    )

    is_investing = factory.Faker("pybool")
    date_joined = factory.Faker("date_time")

    @factory.post_generation
    def nb_shares(self, create, nb_shares, **kwargs):
        if not create:
            return
        for _ in range(nb_shares or 1):
            ShareOwnershipFactory.create(owner=self)


class DraftUserFactory(UserDataFactory, PaymentDataFactoryMixin):
    class Meta:
        model = DraftUser

    ATTRIBUTES = (
        UserDataFactory.ATTRIBUTES
        + PaymentDataFactoryMixin.ATTRIBUTES
        + [
            "num_shares",
            "is_investing",
            "paid_shares",
            "attended_welcome_session",
            "ratenzahlung",
            "paid_membership_fee",
            "signed_membership_agreement",
        ]
    )

    num_shares = factory.Faker("pyint", min_value=COOP_MINIMUM_SHARES, max_value=20)
    is_investing = factory.Faker("pybool")
    paid_shares = factory.Faker("pybool")
    attended_welcome_session = factory.Faker("pybool")
    ratenzahlung = factory.Faker("pybool")
    paid_membership_fee = factory.Faker("pybool")
    signed_membership_agreement = factory.Faker("pybool")
