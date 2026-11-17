import datetime

from django.urls import reverse

from tapir.payments.models import (
    PaymentExportExclusionPeriod,
    PaymentExportExclusionPeriodDeletedLogEntry,
)
from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentExportExclusionPeriodApiViewDelete(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=True
        )

    def test_delete_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        period = PaymentExportExclusionPeriodFactory.create()

        response = self.client.delete(
            reverse("payments:payment_export_exclusion_periods"),
            query_params={"period_id": period.id},
        )

        self.assertStatusCode(response, 403)
        self.assertTrue(PaymentExportExclusionPeriod.objects.exists())

    def test_delete_featureDisabled_returns403(self):
        self._login_as_admin()
        self._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=False
        )
        period = PaymentExportExclusionPeriodFactory.create()

        response = self.client.delete(
            reverse("payments:payment_export_exclusion_periods"),
            query_params={"period_id": period.id},
        )

        self.assertStatusCode(response, 403)
        self.assertTrue(PaymentExportExclusionPeriod.objects.exists())

    def test_delete_default_deletesPeriodAndCreatesLogEntry(self):
        admin = self._login_as_admin()
        period = PaymentExportExclusionPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1), end_date=None
        )
        other_period = PaymentExportExclusionPeriodFactory.create()

        response = self.client.delete(
            reverse("payments:payment_export_exclusion_periods"),
            query_params={"period_id": period.id},
        )

        self.assertStatusCode(response, 200)
        self.assertEqual(
            [other_period], list(PaymentExportExclusionPeriod.objects.all())
        )
        log_entry = PaymentExportExclusionPeriodDeletedLogEntry.objects.get()
        self.assertEqual(admin.id, log_entry.actor_id)
        self.assertEqual(period.member_id, log_entry.user_id)
        self.assertEqual("2026-01-01", log_entry.values["start_date"])

    def test_delete_unknownPeriodId_returns404(self):
        self._login_as_admin()

        response = self.client.delete(
            reverse("payments:payment_export_exclusion_periods"),
            query_params={"period_id": "unknown"},
        )

        self.assertStatusCode(response, 404)
