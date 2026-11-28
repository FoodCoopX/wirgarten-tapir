import datetime
from unittest.mock import patch, MagicMock

from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.payment_export_exclusion_period_service import (
    PaymentExportExclusionPeriodService,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.models import Payment
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import (
    PaymentFactory,
    MandateReferenceFactory,
    MemberFactory,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    PaymentExportExclusionPeriodService,
    "is_member_excluded",
    autospec=True,
    return_value=True,
)
class TestIsPaymentExcluded(TapirUnitTest):
    def test_isPaymentExcluded_exportedAndFlagged_returnsTrueWithoutCheckingPeriods(
        self, mock_is_member_excluded: MagicMock
    ):
        payment = self._build_payment(transaction_id="transaction_id")
        payment.excluded_from_export = True

        result = PaymentExportExclusionPeriodService.is_payment_excluded(
            payment=payment, cache=self._build_cache(enabled=False)
        )

        self.assertTrue(result)
        mock_is_member_excluded.assert_not_called()

    def test_isPaymentExcluded_exportedAndNotFlagged_returnsFalseWithoutCheckingPeriods(
        self, mock_is_member_excluded: MagicMock
    ):
        payment = self._build_payment(transaction_id="transaction_id")

        result = PaymentExportExclusionPeriodService.is_payment_excluded(
            payment=payment, cache=self._build_cache(enabled=True)
        )

        self.assertFalse(result)
        mock_is_member_excluded.assert_not_called()

    def test_isPaymentExcluded_featureDisabled_returnsFalse(
        self, mock_is_member_excluded: MagicMock
    ):
        result = PaymentExportExclusionPeriodService.is_payment_excluded(
            payment=self._build_payment(), cache=self._build_cache(enabled=False)
        )

        self.assertFalse(result)
        mock_is_member_excluded.assert_not_called()

    def test_isPaymentExcluded_coopSharePayment_returnsFalse(
        self, mock_is_member_excluded: MagicMock
    ):
        payment = self._build_payment(payment_type=PAYMENT_TYPE_COOP_SHARES)

        result = PaymentExportExclusionPeriodService.is_payment_excluded(
            payment=payment, cache=self._build_cache(enabled=True)
        )

        self.assertFalse(result)
        mock_is_member_excluded.assert_not_called()

    def test_isPaymentExcluded_notExported_returnsWhetherMemberIsExcludedAtDueDate(
        self, mock_is_member_excluded: MagicMock
    ):
        payment = self._build_payment()
        cache = self._build_cache(enabled=True)

        result = PaymentExportExclusionPeriodService.is_payment_excluded(
            payment=payment, cache=cache
        )

        self.assertTrue(result)
        mock_is_member_excluded.assert_called_once_with(
            member_id=payment.mandate_ref.member_id,
            reference_date=payment.due_date,
            cache=cache,
        )

    @staticmethod
    def _build_payment(
        transaction_id: str | None = None, payment_type: str = "Gemüse"
    ) -> Payment:
        payment = PaymentFactory.build(
            mandate_ref=MandateReferenceFactory.build(
                member=MemberFactory.build(id="member_id")
            ),
            due_date=datetime.date(year=2026, month=6, day=1),
            type=payment_type,
            transaction=None,
        )
        payment.transaction_id = transaction_id
        return payment

    @staticmethod
    def _build_cache(enabled: bool) -> dict:
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED,
            value=enabled,
        )
        return cache
