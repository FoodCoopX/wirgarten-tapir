from unittest.mock import patch, Mock, ANY

from django.test import SimpleTestCase

from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)
from tapir.wirgarten.parameter_keys import ParameterKeys


class TestRenewSubscriptionIfNecessary(SimpleTestCase):
    @patch.object(AutomaticSubscriptionRenewalService, "build_renewed_subscription")
    @patch.object(AutomaticSubscriptionRenewalService, "must_subscription_be_renewed")
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_renewSubscriptionIfNecessary_automaticRenewalIsDisabled_doNothing(
        self,
        mock_get_parameter_value: Mock,
        mock_must_subscription_be_renewed: Mock,
        mock_build_renewed_subscription: Mock,
    ):
        mock_get_parameter_value.return_value = False

        AutomaticSubscriptionRenewalService.renew_subscriptions_if_necessary()

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=ANY
        )
        mock_must_subscription_be_renewed.assert_not_called()

        mock_build_renewed_subscription.assert_not_called()

    @patch.object(AutomaticSubscriptionRenewalService, "build_renewed_subscription")
    @patch.object(AutomaticSubscriptionRenewalService, "must_subscription_be_renewed")
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_active_subscriptions"
    )
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_renewSubscriptionIfNecessary_subscriptionMustNotBeRenewed_dontRenew(
        self,
        mock_get_parameter_value: Mock,
        mock_get_active_subscriptions: Mock,
        mock_must_subscription_be_renewed: Mock,
        mock_build_renewed_subscription: Mock,
    ):
        mock_get_parameter_value.return_value = True
        subscription = Mock
        mock_get_active_subscriptions.return_value = [subscription]
        mock_must_subscription_be_renewed.return_value = False

        AutomaticSubscriptionRenewalService.renew_subscriptions_if_necessary()

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=ANY
        )
        mock_must_subscription_be_renewed.assert_called_once_with(
            subscription, cache=ANY
        )
        mock_build_renewed_subscription.assert_not_called()

    @patch.object(AutomaticSubscriptionRenewalService, "build_renewed_subscription")
    @patch.object(AutomaticSubscriptionRenewalService, "must_subscription_be_renewed")
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_active_subscriptions"
    )
    @patch(
        "tapir.subscriptions.services.automatic_subscription_renewal_service.get_parameter_value"
    )
    def test_renewSubscriptionIfNecessary_subscriptionMustBeRenewed_callRenew(
        self,
        mock_get_parameter_value: Mock,
        mock_get_active_subscriptions: Mock,
        mock_must_subscription_be_renewed: Mock,
        mock_build_renewed_subscription: Mock,
    ):
        mock_get_parameter_value.return_value = True
        subscription = Mock
        mock_get_active_subscriptions.return_value = [subscription]
        mock_must_subscription_be_renewed.return_value = True

        AutomaticSubscriptionRenewalService.renew_subscriptions_if_necessary()

        mock_get_parameter_value.assert_called_once_with(
            ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=ANY
        )
        mock_must_subscription_be_renewed.assert_called_once_with(
            subscription, cache=ANY
        )
        mock_build_renewed_subscription.assert_called_once_with(subscription, cache=ANY)
