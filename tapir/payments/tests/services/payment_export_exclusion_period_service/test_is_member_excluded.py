import datetime
from unittest.mock import patch, MagicMock

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
class TestIsMemberExcluded(TapirUnitTest):
    def test_isMemberExcluded_memberHasNoPeriod_returnsFalse(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        cache = {}

        result = PaymentExportExclusionPeriodService.is_member_excluded(
            member_id="member_id",
            reference_date=datetime.date(year=2026, month=6, day=1),
            cache=cache,
        )

        self.assertFalse(result)
        mock_get_payment_export_exclusion_periods_for_member.assert_called_once_with(
            member_id="member_id", cache=cache
        )

    def test_isMemberExcluded_dateBeforePeriod_returnsFalse(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2026, month=6, day=1),
                end_date=datetime.date(year=2026, month=8, day=31),
            )
        ]

        result = PaymentExportExclusionPeriodService.is_member_excluded(
            member_id="member_id",
            reference_date=datetime.date(year=2026, month=5, day=31),
            cache={},
        )

        self.assertFalse(result)

    def test_isMemberExcluded_dateAfterPeriod_returnsFalse(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2026, month=6, day=1),
                end_date=datetime.date(year=2026, month=8, day=31),
            )
        ]

        result = PaymentExportExclusionPeriodService.is_member_excluded(
            member_id="member_id",
            reference_date=datetime.date(year=2026, month=9, day=1),
            cache={},
        )

        self.assertFalse(result)

    def test_isMemberExcluded_dateOnStartOfPeriod_returnsTrue(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2026, month=6, day=1),
                end_date=datetime.date(year=2026, month=8, day=31),
            )
        ]

        result = PaymentExportExclusionPeriodService.is_member_excluded(
            member_id="member_id",
            reference_date=datetime.date(year=2026, month=6, day=1),
            cache={},
        )

        self.assertTrue(result)

    def test_isMemberExcluded_dateOnEndOfPeriod_returnsTrue(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2026, month=6, day=1),
                end_date=datetime.date(year=2026, month=8, day=31),
            )
        ]

        result = PaymentExportExclusionPeriodService.is_member_excluded(
            member_id="member_id",
            reference_date=datetime.date(year=2026, month=8, day=31),
            cache={},
        )

        self.assertTrue(result)

    def test_isMemberExcluded_periodWithoutEndDate_returnsTrue(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2026, month=6, day=1), end_date=None
            )
        ]

        result = PaymentExportExclusionPeriodService.is_member_excluded(
            member_id="member_id",
            reference_date=datetime.date(year=2040, month=1, day=1),
            cache={},
        )

        self.assertTrue(result)

    def test_isMemberExcluded_dateWithinSecondPeriod_returnsTrue(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2025, month=1, day=1),
                end_date=datetime.date(year=2025, month=3, day=31),
            ),
            self._build_period(
                start_date=datetime.date(year=2026, month=1, day=1),
                end_date=datetime.date(year=2026, month=3, day=31),
            ),
        ]

        result = PaymentExportExclusionPeriodService.is_member_excluded(
            member_id="member_id",
            reference_date=datetime.date(year=2026, month=2, day=15),
            cache={},
        )

        self.assertTrue(result)

    @staticmethod
    def _build_period(start_date: datetime.date, end_date: datetime.date | None):
        return PaymentExportExclusionPeriodFactory.build(
            start_date=start_date, end_date=end_date
        )
