import datetime

from tapir.associations.models import AssociationDepositTransaction
from tapir.associations.services.association_deposit_departure_export import (
    AssociationDepositDepartureExport,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import GrowingPeriodFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAssociationDepositDepartureExport(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(self, datetime.datetime(2026, 11, 23, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)

    def test_getMemberships_nonCalendarGrowingPeriod_includesBothBoundariesOnly(self):
        GrowingPeriodFactory.create(
            start_date=datetime.date(2025, 3, 1), end_date=datetime.date(2026, 2, 28)
        )
        GrowingPeriodFactory.create(
            start_date=datetime.date(2026, 3, 1), end_date=datetime.date(2027, 2, 28)
        )
        memberships = []
        for end_date in [
            datetime.date(2025, 2, 28),
            datetime.date(2025, 3, 1),
            datetime.date(2026, 2, 28),
            datetime.date(2026, 3, 1),
        ]:
            membership = AssociationMembershipFactory.create(
                start_date=datetime.date(2024, 1, 1), end_date=end_date
            )
            AssociationDepositTransaction.objects.create(
                member=membership.member,
                transaction_type=AssociationDepositTransaction.Type.IMPORT,
                amount=200,
                valid_at=membership.start_date,
            )
            memberships.append(membership)

        result = AssociationDepositDepartureExport.get_memberships(
            datetime.datetime(2026, 11, 23, 12)
        )

        self.assertCountEqual(
            [memberships[1].pk, memberships[2].pk], result.values_list("pk", flat=True)
        )

    def test_getMemberships_noCompletedGrowingPeriod_returnsEmptyQueryset(self):
        GrowingPeriodFactory.create(
            start_date=datetime.date(2026, 3, 1), end_date=datetime.date(2027, 2, 28)
        )

        result = AssociationDepositDepartureExport.get_memberships(
            datetime.datetime(2026, 11, 23, 12)
        )

        self.assertFalse(result.exists())

    def test_getColumns_formulaInAccountOwner_exportsAsText(self):
        membership = AssociationMembershipFactory.create()
        membership.member.account_owner = "=1+1"
        column = next(
            column
            for column in AssociationDepositDepartureExport.get_columns()
            if column.id == "account_owner"
        )

        result = column.get_value(membership, datetime.datetime(2026, 11, 23, 12), {})

        self.assertEqual("'=1+1", result)

    def test_getColumns_normalAccountOwner_keepsTextUnchanged(self):
        membership = AssociationMembershipFactory.create()
        membership.member.account_owner = "Mika Muster"
        column = next(
            column
            for column in AssociationDepositDepartureExport.get_columns()
            if column.id == "account_owner"
        )

        result = column.get_value(membership, datetime.datetime(2026, 11, 23, 12), {})

        self.assertEqual("Mika Muster", result)
