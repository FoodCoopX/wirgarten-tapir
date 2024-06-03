import datetime
from collections import defaultdict
from datetime import timedelta

import factory
from dateutil.relativedelta import relativedelta

from tapir.wirgarten.constants import NO_DELIVERY
from tapir.wirgarten.models import (
    CoopShareTransaction,
    ExportedFile,
    GrowingPeriod,
    MandateReference,
    Member,
    MemberPickupLocation,
    Payment,
    PaymentTransaction,
    PickupLocation,
    Product,
    ProductType,
    Subscription,
    ProductCapacity,
    ProductPrice,
    PickupLocationCapability,
)
from tapir.wirgarten.service.payment import generate_mandate_ref

NOW = datetime.datetime(2023, 3, 15, 12, 0, tzinfo=datetime.timezone.utc)

TODAY = NOW.date()


class MemberFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Member

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    account_owner = factory.Faker("last_name")
    iban = factory.Faker("iban")


class MemberWithCoopSharesFactory(MemberFactory):
    @factory.post_generation
    def add_coop_shares(self, create, extracted, **kwargs):
        CoopShareTransactionFactory(member=self, **kwargs)


class MemberWithSubscriptionFactory(MemberWithCoopSharesFactory):
    @factory.post_generation
    def add_subscription(self, create, extracted, **kwargs):
        SubscriptionFactory(member=self, **kwargs)


class ProductTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductType

    name = factory.Faker("word")
    delivery_cycle = NO_DELIVERY[0]


class ProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Product

    type = factory.SubFactory(ProductTypeFactory)
    name = factory.Faker("word")

    _type_counts = defaultdict(int)  # Track counts of Products for each ProductType

    @factory.lazy_attribute
    def base(self):
        ProductFactory._type_counts[self.type.id] += 1
        # If it's the first Product for this type, set base to True
        return ProductFactory._type_counts[self.type.id] == 1


class ProductPriceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductPrice

    product = factory.SubFactory(ProductFactory)
    price = factory.Faker("random_float", min=30, max=150)
    valid_from = TODAY


class MandateReferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MandateReference

    ref = factory.LazyAttribute(lambda o: generate_mandate_ref(o.member.id))
    member = factory.SubFactory(MemberFactory)
    start_ts = TODAY - relativedelta(months=1)


class GrowingPeriodFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GrowingPeriod

    start_date = TODAY + relativedelta(day=1)
    end_date = start_date + relativedelta(years=1, days=-1)


class ProductCapacityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductCapacity

    period = factory.SubFactory(GrowingPeriodFactory)
    product_type = factory.SubFactory(ProductTypeFactory)
    capacity = factory.Faker("random_float", min=1000, max=5000)


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    member = factory.SubFactory(MemberFactory)
    period = factory.SubFactory(GrowingPeriodFactory)
    start_date = factory.SelfAttribute("period.start_date")
    end_date = factory.SelfAttribute("period.end_date")
    quantity = factory.Faker("random_int", min=1, max=10)
    product = factory.SubFactory(ProductFactory)
    mandate_ref = factory.SubFactory(
        MandateReferenceFactory, member=factory.SelfAttribute("..member")
    )


class PickupLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PickupLocation

    name = factory.Faker("company")
    street = factory.Faker("street_address")
    postcode = factory.Faker("postcode")
    city = factory.Faker("city")
    info = factory.Faker("sentence")
    coords_lon = 0
    coords_lat = 0


class PickupLocationCapabilityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PickupLocationCapability

    product_type = factory.SubFactory(ProductTypeFactory)
    max_capacity = factory.Faker("random_int", min=1000, max=2000)
    pickup_location = factory.SubFactory(PickupLocationFactory)


class MemberPickupLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MemberPickupLocation

    member = factory.SubFactory(MemberFactory)
    pickup_location = factory.SubFactory(PickupLocationFactory)
    valid_from = TODAY - relativedelta(months=1)


class CoopShareTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CoopShareTransaction

    member = factory.SubFactory(MemberFactory)
    transaction_type = factory.Faker(
        "random_element", elements=["purchase"]
    )  # cancallation, transfer_in, transfer_out (not implemented yet)
    quantity = factory.Faker("random_int", min=1, max=10)
    share_price = 50
    valid_at = factory.Faker("date_object")


class ExportedFileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExportedFile

    name = factory.Faker("file_name")
    type = "pdf"
    created_at = NOW


class PaymentTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentTransaction

    created_at = NOW
    file = factory.SubFactory(ExportedFileFactory)


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    due_date = TODAY + timedelta(weeks=1)
    mandate_ref = factory.SubFactory(
        MandateReferenceFactory, member=factory.SelfAttribute("..member")
    )
    amount = 100
    status = "PAID"
    transaction = factory.SubFactory(PaymentTransactionFactory)
