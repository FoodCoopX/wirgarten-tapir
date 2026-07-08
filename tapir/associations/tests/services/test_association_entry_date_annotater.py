import datetime

from django.db.models import QuerySet

from tapir.associations.services.association_entry_date_annotater import (
    AssociationEntryDateAnnotater,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestAssociationEntryDateAnnotater(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_annotateQuerysetWithAssociationEntryDate_default_annotatesCorrectly(self):
        (
            member_with_several_memberships,
            member_with_one_past_membership,
            member_with_one_future_membership,
            member_without_membership,
        ) = MemberFactory.create_batch(size=4)

        AssociationMembershipFactory.create(
            member=member_with_several_memberships,
            start_date=datetime.date(year=1998, month=4, day=17),
        )
        AssociationMembershipFactory.create(
            member=member_with_several_memberships,
            start_date=datetime.date(year=1999, month=2, day=19),
        )
        AssociationMembershipFactory.create(
            member=member_with_one_past_membership,
            start_date=datetime.date(year=1998, month=6, day=9),
            end_date=datetime.date(year=1998, month=12, day=31),
        )
        AssociationMembershipFactory.create(
            member=member_with_one_future_membership,
            start_date=datetime.date(year=2100, month=11, day=13),
        )

        queryset = (
            AssociationEntryDateAnnotater.annotate_queryset_with_association_entry_date(
                Member.objects.all()
            )
        )

        self.assertEqual(4, queryset.count())
        self.assert_annotation_equals(
            member=member_with_several_memberships,
            queryset=queryset,
            expected_value=datetime.date(year=1998, month=4, day=17),
        )
        self.assert_annotation_equals(
            member=member_with_one_past_membership,
            queryset=queryset,
            expected_value=datetime.date(year=1998, month=6, day=9),
        )
        self.assert_annotation_equals(
            member=member_with_one_future_membership,
            queryset=queryset,
            expected_value=datetime.date(year=2100, month=11, day=13),
        )
        self.assert_annotation_equals(
            member=member_without_membership,
            queryset=queryset,
            expected_value=None,
        )

    def assert_annotation_equals(
        self, member: Member, queryset: QuerySet, expected_value: datetime.date | None
    ):
        self.assertEqual(
            getattr(
                queryset.get(id=member.id),
                AssociationEntryDateAnnotater.ANNOTATION_ASSOCIATION_ENTRY_DATE,
            ),
            expected_value,
        )
