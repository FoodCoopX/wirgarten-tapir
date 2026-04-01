import datetime

from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    CoopShareTransactionFactory,
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetQuerysetMembersWithContractSinceMoreThanOneYearButNotCoopShare(
    TapirIntegrationTest
):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_wip(self):
        reference_datetime = datetime.datetime(year=1995, month=1, day=1)

        product = ProductPriceFactory(
            valid_from=reference_datetime - datetime.timedelta(days=30)
        ).product

        member_with_old_subscription_and_shares = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member_with_old_subscription_and_shares,
            valid_at=reference_datetime.date(),
        )
        SubscriptionFactory.create(
            member=member_with_old_subscription_and_shares,
            start_date=reference_datetime.date() - datetime.timedelta(days=366),
            end_date=reference_datetime.date() + datetime.timedelta(days=31),
            product=product,
        )

        member_with_old_subscription_but_no_shares = MemberFactory.create()
        SubscriptionFactory.create(
            member=member_with_old_subscription_but_no_shares,
            start_date=reference_datetime.date() - datetime.timedelta(days=366),
            end_date=reference_datetime.date() + datetime.timedelta(days=31),
            product=product,
        )

        member_with_expired_subscription_and_no_shares = MemberFactory.create()
        SubscriptionFactory.create(
            member=member_with_expired_subscription_and_no_shares,
            start_date=reference_datetime.date() - datetime.timedelta(days=366),
            end_date=reference_datetime.date() - datetime.timedelta(days=1),
            product=product,
        )

        result = MemberSegmentProvider.get_queryset_members_with_contract_since_more_than_one_year_but_no_coop_share(
            reference_datetime=reference_datetime
        )

        self.assertIn(member_with_old_subscription_but_no_shares, result)
        self.assertNotIn(member_with_expired_subscription_and_no_shares, result)
        self.assertNotIn(member_with_old_subscription_and_shares, result)
