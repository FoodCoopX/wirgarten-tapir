from decimal import Decimal
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductFactory,
    ProductTypeFactory,
    GrowingPeriodFactory,
    MandateReferenceFactory,
)


class TestBuildRenewedSubscription(SimpleTestCase):
    @patch.object(
        AutomaticSubscriptionRenewalService, "get_renewed_subscription_trial_data"
    )
    @patch.object(NoticePeriodManager, "get_notice_period_duration")
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_next_growing_period"
    )
    def test_buildRenewedSubscription_default_buildsFutureSubscription(
        self,
        mock_get_next_growing_period: Mock,
        mock_get_notice_period_duration: Mock,
        mock_get_renewed_subscription_trial_data: Mock,
    ):
        product_type = ProductTypeFactory.build()
        product = ProductFactory.build()
        product.type = product_type

        original_subscription = Mock()
        member = MemberFactory.build()
        original_subscription.member = member
        original_subscription.product = product
        original_subscription.quantity = 3
        original_subscription.solidarity_price_percentage = 1.2
        original_subscription.solidarity_price_absolute = Decimal("3.6")
        mandate_ref = MandateReferenceFactory.build(ref="test_ref")
        original_subscription.mandate_ref = mandate_ref
        admin_confirmed = Mock()
        original_subscription.admin_confirmed = admin_confirmed

        next_growing_period = GrowingPeriodFactory.build()
        start_date = Mock()
        next_growing_period.start_date = start_date
        end_date = Mock()
        next_growing_period.end_date = end_date
        mock_get_next_growing_period.return_value = next_growing_period

        mock_get_notice_period_duration.return_value = 4

        trial_disabled = Mock()
        trial_end_date_override = Mock()
        mock_get_renewed_subscription_trial_data.return_value = (
            trial_disabled,
            trial_end_date_override,
        )

        cache = {}
        future_subscription = (
            AutomaticSubscriptionRenewalService.build_renewed_subscription(
                original_subscription, cache=cache
            )
        )

        mock_get_next_growing_period.assert_called_once_with(cache=cache)
        mock_get_notice_period_duration.assert_called_once_with(
            product_type, next_growing_period, cache=cache
        )

        self.assertEqual(member, future_subscription.member)
        self.assertEqual(next_growing_period, future_subscription.period)
        self.assertEqual(product, future_subscription.product)
        self.assertEqual(3, future_subscription.quantity)
        self.assertEqual(start_date, future_subscription.start_date)
        self.assertEqual(end_date, future_subscription.end_date)
        self.assertEqual(1.2, future_subscription.solidarity_price_percentage)
        self.assertEqual(Decimal("3.6"), future_subscription.solidarity_price_absolute)
        self.assertEqual(mandate_ref, future_subscription.mandate_ref)
        self.assertEqual(trial_disabled, future_subscription.trial_disabled)
        self.assertEqual(
            trial_end_date_override, future_subscription.trial_end_date_override
        )
        self.assertEqual(4, future_subscription.notice_period_duration)
        self.assertEqual(admin_confirmed, future_subscription.admin_confirmed)
        return
