import datetime
from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse

from tapir.accounts.models import KeycloakUser
from tapir.associations.models import AssociationDeposit
from tapir.associations.services.association_deposit_overview_provider import (
    AssociationDepositOverviewProvider,
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
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestDepositDepartureExport(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_csvExport_reportsHistoricalDepositForRejoinedMember(self):
        mock_timezone(self, datetime.datetime(2026, 11, 5, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        member = MemberFactory(is_superuser=True)
        departed = AssociationMembershipFactory(
            member=member,
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
        )
        current = AssociationMembershipFactory(
            member=member,
            start_date=datetime.date(2026, 3, 1),
            end_date=datetime.date(2026, 12, 31),
        )
        AssociationDeposit.objects.create(
            membership=departed, payment=PaymentFactory(amount=200)
        )
        AssociationDeposit.objects.create(
            membership=current, payment=PaymentFactory(amount=250, transaction=None)
        )
        AssociationMembershipFactory(
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
        self.assertIn("2025-12-31", csv)
        self.assertIn("200,00", csv)
        self.assertNotIn("250,00", csv)
        overview = AssociationDepositOverviewProvider.annotate_members(
            Member.objects.filter(pk=member.pk), {}
        ).get()
        self.assertEqual(Decimal("250"), overview.deposit_agreed)
        self.assertEqual(Decimal("0"), overview.deposit_exported)

    def test_doAutomatedCsvExports_yearlyTemplate_exportsPreviousYearOnce(self):
        mock_timezone(self, datetime.datetime(2026, 1, 2, 12))
        self._set_parameter(
            ParameterKeys.ORGANISATION_LEGAL_STATUS, LEGAL_STATUS_ASSOCIATION
        )
        for year, amount in ((2024, 300), (2025, 200)):
            membership = AssociationMembershipFactory(
                start_date=datetime.date(year, 1, 1),
                end_date=datetime.date(year, 12, 31),
            )
            AssociationDeposit.objects.create(
                membership=membership, payment=PaymentFactory(amount=amount)
            )
        CsvExportTemplateManager.create_exports_from_template(
            "association_deposit_departures", {}
        )
        export = CsvExport.objects.get()
        self.assertEqual([], export.email_recipients)
        AutomatedExportsManager.do_automated_csv_exports({})
        AutomatedExportsManager.do_automated_csv_exports({})
        file = AutomatedCsvExportResult.objects.get().file
        self.assertTrue(file.requires_coop_manage)
        self.client.force_login(MemberFactory())
        with patch.object(
            KeycloakUser,
            "has_perm",
            autospec=True,
            side_effect=lambda _, perm, obj=None: perm == Permission.Coop.VIEW,
        ):
            self.assertEqual(
                403,
                self.client.get(
                    reverse("wirgarten:exported_files_download", args=[file.pk])
                ).status_code,
            )
            response = self.client.get(reverse("wirgarten:exported_files_list"))
            self.assertNotIn(file, response.context["object_list"])
        csv = bytes(file.file).decode()
        self.assertIn("2025-12-31", csv)
        self.assertIn("200,00", csv)
        self.assertNotIn("2024-12-31", csv)
