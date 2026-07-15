import datetime

from django.db.models import QuerySet

from tapir.coop.services.cooperative_entry_date_annotater import (
    CooperativeEntryDateAnnotater,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, CoopShareTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCooperativeEntryDateAnnotater(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_annotateMemberQuerysetWithCoopSharesTo(self):
        (
            member_with_several_transactions,
            member_with_one_transaction,
            member_without_transactions,
        ) = MemberFactory.create_batch(size=3)

        CoopShareTransactionFactory.create(
            member=member_with_several_transactions,
            valid_at=datetime.date(year=2010, month=1, day=1),
        )
        CoopShareTransactionFactory.create(
            member=member_with_several_transactions,
            valid_at=datetime.date(year=2010, month=2, day=1),
        )
        CoopShareTransactionFactory.create(
            member=member_with_several_transactions,
            valid_at=datetime.date(year=2010, month=3, day=1),
        )
        CoopShareTransactionFactory.create(
            member=member_with_one_transaction,
            valid_at=datetime.date(year=2011, month=1, day=1),
        )

        queryset = (
            CooperativeEntryDateAnnotater.annotate_member_queryset_with_coop_entry_date(
                queryset=Member.objects.all()
            )
        )

        self.assertEqual(3, queryset.count())
        self.assert_annotation_equals(
            member=member_with_several_transactions,
            queryset=queryset,
            expected_value=datetime.date(year=2010, month=1, day=1),
        )
        self.assert_annotation_equals(
            member=member_with_one_transaction,
            queryset=queryset,
            expected_value=datetime.date(year=2011, month=1, day=1),
        )
        self.assert_annotation_equals(
            member=member_without_transactions,
            queryset=queryset,
            expected_value=None,
        )

    def assert_annotation_equals(
        self, member: Member, queryset: QuerySet, expected_value: datetime.date | None
    ):
        self.assertEqual(
            getattr(
                queryset.get(id=member.id),
                CooperativeEntryDateAnnotater.ANNOTATION_COOP_ENTRY_DATE,
            ),
            expected_value,
        )
