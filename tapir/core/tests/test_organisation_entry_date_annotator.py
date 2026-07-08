import datetime

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import (
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_COMPANY,
)
from tapir.core.services.organisation_entry_date_annotator import (
    OrganisationEntryDateAnnotator,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, CoopShareTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestOrganisationEntryDateAnnotator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        member = MemberFactory.create()
        Member.objects.update(
            created_at=datetime.datetime(
                year=2023, month=4, day=15, hour=12, tzinfo=datetime.timezone.utc
            )
        )
        CoopShareTransactionFactory.create(
            member=member, valid_at=datetime.date(year=1998, month=6, day=12)
        )
        AssociationMembershipFactory.create(
            member=member, start_date=datetime.date(year=2017, month=12, day=14)
        )

    def test_annotateWithOrganisationEntryDate_legalStatusIsAssociation_annotatesWithAssociationMembershipStartDate(
        self,
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_ASSOCIATION
        )

        queryset = OrganisationEntryDateAnnotator.annotate_with_organisation_entry_date(
            queryset=Member.objects.all(), cache={}
        )

        member = queryset.get()
        annotated_value = getattr(
            member, OrganisationEntryDateAnnotator.ANNOTATION_ORGANISATION_ENTRY_DATE
        )
        self.assertEqual(datetime.date(year=2017, month=12, day=14), annotated_value)

    def test_annotateWithOrganisationEntryDate_legalStatusIsCooperative_annotatesWithShareTransactionValidityDate(
        self,
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COOPERATIVE
        )

        queryset = OrganisationEntryDateAnnotator.annotate_with_organisation_entry_date(
            queryset=Member.objects.all(), cache={}
        )

        member = queryset.get()
        annotated_value = getattr(
            member, OrganisationEntryDateAnnotator.ANNOTATION_ORGANISATION_ENTRY_DATE
        )
        self.assertEqual(datetime.date(year=1998, month=6, day=12), annotated_value)

    def test_annotateWithOrganisationEntryDate_legalStatusIsCompany_annotatesWithMemberCreationDate(
        self,
    ):
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COMPANY
        )

        queryset = OrganisationEntryDateAnnotator.annotate_with_organisation_entry_date(
            queryset=Member.objects.all(), cache={}
        )

        member = queryset.get()
        annotated_value = getattr(
            member, OrganisationEntryDateAnnotator.ANNOTATION_ORGANISATION_ENTRY_DATE
        )
        self.assertEqual(datetime.date(year=2023, month=4, day=15), annotated_value)
