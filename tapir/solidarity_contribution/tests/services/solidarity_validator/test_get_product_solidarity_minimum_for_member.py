import datetime

from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetProductSolidarityMinimumForMember(TapirIntegrationTest):
    def test_getProductSolidarityMinimumForMember_default_ignoresSubscriptionsThatEndedBeforeReferenceDate(
        self,
    ):
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1)
        )
        SubscriptionFactory.create(
            member=member,
            period=growing_period,
            end_date=datetime.date(year=2025, month=5, day=31),
            product__solidarity_choices="-20,0",
        )
        SubscriptionFactory.create(
            member=member,
            period=growing_period,
            product__solidarity_choices="-10,0,10",
        )

        result = SolidarityValidator.get_product_solidarity_minimum_for_member(
            member_id=member.id,
            reference_date=datetime.date(year=2025, month=6, day=1),
            cache={},
        )

        self.assertEqual(-10, result)

    def test_getProductSolidarityMinimumForMember_subscriptionEndsOnReferenceDate_subscriptionIsIncluded(
        self,
    ):
        member = MemberFactory.create()
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1)
        )
        SubscriptionFactory.create(
            member=member,
            period=growing_period,
            end_date=datetime.date(year=2025, month=6, day=1),
            product__solidarity_choices="-20,0",
        )
        SubscriptionFactory.create(
            member=member,
            period=growing_period,
            product__solidarity_choices="-10,0,10",
        )

        result = SolidarityValidator.get_product_solidarity_minimum_for_member(
            member_id=member.id,
            reference_date=datetime.date(year=2025, month=6, day=1),
            cache={},
        )

        self.assertEqual(-20, result)
