import factory

from tapir.payments.models import MemberCredit, PaymentExportExclusionPeriod
from tapir.wirgarten.tests.factories import MemberFactory


class MemberCreditFactory(factory.django.DjangoModelFactory[MemberCredit]):
    class Meta:
        model = MemberCredit

    due_date = factory.Faker("date")
    member = factory.SubFactory(MemberFactory)
    amount = factory.Faker("pydecimal", min_value=10, max_value=100)
    purpose = factory.Faker("bs")
    comment = factory.Faker("bs")
    source = factory.Faker("bs")


class PaymentExportExclusionPeriodFactory(
    factory.django.DjangoModelFactory[PaymentExportExclusionPeriod]
):
    class Meta:
        model = PaymentExportExclusionPeriod

    member = factory.SubFactory(MemberFactory)
    start_date = factory.Faker("date_object")
    end_date = None
    comment = factory.Faker("bs")
