from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)


class TestValidateRhythms(SimpleTestCase):
    def test_validateRhythms_inputContainsInvalidValue_raisesException(self):
        input = "Monatlich,Wöchentlich"

        with self.assertRaises(ValidationError):
            MemberPaymentRhythmService.validate_rhythms(input)

    def test_validateRhythms_inputIsValid_doesntRaiseException(self):
        input = "Monatlich,Halbjährlich"

        MemberPaymentRhythmService.validate_rhythms(input)
