import datetime
from unittest.mock import patch, Mock

from django.test import SimpleTestCase

from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import mock_timezone


class TestMustSubscriptionBeRenewed(SimpleTestCase):
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_mustSubscriptionBeRenewed_automaticRenewalIsDisabled_returnFalse(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = False

        result = AutomaticSubscriptionRenewalService.must_subscription_be_renewed(
            Mock()
        )

        self.assertFalse(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        )

    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_mustSubscriptionBeRenewed_subscriptionHasBeenCancelled_returnFalse(
        self, mock_get_parameter_value: Mock
    ):
        mock_get_parameter_value.return_value = True
        subscription = Mock()
        subscription.cancellation_ts = datetime.datetime.now()

        result = AutomaticSubscriptionRenewalService.must_subscription_be_renewed(
            subscription
        )

        self.assertFalse(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        )

    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_next_growing_period"
    )
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_mustSubscriptionBeRenewed_noFutureGrowingPeriod_returnFalse(
        self, mock_get_parameter_value: Mock, mock_get_next_growing_period: Mock
    ):
        mock_get_parameter_value.return_value = True
        subscription = Mock()
        subscription.cancellation_ts = None
        mock_get_next_growing_period.return_value = None

        result = AutomaticSubscriptionRenewalService.must_subscription_be_renewed(
            subscription
        )

        self.assertFalse(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        )
        mock_get_next_growing_period.assert_called_once_with()

    @patch.object(Subscription, "objects")
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_next_growing_period"
    )
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_mustSubscriptionBeRenewed_futureSubscriptionAlreadyExists_returnFalse(
        self,
        mock_get_parameter_value: Mock,
        mock_get_next_growing_period: Mock,
        mock_subscription_objects: Mock,
    ):
        mock_get_parameter_value.return_value = True
        subscription = Mock()
        subscription.cancellation_ts = None
        member = Mock()
        subscription.member = member
        product = Mock()
        subscription.product = product
        next_growing_period = Mock()
        mock_get_next_growing_period.return_value = next_growing_period
        mock_subscription_objects.filter.return_value.exists.return_value = True

        result = AutomaticSubscriptionRenewalService.must_subscription_be_renewed(
            subscription
        )

        self.assertFalse(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        )
        mock_get_next_growing_period.assert_called_once_with()
        mock_subscription_objects.filter.assert_called_once_with(
            member=member, period=next_growing_period, product=product
        )
        mock_subscription_objects.filter.return_value.exists.assert_called_once_with()

    @patch.object(NoticePeriodManager, "get_max_cancellation_date")
    @patch.object(Subscription, "objects")
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_next_growing_period"
    )
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_mustSubscriptionBeRenewed_maxCancellationIsInTheFuture_returnFalse(
        self,
        mock_get_parameter_value: Mock,
        mock_get_next_growing_period: Mock,
        mock_subscription_objects: Mock,
        mock_get_max_cancellation_date: Mock,
    ):
        mock_get_parameter_value.return_value = True
        subscription = Mock()
        subscription.cancellation_ts = None
        member = Mock()
        subscription.member = member
        product = Mock()
        subscription.product = product
        next_growing_period = Mock()
        mock_get_next_growing_period.return_value = next_growing_period
        mock_subscription_objects.filter.return_value.exists.return_value = False
        mock_get_max_cancellation_date.return_value = datetime.date(
            year=2025, month=3, day=2
        )
        mock_timezone(self, datetime.datetime(year=2025, month=3, day=1))

        result = AutomaticSubscriptionRenewalService.must_subscription_be_renewed(
            subscription
        )

        self.assertFalse(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        )
        mock_get_next_growing_period.assert_called_once_with()
        mock_subscription_objects.filter.assert_called_once_with(
            member=member, period=next_growing_period, product=product
        )
        mock_subscription_objects.filter.return_value.exists.assert_called_once_with()
        mock_get_max_cancellation_date.assert_called_once_with(subscription)

    @patch.object(NoticePeriodManager, "get_max_cancellation_date")
    @patch.object(Subscription, "objects")
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_next_growing_period"
    )
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_mustSubscriptionBeRenewed_maxCancellationIsOnSameDay_returnFalse(
        self,
        mock_get_parameter_value: Mock,
        mock_get_next_growing_period: Mock,
        mock_subscription_objects: Mock,
        mock_get_max_cancellation_date: Mock,
    ):
        mock_get_parameter_value.return_value = True
        subscription = Mock()
        subscription.cancellation_ts = None
        member = Mock()
        subscription.member = member
        product = Mock()
        subscription.product = product
        next_growing_period = Mock()
        mock_get_next_growing_period.return_value = next_growing_period
        mock_subscription_objects.filter.return_value.exists.return_value = False
        mock_get_max_cancellation_date.return_value = datetime.date(
            year=2025, month=3, day=2
        )
        mock_timezone(self, datetime.datetime(year=2025, month=3, day=2))

        result = AutomaticSubscriptionRenewalService.must_subscription_be_renewed(
            subscription
        )

        self.assertFalse(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        )
        mock_get_next_growing_period.assert_called_once_with()
        mock_subscription_objects.filter.assert_called_once_with(
            member=member, period=next_growing_period, product=product
        )
        mock_subscription_objects.filter.return_value.exists.assert_called_once_with()
        mock_get_max_cancellation_date.assert_called_once_with(subscription)

    @patch.object(NoticePeriodManager, "get_max_cancellation_date")
    @patch.object(Subscription, "objects")
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_next_growing_period"
    )
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_mustSubscriptionBeRenewed_maxCancellationIsInThePast_returnTrue(
        self,
        mock_get_parameter_value: Mock,
        mock_get_next_growing_period: Mock,
        mock_subscription_objects: Mock,
        mock_get_max_cancellation_date: Mock,
    ):
        mock_get_parameter_value.return_value = True
        subscription = Mock()
        subscription.cancellation_ts = None
        member = Mock()
        subscription.member = member
        product = Mock()
        subscription.product = product
        next_growing_period = Mock()
        mock_get_next_growing_period.return_value = next_growing_period
        mock_subscription_objects.filter.return_value.exists.return_value = False
        mock_get_max_cancellation_date.return_value = datetime.date(
            year=2025, month=3, day=2
        )
        mock_timezone(self, datetime.datetime(year=2025, month=3, day=3))

        result = AutomaticSubscriptionRenewalService.must_subscription_be_renewed(
            subscription
        )

        self.assertTrue(result)
        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL
        )
        mock_get_next_growing_period.assert_called_once_with()
        mock_subscription_objects.filter.assert_called_once_with(
            member=member, period=next_growing_period, product=product
        )
        mock_subscription_objects.filter.return_value.exists.assert_called_once_with()
        mock_get_max_cancellation_date.assert_called_once_with(subscription)
