import factory

from tapir.associations.models import (
    AssociationMembershipType,
    AssociationMembership,
    AssociationMembershipTypePrice,
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
    valid_from = factory.Faker("date")
    price = factory.Faker("pydecimal", min_value=3, max_value=30)


class AssociationMembershipFactory(
    factory.django.DjangoModelFactory[AssociationMembership]
):
    class Meta:
        model = AssociationMembership

    member = factory.SubFactory(MemberFactory)
    type = factory.SubFactory(AssociationMembershipTypeFactory)
    start_date = factory.Faker("date")
    end_date = None
