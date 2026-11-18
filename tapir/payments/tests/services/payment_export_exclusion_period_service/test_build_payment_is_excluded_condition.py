import datetime

from tapir.payments.config import PAYMENT_TYPE_COOP_SHARES
from tapir.payments.services.payment_export_exclusion_period_service import (
    PaymentExportExclusionPeriodService,
)
from tapir.payments.tests.factories import PaymentExportExclusionPeriodFactory
from tapir.wirgarten.models import Payment, Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PaymentFactory,
    MemberFactory,
    PaymentTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestBuildPaymentIsExcludedCondition(TapirIntegrationTest):
    DUE_DATE = datetime.date(year=2026, month=6, day=1)

    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_buildPaymentIsExcludedCondition_featureEnabled_sameResultAsIsPaymentExcluded(
        self,
    ):
        self._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=True
        )
        self._create_payments_in_all_states()

        self._assert_condition_matches_is_payment_excluded()

    def test_buildPaymentIsExcludedCondition_featureDisabled_sameResultAsIsPaymentExcluded(
        self,
    ):
        self._set_parameter(
            key=ParameterKeys.PAYMENT_EXPORT_EXCLUSION_ENABLED, value=False
        )
        self._create_payments_in_all_states()

        self._assert_condition_matches_is_payment_excluded()

    def _create_payments_in_all_states(self) -> None:
        excluded_member = MemberFactory.create()
        PaymentExportExclusionPeriodFactory.create(
            member=excluded_member, start_date=self.DUE_DATE, end_date=None
        )
        other_member = MemberFactory.create()

        for member in [excluded_member, other_member]:
            for payment_type in ["Gemüse", PAYMENT_TYPE_COOP_SHARES]:
                self._create_payment(member=member, payment_type=payment_type)
                for excluded_from_export in [True, False]:
                    self._create_payment(
                        member=member,
                        payment_type=payment_type,
                        exported=True,
                        excluded_from_export=excluded_from_export,
                    )

    def _create_payment(
        self,
        member: Member,
        payment_type: str,
        exported: bool = False,
        excluded_from_export: bool = False,
    ) -> None:
        PaymentFactory.create(
            mandate_ref__member=member,
            due_date=self.DUE_DATE,
            type=payment_type,
            transaction=PaymentTransactionFactory.create() if exported else None,
            excluded_from_export=excluded_from_export,
        )

    def _assert_condition_matches_is_payment_excluded(self) -> None:
        cache = {}
        excluded_ids = set(
            Payment.objects.filter(
                PaymentExportExclusionPeriodService.build_payment_is_excluded_condition(
                    cache=cache
                )
            ).values_list("id", flat=True)
        )

        payments = Payment.objects.select_related("mandate_ref")
        self.assertEqual(12, payments.count())
        for payment in payments:
            self.assertEqual(
                PaymentExportExclusionPeriodService.is_payment_excluded(
                    payment=payment, cache=cache
                ),
                payment.id in excluded_ids,
                f"type={payment.type}, exported={payment.transaction_id is not None}, "
                f"flag={payment.excluded_from_export}",
            )
