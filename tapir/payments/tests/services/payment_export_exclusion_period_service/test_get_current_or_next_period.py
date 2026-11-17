import datetime
from unittest.mock import patch, MagicMock

from tapir.payments.models import PaymentExportExclusionPeriod
from tapir.payments.services.payment_export_exclusion_period_service import (
    PaymentExportExclusionPeriodService,
)
from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    TapirCache,
    "get_payment_export_exclusion_periods_for_member",
    autospec=True,
    return_value=[],
)
class TestGetCurrentOrNextPeriod(TapirUnitTest):
    REFERENCE_DATE = datetime.date(year=2026, month=6, day=15)

    def test_getCurrentOrNextPeriod_memberHasNoPeriod_returnsNone(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        cache = {}

        result = PaymentExportExclusionPeriodService.get_current_or_next_period(
            member_id="member_id", reference_date=self.REFERENCE_DATE, cache=cache
        )

        self.assertIsNone(result)
        mock_get_payment_export_exclusion_periods_for_member.assert_called_once_with(
            member_id="member_id", cache=cache
        )

    def test_getCurrentOrNextPeriod_onlyPastPeriod_returnsNone(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2026, month=1, day=1),
                end_date=datetime.date(year=2026, month=5, day=31),
            )
        ]

        result = PaymentExportExclusionPeriodService.get_current_or_next_period(
            member_id="member_id", reference_date=self.REFERENCE_DATE, cache={}
        )

        self.assertIsNone(result)

    def test_getCurrentOrNextPeriod_pastAndCurrentPeriod_returnsCurrentPeriod(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        current_period = self._build_period(
            start_date=datetime.date(year=2026, month=6, day=1),
            end_date=datetime.date(year=2026, month=6, day=30),
        )
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2026, month=1, day=1),
                end_date=datetime.date(year=2026, month=5, day=31),
            ),
            current_period,
        ]

        result = PaymentExportExclusionPeriodService.get_current_or_next_period(
            member_id="member_id", reference_date=self.REFERENCE_DATE, cache={}
        )

        self.assertEqual(current_period, result)

    def test_getCurrentOrNextPeriod_openEndedPeriodStartedInThePast_returnsPeriod(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        period = self._build_period(
            start_date=datetime.date(year=2020, month=1, day=1), end_date=None
        )
        mock_get_payment_export_exclusion_periods_for_member.return_value = [period]

        result = PaymentExportExclusionPeriodService.get_current_or_next_period(
            member_id="member_id", reference_date=self.REFERENCE_DATE, cache={}
        )

        self.assertEqual(period, result)

    def test_getCurrentOrNextPeriod_twoFuturePeriods_returnsEarliest(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        next_period = self._build_period(
            start_date=datetime.date(year=2026, month=7, day=1),
            end_date=datetime.date(year=2026, month=7, day=31),
        )
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            next_period,
            self._build_period(
                start_date=datetime.date(year=2027, month=1, day=1), end_date=None
            ),
        ]

        result = PaymentExportExclusionPeriodService.get_current_or_next_period(
            member_id="member_id", reference_date=self.REFERENCE_DATE, cache={}
        )

        self.assertEqual(next_period, result)

    @staticmethod
    def _build_period(
        start_date: datetime.date, end_date: datetime.date | None
    ) -> PaymentExportExclusionPeriod:
        return PaymentExportExclusionPeriodFactory.build(
            start_date=start_date, end_date=end_date
        )
