import datetime
from decimal import Decimal

from tapir.configuration.models import TapirParameter
from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetSolidarityExcess(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getSolidarityExcess_default_returnsSumOfSoliFactors(self):
        SolidarityContribution.objects.create(
            member=MemberFactory.create(),
            amount=Decimal("12.5"),
            start_date=datetime.date(year=1996, month=1, day=1),
            end_date=datetime.date(year=1996, month=12, day=31),
        )
        SolidarityContribution.objects.create(
            member=MemberFactory.create(),
            amount=Decimal("-8"),
            start_date=datetime.date(year=1996, month=1, day=1),
            end_date=datetime.date(year=1996, month=12, day=31),
        )
        SolidarityContribution.objects.create(
            member=MemberFactory.create(),
            amount=Decimal("0.27"),
            start_date=datetime.date(year=1996, month=6, day=12),
            end_date=datetime.date(year=1996, month=12, day=31),
        )

        result = SolidarityValidator.get_solidarity_excess(
            reference_date=datetime.date(year=1996, month=6, day=11), cache={}
        )

        self.assertEqual(Decimal("4.5"), result)

    def test_getSolidarityExcess_askingAboutAFutureGrowingPeriod_returnsSumOfSoliFactorsIncludingRenewals(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        ).update(value=True)
        GrowingPeriodFactory.create(start_date=datetime.date(year=1996, month=1, day=1))
        GrowingPeriodFactory.create(start_date=datetime.date(year=1997, month=1, day=1))

        SolidarityContribution.objects.create(
            member=MemberFactory.create(),
            amount=Decimal("12.5"),
            start_date=datetime.date(year=1996, month=1, day=1),
            end_date=datetime.date(year=1996, month=12, day=31),
        )
        SolidarityContribution.objects.create(
            member=MemberFactory.create(),
            amount=Decimal("-8"),
            start_date=datetime.date(year=1997, month=1, day=1),
            end_date=datetime.date(year=1997, month=12, day=31),
        )

        result = SolidarityValidator.get_solidarity_excess(
            reference_date=datetime.date(year=1997, month=3, day=11), cache={}
        )

        self.assertEqual(Decimal("4.5"), result)
