import datetime

from tapir.payments.models import MemberPaymentRhythm
from tapir.subscriptions.services.order_confirmation_mail_token_builder import (
    OrderConfirmationMailTokenBuilder,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetPaymentRhythmText(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_getPaymentRhythmText_default_returnsDisplayName(self):
        now = mock_timezone(self, datetime.datetime(year=2026, month=5, day=11))
        member = MemberFactory.create()
        MemberPaymentRhythm.objects.create(
            member=member,
            rhythm=MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            valid_from=now.date(),
        )

        result = OrderConfirmationMailTokenBuilder.get_payment_rhythm_text(
            member=member, cache={}
        )

        self.assertEqual("Halbjährlich", result)
