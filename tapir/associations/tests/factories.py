import factory

from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembership,
    AssociationMembershipTypePrice,
    AssociationDepositAccount,
    AssociationDepositReceipt,
)
from tapir.wirgarten.tests.factories import MemberFactory


class AssociationMembershipTypeFactory(
    factory.django.DjangoModelFactory[AssociationMembershipType]
):
    class Meta:
        model = AssociationMembershipType

    name = factory.Faker("bs")
    deleted = False
    description_in_bestell_wizard = factory.Faker("paragraph")
    order_in_bestell_wizard = 1


class AssociationMembershipTypePriceFactory(
    factory.django.DjangoModelFactory[AssociationMembershipTypePrice]
):
    class Meta:
        model = AssociationMembershipTypePrice

    type = factory.SubFactory(AssociationMembershipTypeFactory)
    valid_from = factory.Faker("date_object")
    price = factory.Faker("pydecimal", min_value=3, max_value=30)


class AssociationMembershipFactory(
    factory.django.DjangoModelFactory[AssociationMembership]
):
    class Meta:
        model = AssociationMembership

    member = factory.SubFactory(MemberFactory)
    type = factory.SubFactory(AssociationMembershipTypeFactory)
    start_date = factory.Faker("date_object")
    end_date = None


class AssociationDepositAccountFactory(
    factory.django.DjangoModelFactory[AssociationDepositAccount]
):
    member = factory.SubFactory(MemberFactory)

    class Meta:
        model = AssociationDepositAccount


class AssociationDepositReceiptFactory(
    factory.django.DjangoModelFactory[AssociationDepositReceipt]
):
    account = factory.SubFactory(AssociationDepositAccountFactory)
    reference = factory.Sequence(lambda number: f"receipt-{number}")
    amount = 200
    received_on = factory.Faker("past_date")
    note = "Historischer Zahlungseingang"

    class Meta:
        model = AssociationDepositReceipt
