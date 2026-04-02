import datetime

from tapir.generic_exports.services.member_segment_provider import MemberSegmentProvider
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    CoopShareTransactionFactory,
    MemberFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetQuerysetMembersWithCancelledSharesInPreviousYear(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_wip(self):
        this_year = 2026

        members_with_shares_cancelled_last_year = []

        # created 2 years ago, cancelled last year
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member,
            quantity=55,
            valid_at=datetime.date(this_year - 2, 3, 1),
        )
        CoopShareTransactionFactory.create(
            member=member,
            quantity=-55,
            valid_at=datetime.date(this_year - 1, 2, 1),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
        )
        members_with_shares_cancelled_last_year.append(member)

        # created 2 years ago, cancelled this year
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member,
            quantity=55,
            valid_at=datetime.date(this_year - 2, 3, 1),
        )
        CoopShareTransactionFactory.create(
            member=member,
            quantity=-55,
            valid_at=datetime.date(this_year, 2, 1),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
        )
        # members_with_shares_cancelled_last_year.append(member)

        # created 2 years ago, partially cancelled last year
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member,
            quantity=55,
            valid_at=datetime.date(this_year - 2, 3, 1),
        )
        CoopShareTransactionFactory.create(
            member=member,
            quantity=-6,
            valid_at=datetime.date(this_year - 1, 2, 1),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
        )
        members_with_shares_cancelled_last_year.append(member)

        result = MemberSegmentProvider.get_queryset_members_with_cancelled_shares_in_previous_year(
            reference_datetime=datetime.datetime(this_year, 2, 1)
        )
        self.assertEqual(len(members_with_shares_cancelled_last_year), len(result))
        for m in members_with_shares_cancelled_last_year:
            self.assertIn(m, result)
