import datetime

from django.urls import reverse

from tapir.payments.models import (
    PaymentExportExclusionPeriod,
    PaymentExportExclusionPeriodUpdatedLogEntry,
)
from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPaymentExportExclusionPeriodApiViewPut(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=True
        )

    def test_put_loggedInAsNormalMember_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        period = self._create_period()

        response = self._put(
            period=period, start_date="2026-01-01", end_date="2027-12-31"
        )

        self.assertStatusCode(response, 403)
        period.refresh_from_db()
        self.assertEqual(datetime.date(year=2026, month=12, day=31), period.end_date)

    def test_put_featureDisabled_returns403(self):
        self._login_as_admin()
        self._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=False
        )
        period = self._create_period()

        response = self._put(
            period=period, start_date="2026-01-01", end_date="2027-12-31"
        )

        self.assertStatusCode(response, 403)
        period.refresh_from_db()
        self.assertEqual(datetime.date(year=2026, month=12, day=31), period.end_date)

    def test_put_default_updatesAllFieldsAndCreatesLogEntry(self):
        admin = self._login_as_admin()
        period = self._create_period()

        response = self._put(
            period=period, start_date="2026-02-01", end_date="2027-12-31"
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response_content=response.json())
        period.refresh_from_db()
        self.assertEqual(datetime.date(year=2026, month=2, day=1), period.start_date)
        self.assertEqual(datetime.date(year=2027, month=12, day=31), period.end_date)
        self.assertEqual("Kredit verlängert", period.comment)
        log_entry = PaymentExportExclusionPeriodUpdatedLogEntry.objects.get()
        self.assertEqual(admin.id, log_entry.actor_id)
        self.assertEqual(period.member_id, log_entry.user_id)
        self.assertEqual("2026-12-31", log_entry.old_values["end_date"])
        self.assertEqual("2027-12-31", log_entry.new_values["end_date"])

    def test_put_removeEndDate_periodBecomesOpenEnded(self):
        self._login_as_admin()
        period = self._create_period()

        response = self._put(period=period, start_date="2026-01-01", end_date=None)

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response_content=response.json())
        period.refresh_from_db()
        self.assertIsNone(period.end_date)

    def test_put_endDateBeforeStartDate_returnsErrorAndChangesNothing(self):
        self._login_as_admin()
        period = self._create_period()

        response = self._put(
            period=period, start_date="2026-03-01", end_date="2026-02-28"
        )

        self.assertStatusCode(response, 200)
        self.assert_order_not_confirmed(
            response_content=response.json(),
            expected_error="Das End-Datum darf nicht vor dem Start-Datum liegen",
        )
        period.refresh_from_db()
        self.assertEqual(datetime.date(year=2026, month=1, day=1), period.start_date)
        self.assertFalse(PaymentExportExclusionPeriodUpdatedLogEntry.objects.exists())

    def test_put_datesNotOnMonthBoundaries_returnsErrorAndChangesNothing(self):
        self._login_as_admin()
        period = self._create_period()

        response = self._put(
            period=period, start_date="2026-01-15", end_date="2026-12-31"
        )

        self.assertStatusCode(response, 200)
        self.assert_order_not_confirmed(
            response_content=response.json(),
            expected_error="Das Start-Datum muss der erste Tag eines Monats sein",
        )
        period.refresh_from_db()
        self.assertEqual(datetime.date(year=2026, month=1, day=1), period.start_date)
        self.assertFalse(PaymentExportExclusionPeriodUpdatedLogEntry.objects.exists())

    def test_put_overlapsOtherPeriodOfSameMember_returnsErrorAndChangesNothing(
        self,
    ):
        self._login_as_admin()
        period = self._create_period()
        PaymentExportExclusionPeriodFactory.create(
            member=period.member,
            start_date=datetime.date(year=2027, month=6, day=1),
            end_date=None,
        )

        response = self._put(
            period=period, start_date="2026-01-01", end_date="2027-12-31"
        )

        self.assertStatusCode(response, 200)
        self.assert_order_not_confirmed(
            response_content=response.json(),
            expected_error="Der Zeitraum überschneidet sich mit dem bestehenden Zeitraum 01.06.2027 - unbefristet",
        )
        period.refresh_from_db()
        self.assertEqual(datetime.date(year=2026, month=12, day=31), period.end_date)

    def test_put_newDatesOverlapOldDatesOfSamePeriod_updatesPeriod(self):
        self._login_as_admin()
        period = self._create_period()

        response = self._put(
            period=period, start_date="2026-06-01", end_date="2027-06-30"
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response_content=response.json())

    def test_put_otherMemberHasOverlappingPeriod_updatesPeriod(self):
        self._login_as_admin()
        period = self._create_period()
        PaymentExportExclusionPeriodFactory.create(
            member=MemberFactory.create(),
            start_date=datetime.date(year=2020, month=1, day=1),
            end_date=None,
        )

        response = self._put(
            period=period, start_date="2026-01-01", end_date="2027-12-31"
        )

        self.assertStatusCode(response, 200)
        self.assert_order_confirmed(response_content=response.json())

    @staticmethod
    def _create_period() -> PaymentExportExclusionPeriod:
        return PaymentExportExclusionPeriodFactory.create(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=12, day=31),
            comment="Kredit",
        )

    def _put(
        self,
        period: PaymentExportExclusionPeriod,
        start_date: str,
        end_date: str | None,
    ):
        return self.client.put(
            reverse("payments:payment_export_exclusion_periods"),
            data={
                "period_id": period.id,
                "start_date": start_date,
                "end_date": end_date,
                "comment": "Kredit verlängert",
            },
            content_type="application/json",
        )
