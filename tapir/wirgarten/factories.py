import factory
import factory.fuzzy
from datetime import timedelta

from django.utils import timezone
from tapir.wirgarten.models import (
    PickupLocation,
    Member,
    MandateReference,
    Subscription,
    Product,
    ProductType,
    GrowingPeriod,
    PaymentTransaction,
    Payment,
    ExportedFile,
)
from tapir.accounts.tests.factories.factories import TapirUserFactory
from tapir.wirgarten.service.payment import generate_mandate_ref
from tapir.wirgarten.constants import NO_DELIVERY


class PickupLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PickupLocation

    name = factory.fuzzy.FuzzyText()
    coords_lon = 1
    coords_lat = 2
    street = factory.fuzzy.FuzzyText()
    street_2 = factory.fuzzy.FuzzyText()
    postcode = factory.Faker("postcode")
    city = factory.Faker("city")
    info = factory.Faker("sentence")


class MemberFactory(TapirUserFactory):
    class Meta:
        model = Member

    account_owner = factory.Faker("last_name")
    iban = factory.Faker("iban")
    bic = "AABSDE31"
    sepa_consent = factory.LazyAttribute(lambda _: timezone.now())
    pickup_location = factory.SubFactory(PickupLocationFactory)
    withdrawal_consent = factory.LazyAttribute(lambda _: timezone.now())
    privacy_consent = factory.LazyAttribute(lambda _: timezone.now())


class MandateReferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MandateReference

    class Params:
        for_shares = factory.Trait(
            ref=factory.LazyAttribute(lambda o: generate_mandate_ref(o.member.id, True))
        )

    ref = factory.LazyAttribute(lambda o: generate_mandate_ref(o.member.id, False))
    member = factory.SubFactory(MemberFactory)
    start_ts = factory.LazyAttribute(lambda _: timezone.now())


class ProductTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductType

    name = factory.fuzzy.FuzzyText()
    delivery_cycle = NO_DELIVERY[0]


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    type = factory.SubFactory(ProductTypeFactory)
    name = factory.fuzzy.FuzzyText()


class GrowingPeriodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GrowingPeriod

    start_date = timezone.now().replace(month=3)
    end_date = factory.LazyAttribute(
        lambda o: o.start_date.replace(month=2, year=o.start_date.year + 1)
    )


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    member = factory.SubFactory(MemberFactory)
    product = factory.SubFactory(ProductFactory)
    period = factory.SubFactory(GrowingPeriodFactory)
    quantity = 1
    start_date = factory.LazyAttribute(lambda _: timezone.now())
    end_date = factory.LazyAttribute(lambda _: timezone.now())
    cancellation_ts = factory.LazyAttribute(lambda _: timezone.now())
    solidarity_price = 0.3
    mandate_ref = factory.SubFactory(
        MandateReferenceFactory, member=factory.SelfAttribute("..member")
    )


class ExportedFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExportedFile

    name = factory.fuzzy.FuzzyText()
    type = "pdf"
    # file = models.BinaryField(null=False)
    created_at = factory.LazyAttribute(lambda _: timezone.now())


class PaymentTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentTransaction

    created_at = factory.LazyAttribute(lambda _: timezone.now())
    file = factory.SubFactory(ExportedFileFactory)


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    due_date = factory.LazyAttribute(lambda _: timezone.now() + timedelta(weeks=1))
    mandate_ref = factory.SubFactory(MandateReferenceFactory)
    amount = 100
    status = "PAID"
    transaction = factory.SubFactory(PaymentTransactionFactory)
