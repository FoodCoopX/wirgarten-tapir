from unittest.mock import Mock, patch

from tapir.payments.models import MemberPaymentRhythm
from tapir.subscriptions.services.order_confirmation_mail_token_builder import (
    OrderConfirmationMailTokenBuilder,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestGetPaymentRhythmText(TapirUnitTest):
    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.get_today",
        autospec=True,
    )
    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.MemberPaymentRhythmService.get_rhythm_display_name",
        autospec=True,
    )
    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.MemberPaymentRhythmService.get_member_payment_rhythm",
        autospec=True,
    )
    def test_getPaymentRhythmText_default_returnsDisplayName(
        self,
        mock_get_member_payment_rhythm: Mock,
        mock_get_rhythm_display_name: Mock,
        mock_get_today: Mock,
    ):
        member = MemberFactory.build()
        cache = {}
        today = Mock()
        mock_get_today.return_value = today
        mock_get_member_payment_rhythm.return_value = (
            MemberPaymentRhythm.Rhythm.SEMIANNUALLY
        )
        mock_get_rhythm_display_name.return_value = "Halbjährlich"

        result = OrderConfirmationMailTokenBuilder.get_payment_rhythm_text(
            member=member, cache=cache
        )

        self.assertEqual("Halbjährlich", result)
        mock_get_today.assert_called_once_with(cache=cache)
        mock_get_member_payment_rhythm.assert_called_once_with(
            member=member, reference_date=today, cache=cache
        )
        mock_get_rhythm_display_name.assert_called_once_with(
            MemberPaymentRhythm.Rhythm.SEMIANNUALLY
        )
