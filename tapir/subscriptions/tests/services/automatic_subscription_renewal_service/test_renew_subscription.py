from decimal import Decimal
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.wirgarten.models import Subscription


class TestRenewSubscription(SimpleTestCase):
    @patch.object(
        AutomaticSubscriptionRenewalService, "get_renewed_subscription_trial_data"
    )
    @patch.object(NoticePeriodManager, "get_notice_period_duration")
    @patch.object(Subscription, "objects")
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_next_growing_period"
    )
    def test_renewSubscription_default_createsFutureSubscription(
        self,
        mock_get_next_growing_period: Mock,
        mock_subscription_objects: Mock,
        mock_get_notice_period_duration: Mock,
        mock_get_renewed_subscription_trial_data: Mock,
    ):
        product_type = Mock()
        product = Mock()
        product.type = product_type

        subscription = Mock()
        member = Mock()
        subscription.member = member
        subscription.product = product
        subscription.quantity = 3
        subscription.solidarity_price = 1.2
        subscription.solidarity_price_absolute = Decimal("3.6")
        mandate_ref = Mock()
        subscription.mandate_ref = mandate_ref

        next_growing_period = Mock()
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
        AutomaticSubscriptionRenewalService.renew_subscription(
            subscription, cache=cache
        )

        mock_get_next_growing_period.assert_called_once_with(cache=cache)
        mock_get_notice_period_duration.assert_called_once_with(
            product_type, next_growing_period, cache=cache
        )

        mock_subscription_objects.create.assert_called_once_with(
            member=member,
            period=next_growing_period,
            product=product,
            quantity=3,
            start_date=start_date,
            end_date=end_date,
            solidarity_price=1.2,
            solidarity_price_absolute=Decimal("3.6"),
            mandate_ref=mandate_ref,
            trial_disabled=trial_disabled,
            trial_end_date_override=trial_end_date_override,
            notice_period_duration=4,
        )
