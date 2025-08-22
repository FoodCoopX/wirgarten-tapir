from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestGetAllowedRhythms(SimpleTestCase):
    @patch(
        "tapir.payments.services.member_payment_rhythm_service.get_parameter_value",
        autospec=True,
    )
    def test_getAllowedRhythms_default_returnsChoicesCorrespondingToConfig(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = "Monatlich,Vierteljährlich"
        cache = Mock()

        result = MemberPaymentRhythmService.get_allowed_rhythms(cache=cache)

        self.assertEqual(
            [MemberPaymentRhythm.Rhythm.MONTHLY, MemberPaymentRhythm.Rhythm.QUARTERLY],
            result,
        )

        mock_get_parameter_value.assert_called_once_with(
            key=ParameterKeys.PAYMENT_ALLOWED_RHYTHMS, cache=cache
        )
