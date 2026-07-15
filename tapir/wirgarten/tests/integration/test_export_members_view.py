from django.urls import reverse
from rest_framework import status

from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import (
    LEGAL_STATUS_ASSOCIATION,
    LEGAL_STATUS_COOPERATIVE,
    LEGAL_STATUS_COMPANY,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    CoopShareTransactionFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExportMembersView(TapirIntegrationTest):
    # The ExportMembersView class is legacy code, I chose not to take the time to test it fully.
    # Instead, I just check that it renders for the three legal statuses as we had unexpected bugs related to that.

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        MemberFactory.create_batch(size=10)
        AssociationMembershipFactory.create_batch(size=10)
        CoopShareTransactionFactory.create_batch(size=10)
        SubscriptionFactory.create_batch(size=10)

    def test_exportMembersView_legalStatusIsAssociation_returns200(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_ASSOCIATION
        )

        response = self.client.get(reverse("wirgarten:member_overview_export"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_exportMembersView_legalStatusIsCooperative_returns200(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COOPERATIVE
        )

        response = self.client.get(reverse("wirgarten:member_overview_export"))

        self.assertStatusCode(response, status.HTTP_200_OK)

    def test_exportMembersView_legalStatusIsCompany_returns200(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        self._set_parameter(
            key=ParameterKeys.ORGANISATION_LEGAL_STATUS, value=LEGAL_STATUS_COMPANY
        )

        response = self.client.get(reverse("wirgarten:member_overview_export"))

        self.assertStatusCode(response, status.HTTP_200_OK)
