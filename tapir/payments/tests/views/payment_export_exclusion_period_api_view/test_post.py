import datetime

from django.urls import reverse

from tapir.payments.models import (
    PaymentExportExclusionPeriod,
    PaymentExportExclusionPeriodCreatedLogEntry,
)
from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentExportExclusionPeriodApiViewPost(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=True
        )

    def test_post_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self._post(member=member, start_date="2026-01-01", end_date=None)

        self.assertStatusCode(response, 403)
        self.assertFalse(PaymentExportExclusionPeriod.objects.exists())

    def test_post_featureDisabled_returns403(self):
        self._login_as_admin()
        self._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=False
        )
        member = MemberFactory.create()

        response = self._post(member=member, start_date="2026-01-01", end_date=None)

        self.assertStatusCode(response, 403)
        self.assertFalse(PaymentExportExclusionPeriod.objects.exists())

    def test_post_default_createsPeriodAndLogEntry(self):
        admin = self._login_as_admin()
        member = MemberFactory.create()

        response = self._post(
            member=member, start_date="2026-01-01", end_date="2026-12-31"
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response_content=response.json())
        period = PaymentExportExclusionPeriod.objects.get()
        self.assertEqual(member.id, period.member_id)
        self.assertEqual(datetime.date(year=2026, month=1, day=1), period.start_date)
        self.assertEqual(datetime.date(year=2026, month=12, day=31), period.end_date)
        self.assertEqual("Kredit", period.comment)
        log_entry = PaymentExportExclusionPeriodCreatedLogEntry.objects.get()
        self.assertEqual(admin.id, log_entry.actor_id)
        self.assertEqual(member.id, log_entry.user_id)
        self.assertEqual("2026-01-01", log_entry.values["start_date"])

    def test_post_noEndDate_createsOpenEndedPeriod(self):
        self._login_as_admin()
        member = MemberFactory.create()

        response = self._post(member=member, start_date="2026-01-01", end_date=None)

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response_content=response.json())
        self.assertIsNone(PaymentExportExclusionPeriod.objects.get().end_date)

    def test_post_endDateBeforeStartDate_returnsErrorAndCreatesNothing(self):
        self._login_as_admin()
        member = MemberFactory.create()

        response = self._post(
            member=member, start_date="2026-03-01", end_date="2026-02-28"
        )

        self.assertStatusCode(response, 200)
        self.assert_order_not_confirmed(
            response_content=response.json(),
            expected_error="Das End-Datum darf nicht vor dem Start-Datum liegen",
        )
        self.assertFalse(PaymentExportExclusionPeriod.objects.exists())
        self.assertFalse(PaymentExportExclusionPeriodCreatedLogEntry.objects.exists())

    def test_post_datesNotOnMonthBoundaries_returnsErrorAndCreatesNothing(self):
        self._login_as_admin()
        member = MemberFactory.create()

        response = self._post(
            member=member, start_date="2026-03-15", end_date="2026-04-14"
        )

        self.assertStatusCode(response, 200)
        self.assert_order_not_confirmed(
            response_content=response.json(),
            expected_error="Das Start-Datum muss der erste Tag eines Monats sein",
        )
        self.assertFalse(PaymentExportExclusionPeriod.objects.exists())

    def test_post_overlapsExistingPeriod_returnsErrorAndCreatesNothing(self):
        self._login_as_admin()
        existing_period = PaymentExportExclusionPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1), end_date=None
        )

        response = self._post(
            member=existing_period.member,
            start_date="2027-01-01",
            end_date="2027-03-31",
        )

        self.assertStatusCode(response, 200)
        self.assert_order_not_confirmed(
            response_content=response.json(),
            expected_error="Der Zeitraum überschneidet sich mit dem bestehenden Zeitraum 01.01.2026 - unbefristet",
        )
        self.assertEqual(1, PaymentExportExclusionPeriod.objects.count())

    def _post(self, member: Member, start_date: str, end_date: str | None):
        return self.client.post(
            reverse("payments:payment_export_exclusion_periods"),
            data={
                "member_id": member.id,
                "start_date": start_date,
                "end_date": end_date,
                "comment": "Kredit",
            },
            content_type="application/json",
        )
