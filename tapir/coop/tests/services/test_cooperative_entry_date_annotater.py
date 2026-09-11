import datetime

from django.db.models import QuerySet

from tapir.coop.services.cooperative_entry_date_annotater import (
    CooperativeEntryDateAnnotater,
)
from tapir.wirgarten.models import Member, CoopShareTransaction
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, CoopShareTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCooperativeEntryDateAnnotater(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_annotateMemberQuerysetWithCoopEntryDate_default_annotatesCorrectValues(
        self,
    ):
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
        self.assert_annotation_entry_date_equals(
            member=member_with_several_transactions,
            queryset=queryset,
            expected_value=datetime.date(year=2010, month=1, day=1),
        )
        self.assert_annotation_entry_date_equals(
            member=member_with_one_transaction,
            queryset=queryset,
            expected_value=datetime.date(year=2011, month=1, day=1),
        )
        self.assert_annotation_entry_date_equals(
            member=member_without_transactions,
            queryset=queryset,
            expected_value=None,
        )

    def assert_annotation_entry_date_equals(
        self, member: Member, queryset: QuerySet, expected_value: datetime.date | None
    ):
        self.assertEqual(
            getattr(
                queryset.get(id=member.id),
                CooperativeEntryDateAnnotater.ANNOTATION_COOP_ENTRY_DATE,
            ),
            expected_value,
        )

    def test_annotateMemberQuerysetWithCoopExitDate_default_annotatesCorrectValues(
        self,
    ):
        (
            member_with_all_shares_cancelled,
            member_with_some_negative_transactions,
            member_with_one_positive_transaction,
            member_without_transactions,
        ) = MemberFactory.create_batch(size=4)

        CoopShareTransactionFactory.create(
            member=member_with_all_shares_cancelled,
            valid_at=datetime.date(year=2010, month=1, day=1),
            quantity=5,
        )
        CoopShareTransactionFactory.create(
            member=member_with_all_shares_cancelled,
            valid_at=datetime.date(year=2010, month=6, day=6),
            quantity=-2,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
        )
        CoopShareTransactionFactory.create(
            member=member_with_all_shares_cancelled,
            valid_at=datetime.date(year=2010, month=7, day=7),
            quantity=-3,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
        )

        CoopShareTransactionFactory.create(
            member=member_with_some_negative_transactions,
            valid_at=datetime.date(year=2010, month=1, day=1),
            quantity=5,
        )
        CoopShareTransactionFactory.create(
            member=member_with_some_negative_transactions,
            valid_at=datetime.date(year=2010, month=8, day=8),
            quantity=-2,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
        )
        CoopShareTransactionFactory.create(
            member=member_with_some_negative_transactions,
            valid_at=datetime.date(year=2010, month=9, day=9),
            quantity=-1,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
        )

        CoopShareTransactionFactory.create(
            member=member_with_one_positive_transaction,
            valid_at=datetime.date(year=2010, month=1, day=1),
            quantity=1,
        )

        queryset = (
            CooperativeEntryDateAnnotater.annotate_member_queryset_with_coop_exit_date(
                queryset=Member.objects.all()
            )
        )

        self.assert_annotation_exit_date_equals(
            member=member_without_transactions, queryset=queryset, expected_value=None
        )
        self.assert_annotation_exit_date_equals(
            member=member_with_one_positive_transaction,
            queryset=queryset,
            expected_value=None,
        )
        self.assert_annotation_exit_date_equals(
            member=member_with_some_negative_transactions,
            queryset=queryset,
            expected_value=None,
        )
        self.assert_annotation_exit_date_equals(
            member=member_with_all_shares_cancelled,
            queryset=queryset,
            expected_value=datetime.date(year=2010, month=7, day=7),
        )

    def assert_annotation_exit_date_equals(
        self, member: Member, queryset: QuerySet, expected_value: datetime.date | None
    ):
        self.assertEqual(
            getattr(
                queryset.get(id=member.id),
                CooperativeEntryDateAnnotater.ANNOTATION_COOP_EXIT_DATE,
            ),
            expected_value,
        )
