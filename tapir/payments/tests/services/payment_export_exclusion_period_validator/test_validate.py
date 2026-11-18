import datetime
from unittest.mock import patch, MagicMock

from django.core.exceptions import ValidationError

from tapir.payments.models import PaymentExportExclusionPeriod
from tapir.payments.services.payment_export_exclusion_period_validator import (
    PaymentExportExclusionPeriodValidator,
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
class TestValidate(TapirUnitTest):
    def test_validate_noOtherPeriod_doesNotRaise(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        cache = {}

        PaymentExportExclusionPeriodValidator.validate(
            member_id="member_id",
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=3, day=31),
            period_id_being_edited=None,
            cache=cache,
        )

        mock_get_payment_export_exclusion_periods_for_member.assert_called_once_with(
            member_id="member_id", cache=cache
        )

    def test_validate_endDateBeforeStartDate_raisesError(self, _: MagicMock):
        with self.assertRaisesMessage(
            ValidationError, "Das End-Datum darf nicht vor dem Start-Datum liegen"
        ):
            PaymentExportExclusionPeriodValidator.validate(
                member_id="member_id",
                start_date=datetime.date(year=2026, month=3, day=1),
                end_date=datetime.date(year=2026, month=2, day=28),
                period_id_being_edited=None,
                cache={},
            )

    def test_validate_periodCoversSingleMonth_doesNotRaise(self, _: MagicMock):
        PaymentExportExclusionPeriodValidator.validate(
            member_id="member_id",
            start_date=datetime.date(year=2026, month=3, day=1),
            end_date=datetime.date(year=2026, month=3, day=31),
            period_id_being_edited=None,
            cache={},
        )

    def test_validate_startDateNotFirstOfMonth_raisesError(self, _: MagicMock):
        with self.assertRaisesMessage(
            ValidationError,
            "Das Start-Datum muss der erste Tag eines Monats sein",
        ):
            PaymentExportExclusionPeriodValidator.validate(
                member_id="member_id",
                start_date=datetime.date(year=2026, month=3, day=2),
                end_date=datetime.date(year=2026, month=3, day=31),
                period_id_being_edited=None,
                cache={},
            )

    def test_validate_endDateNotLastOfMonth_raisesError(self, _: MagicMock):
        with self.assertRaisesMessage(
            ValidationError,
            "Das End-Datum muss der letzte Tag eines Monats sein",
        ):
            PaymentExportExclusionPeriodValidator.validate(
                member_id="member_id",
                start_date=datetime.date(year=2026, month=3, day=1),
                end_date=datetime.date(year=2026, month=3, day=30),
                period_id_being_edited=None,
                cache={},
            )

    def test_validate_openEndedPeriodStartingFirstOfMonth_doesNotRaise(
        self, _: MagicMock
    ):
        PaymentExportExclusionPeriodValidator.validate(
            member_id="member_id",
            start_date=datetime.date(year=2026, month=3, day=1),
            end_date=None,
            period_id_being_edited=None,
            cache={},
        )

    def test_validate_endDateIsLastDayOfFebruaryInLeapYear_doesNotRaise(
        self, _: MagicMock
    ):
        PaymentExportExclusionPeriodValidator.validate(
            member_id="member_id",
            start_date=datetime.date(year=2028, month=2, day=1),
            end_date=datetime.date(year=2028, month=2, day=29),
            period_id_being_edited=None,
            cache={},
        )

    def test_validate_overlapsOtherPeriod_raisesError(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2026, month=1, day=1), end_date=None
            )
        ]

        with self.assertRaisesMessage(
            ValidationError,
            "Der Zeitraum überschneidet sich mit dem bestehenden Zeitraum 01.01.2026 - unbefristet",
        ):
            PaymentExportExclusionPeriodValidator.validate(
                member_id="member_id",
                start_date=datetime.date(year=2026, month=6, day=1),
                end_date=datetime.date(year=2026, month=6, day=30),
                period_id_being_edited=None,
                cache={},
            )

    def test_validate_doesNotOverlapOtherPeriod_doesNotRaise(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            self._build_period(
                start_date=datetime.date(year=2026, month=1, day=1),
                end_date=datetime.date(year=2026, month=5, day=31),
            )
        ]

        PaymentExportExclusionPeriodValidator.validate(
            member_id="member_id",
            start_date=datetime.date(year=2026, month=6, day=1),
            end_date=None,
            period_id_being_edited=None,
            cache={},
        )

    def test_validate_onlyOverlapsPeriodBeingEdited_doesNotRaise(
        self, mock_get_payment_export_exclusion_periods_for_member: MagicMock
    ):
        stored_period = self._build_period(
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=datetime.date(year=2026, month=3, day=31),
        )
        mock_get_payment_export_exclusion_periods_for_member.return_value = [
            stored_period
        ]

        PaymentExportExclusionPeriodValidator.validate(
            member_id="member_id",
            start_date=datetime.date(year=2026, month=1, day=1),
            end_date=None,
            period_id_being_edited=stored_period.id,
            cache={},
        )

    @staticmethod
    def _build_period(
        start_date: datetime.date, end_date: datetime.date | None
    ) -> PaymentExportExclusionPeriod:
        return PaymentExportExclusionPeriodFactory.build(
            start_date=start_date, end_date=end_date
        )
