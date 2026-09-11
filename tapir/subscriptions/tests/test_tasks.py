from unittest.mock import patch, Mock

from tapir.wirgarten.tests.test_utils import TapirUnitTest

from tapir.subscriptions import tasks
from tapir.subscriptions.services.automatic_subscription_renewal_service import (
    AutomaticSubscriptionRenewalService,
)


class TestTasks(TapirUnitTest):
    @patch.object(
        AutomaticSubscriptionRenewalService, "renew_subscriptions_if_necessary"
    )
    def test_doAutomatedExports_default_callsService(
        self, mock_renew_subscriptions_if_necessary: Mock
    ):
        tasks.automatic_subscription_renewal()
        mock_renew_subscriptions_if_necessary.assert_called_once_with()
