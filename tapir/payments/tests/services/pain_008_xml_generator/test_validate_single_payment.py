import datetime

from tapir.payments.services.pain_008_xml_string_generator import (
    Pain008XmlStringGenerator,
    Pain008XmlSinglePaymentException,
)
from tapir.wirgarten.tests.factories import PaymentFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestValidateSinglePayment(TapirUnitTest):
    def test_validateSinglePayment_invalidIban_raisesSinglePaymentException(self):
        payment = PaymentFactory.build(
            mandate_ref__member__first_name="John",
            mandate_ref__member__last_name="Doe",
            mandate_ref__member__member_no=12,
            mandate_ref__member__iban="DE00123456781234567890",
        )

        with self.assertRaises(Pain008XmlSinglePaymentException) as context:
            Pain008XmlStringGenerator.validate_single_payment(
                payment=payment, cache={}, collection_date=datetime.date(2026, 1, 1)
            )

        self.assertEqual(
            "Mitglied John Doe #12: Ungültige IBAN.", context.exception.message
        )
