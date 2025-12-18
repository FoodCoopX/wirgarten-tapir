import factory
from dateutil.relativedelta import relativedelta

from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.wirgarten.tests.factories import MemberFactory


class SolidarityContributionFactory(
    factory.django.DjangoModelFactory[SolidarityContribution]
):
    class Meta:
        model = SolidarityContribution

    member = factory.SubFactory(MemberFactory)
    amount = factory.Faker("pyfloat", min_value=-20, max_value=20)
    end_date = factory.LazyAttribute(
        lambda contribution: contribution.start_date + relativedelta(years=1, days=-1)
    )
