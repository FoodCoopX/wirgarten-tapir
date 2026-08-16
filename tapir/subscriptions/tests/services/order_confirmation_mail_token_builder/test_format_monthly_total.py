import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from tapir.solidarity_contribution.models import SolidarityContribution
from tapir.subscriptions.services.order_confirmation_mail_token_builder import (
    OrderConfirmationMailTokenBuilder,
)
from tapir.wirgarten.tests.factories import SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestFormatMonthlyTotal(TapirUnitTest):
    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.SubscriptionPriceCalculator.get_monthly_price",
        autospec=True,
    )
    def test_formatMonthlyTotal_subscriptionsAndSolidarity_sumsBoth(
        self, mock_get_monthly_price: Mock
    ):
        reference_date = datetime.date(year=2026, month=5, day=11)
        cache = {}
        subscription_1 = SubscriptionFactory.build()
        subscription_2 = SubscriptionFactory.build()
        mock_get_monthly_price.side_effect = [Decimal("10.00"), Decimal("7.50")]
        solidarity_contribution = SolidarityContribution(
            amount=Decimal("12.00"),
        )

        result = OrderConfirmationMailTokenBuilder.format_monthly_total(
            subscriptions=[subscription_1, subscription_2],
            solidarity_contribution=solidarity_contribution,
            reference_date=reference_date,
            cache=cache,
        )

        self.assertEqual("29,50", result)

    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.SubscriptionPriceCalculator.get_monthly_price",
        autospec=True,
    )
    def test_formatMonthlyTotal_noSolidarity_sumsOnlySubscriptions(
        self, mock_get_monthly_price: Mock
    ):
        reference_date = Mock()
        cache = {}
        mock_get_monthly_price.return_value = Decimal("8.00")

        result = OrderConfirmationMailTokenBuilder.format_monthly_total(
            subscriptions=[SubscriptionFactory.build()],
            solidarity_contribution=None,
            reference_date=reference_date,
            cache=cache,
        )

        self.assertEqual("8,00", result)

    def test_formatMonthlyTotal_noSubscriptions_returnsSolidarityOnly(self):
        result = OrderConfirmationMailTokenBuilder.format_monthly_total(
            subscriptions=[],
            solidarity_contribution=SolidarityContribution(amount=Decimal("4.20")),
            reference_date=Mock(),
            cache={},
        )

        self.assertEqual("4,20", result)

    @patch(
        "tapir.subscriptions.services.order_confirmation_mail_token_builder.SubscriptionPriceCalculator.get_monthly_price",
        autospec=True,
    )
    def test_formatMonthlyTotal_solidarityAmountIsFloat_stillAddsIt(
        self, mock_get_monthly_price: Mock
    ):
        mock_get_monthly_price.return_value = Decimal("10.00")
        solidarity_contribution = SolidarityContribution(amount=12.70)

        result = OrderConfirmationMailTokenBuilder.format_monthly_total(
            subscriptions=[SubscriptionFactory.build()],
            solidarity_contribution=solidarity_contribution,
            reference_date=Mock(),
            cache={},
        )

        self.assertEqual("22,70", result)
