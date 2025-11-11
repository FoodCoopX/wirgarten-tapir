import datetime

from tapir.configuration.models import TapirParameter
from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.wirgarten.models import CoopShareTransaction, HarvestShareProduct
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductTypeFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetQuerysetMembersWithTooFewCoopShares(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        TapirParameter.objects.filter(key=ParameterKeys.COOP_MIN_SHARES).update(value=3)

    def test_getQuerysetMembersWithTooFewCoopShares_memberHasNoSubscriptionsAndLessThanTheConfigMinimum_memberIncludedInQueryset(
        self,
    ):
        member = MemberFactory.create()
        CoopShareTransaction.objects.create(
            member=member,
            share_price=100,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            quantity=2,
            valid_at=datetime.date(year=2024, month=2, day=1),
        )

        queryset = MemberSegmentProvider.get_queryset_members_with_too_few_coop_shares(
            datetime.datetime(year=2024, month=2, day=3)
        )

        self.assertIn(member, queryset)

    def test_getQuerysetMembersWithTooFewCoopShares_memberHasNoSubscriptionsAndMoreThanTheConfigMinimum_memberNotIncludedInQueryset(
        self,
    ):
        member = MemberFactory.create()
        CoopShareTransaction.objects.create(
            member=member,
            share_price=100,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            quantity=3,
            valid_at=datetime.date(year=2024, month=2, day=1),
        )

        queryset = MemberSegmentProvider.get_queryset_members_with_too_few_coop_shares(
            datetime.datetime(year=2024, month=2, day=3)
        )

        self.assertNotIn(member, queryset)

    def test_getQuerysetMembersWithTooFewCoopShares_memberHasEnoughSharesForTheirSubscriptions_memberNotIncludedInQueryset(
        self,
    ):
        member = MemberFactory.create()

        product = HarvestShareProduct.objects.create(
            min_coop_shares=1,
            type=ProductTypeFactory.create(),
            name="test_product",
            base=True,
        )
        SubscriptionFactory.create(
            member=member,
            product=product,
            quantity=4,
            period=GrowingPeriodFactory.create(
                start_date=datetime.date(year=2024, month=1, day=1)
            ),
        )

        CoopShareTransaction.objects.create(
            member=member,
            share_price=100,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            quantity=4,
            valid_at=datetime.date(year=2024, month=2, day=1),
        )

        queryset = MemberSegmentProvider.get_queryset_members_with_too_few_coop_shares(
            datetime.datetime(year=2024, month=2, day=3)
        )

        self.assertNotIn(member, queryset)

    def test_getQuerysetMembersWithTooFewCoopShares_memberDoesntHaveEnoughSharesForTheirSubscriptions_memberIncludedInQueryset(
        self,
    ):
        member = MemberFactory.create()

        product = HarvestShareProduct.objects.create(
            min_coop_shares=1,
            type=ProductTypeFactory.create(),
            name="test_product",
            base=True,
        )
        SubscriptionFactory.create(
            member=member,
            product=product,
            quantity=4,
            period=GrowingPeriodFactory.create(
                start_date=datetime.date(year=2024, month=1, day=1)
            ),
        )

        CoopShareTransaction.objects.create(
            member=member,
            share_price=100,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            quantity=3,
            valid_at=datetime.date(year=2024, month=2, day=1),
        )

        queryset = MemberSegmentProvider.get_queryset_members_with_too_few_coop_shares(
            datetime.datetime(year=2024, month=2, day=3)
        )

        self.assertIn(member, queryset)

    def test_getQuerysetMembersWithTooFewCoopShares_memberWithoutSharesNorSubscriptions_memberNotIncludedInQueryset(
        self,
    ):
        member = MemberFactory.create()

        queryset = MemberSegmentProvider.get_queryset_members_with_too_few_coop_shares(
            datetime.datetime(year=2024, month=2, day=3)
        )

        self.assertNotIn(member, queryset)

    def test_getQuerysetMembersWithTooFewCoopShares_memberIsStudent_memberNotIncludedInQueryset(
        self,
    ):
        member = MemberFactory.create(is_student=True)

        product = HarvestShareProduct.objects.create(
            min_coop_shares=1,
            type=ProductTypeFactory.create(),
            name="test_product",
            base=True,
        )
        SubscriptionFactory.create(
            member=member,
            product=product,
            quantity=4,
            period=GrowingPeriodFactory.create(
                start_date=datetime.date(year=2024, month=1, day=1)
            ),
        )

        queryset = MemberSegmentProvider.get_queryset_members_with_too_few_coop_shares(
            datetime.datetime(year=2024, month=2, day=3)
        )

        self.assertNotIn(member, queryset)

    def test_getQuerysetMembersWithTooFewCoopShares_personIsNotAMemberYet_memberNotIncludedInQueryset(
        self,
    ):
        member = MemberFactory.create(is_student=False)
        member.member_no = None
        member.save()

        product = HarvestShareProduct.objects.create(
            min_coop_shares=1,
            type=ProductTypeFactory.create(),
            name="test_product",
            base=True,
        )
        SubscriptionFactory.create(
            member=member,
            product=product,
            quantity=4,
            period=GrowingPeriodFactory.create(
                start_date=datetime.date(year=2024, month=1, day=1)
            ),
        )

        queryset = MemberSegmentProvider.get_queryset_members_with_too_few_coop_shares(
            datetime.datetime(year=2024, month=2, day=3)
        )

        self.assertNotIn(member, queryset)
