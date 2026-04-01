import datetime

from tapir.payments.services.month_payment_builder import MonthPaymentBuilder
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PaymentFactory,
    MandateReferenceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCombineSimilarPayments(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_combineSimilarPayments_default_onlySimilarPaymentsGetCombined(self):
        member_1 = MemberFactory.create()
        mandate_ref_1 = MandateReferenceFactory.create(
            member=member_1, ref="test_ref_1"
        )
        member_2 = MemberFactory.create()
        mandate_ref_2 = MandateReferenceFactory.create(
            member=member_2, ref="test_ref_2"
        )
        type_1 = "test_type_1"
        type_2 = "test_type_2"
        due_date_1 = datetime.date(year=2024, month=6, day=1)
        due_date_2 = datetime.date(year=2024, month=6, day=2)

        payment_a = PaymentFactory.build(
            mandate_ref=mandate_ref_1,
            type=type_1,
            due_date=due_date_1,
            amount=1.25,
            subscription_payment_range_start=datetime.date(year=2024, month=5, day=15),
            subscription_payment_range_end=datetime.date(year=2024, month=5, day=31),
        )
        payment_b = PaymentFactory.build(
            mandate_ref=mandate_ref_1,
            type=type_1,
            due_date=due_date_1,
            amount=2.33,
            subscription_payment_range_start=datetime.date(year=2024, month=6, day=1),
            subscription_payment_range_end=datetime.date(year=2024, month=6, day=27),
        )
        payment_c = PaymentFactory.build(
            mandate_ref=mandate_ref_2, type=type_1, due_date=due_date_1, amount=1
        )
        payment_d = PaymentFactory.build(
            mandate_ref=mandate_ref_1, type=type_2, due_date=due_date_1, amount=1
        )
        payment_e = PaymentFactory.build(
            mandate_ref=mandate_ref_1, type=type_1, due_date=due_date_2, amount=1
        )

        result = MonthPaymentBuilder.combine_similar_payments(
            [payment_a, payment_b, payment_c, payment_d, payment_e]
        )

        # A and B should get combined, others should stay the same
        self.assertEqual(4, len(result))

        self.assertNotIn(payment_a, result)
        self.assertNotIn(payment_b, result)
        self.assertIn(payment_c, result)
        self.assertIn(payment_d, result)
        self.assertIn(payment_e, result)

        for payment in result:
            if (
                payment.mandate_ref.member == member_1
                and payment.type == type_1
                and payment.due_date == due_date_1
            ):
                self.assertEqual(1.25 + 2.33, payment.amount)
                self.assertEqual(
                    datetime.date(year=2024, month=5, day=15),
                    payment.subscription_payment_range_start,
                )
                self.assertEqual(
                    datetime.date(year=2024, month=6, day=27),
                    payment.subscription_payment_range_end,
                )
