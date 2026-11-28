import datetime
from decimal import Decimal

from django.urls import reverse

from tapir.associations.models import AssociationDepositTransaction
from tapir.associations.services.association_deposit_annotator import (
    AssociationDepositAnnotator,
)
from tapir.associations.tests.factories import AssociationMembershipFactory
from tapir.core.config import LEGAL_STATUS_ASSOCIATION
from tapir.generic_exports.models import AutomatedCsvExportResult, CsvExport
from tapir.generic_exports.services.automated_exports_manager import (
    AutomatedExportsManager,
)
from tapir.generic_exports.services.csv_export_template_manager import (
    CsvExportTemplateManager,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestDepositDepartureExport(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        self._set_parameter(ParameterKeys.ASSOCIATION_DEPOSIT_ENABLED, True)
        GrowingPeriodFactory.create(
            start_date=datetime.date(2025, 3, 1), end_date=datetime.date(2026, 2, 28)
        )

    def test_get_csvExport_excludesDepositOfRejoinedMember(self):
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        member = MemberFactory.create(is_superuser=True)
        AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
        )
        AssociationMembershipFactory.create(
            member=member,
            start_date=datetime.date(2026, 3, 1),
            end_date=datetime.date(2026, 12, 31),
        )
        AssociationDepositTransaction.objects.create(
            member=member,
            transaction_type=AssociationDepositTransaction.Type.IMPORT,
            amount=200,
            valid_at=datetime.date(2025, 1, 1),
        )
        AssociationMembershipFactory.create(
            member=member, start_date=datetime.date(2027, 3, 1)
        )
        CsvExportTemplateManager.create_exports_from_template(
            "association_deposit_departures", {}
        )
        self.client.force_login(member)
        response = self.client.get(
            reverse("generic_exports:build_csv_export"),
            {
                "csv_export_id": CsvExport.objects.get().pk,
                "reference_datetime": "2026-11-05T12:00:00+01:00",
            },
        )
        self.assertStatusCode(response, 200)
        csv = response.json()["file_as_string"]
        self.assertNotIn("2025-12-31", csv)
        self.assertNotIn("200,00", csv)
        overview = AssociationDepositAnnotator.annotate_members(
            Member.objects.filter(pk=member.pk)
        ).get()
        self.assertEqual(Decimal("200"), overview.deposit_agreed)
        self.assertEqual(Decimal("200"), overview.deposit_exported)

    def test_doAutomatedCsvExports_yearlyTemplate_exportsPreviousGrowingPeriodOnce(
        self,
    ):
        mock_timezone(self, datetime.datetime(2027, 1, 2, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        for year, amount in ((2025, 300), (2026, 200)):
            membership = AssociationMembershipFactory.create(
                start_date=datetime.date(year, 1, 1),
                end_date=datetime.date(year, 12, 31),
            )
            AssociationDepositTransaction.objects.create(
                member=membership.member,
                transaction_type=AssociationDepositTransaction.Type.IMPORT,
                amount=amount,
                valid_at=membership.start_date,
            )
        CsvExportTemplateManager.create_exports_from_template(
            "association_deposit_departures", {}
        )
        export = CsvExport.objects.get()
        self.assertEqual([], export.email_recipients)
        AutomatedExportsManager.do_automated_csv_exports({})
        AutomatedExportsManager.do_automated_csv_exports({})
        file = AutomatedCsvExportResult.objects.get().file
        self.client.force_login(MemberFactory.create())
        self.assertEqual(
            302,
            self.client.get(
                reverse("wirgarten:exported_files_download", args=[file.pk])
            ).status_code,
        )
        self.assertEqual(
            403,
            self.client.get(reverse("wirgarten:exported_files_list")).status_code,
        )
        csv = bytes(file.file).decode()
        self.assertIn("2025-12-31", csv)
        self.assertIn("300,00", csv)
        self.assertNotIn("2026-12-31", csv)
