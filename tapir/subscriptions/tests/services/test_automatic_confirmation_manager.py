import datetime
from unittest.mock import patch, Mock

from tapir_mail.service.shortcuts import make_timezone_aware

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.automatic_confirmation_manager import (
    AutomaticConfirmationManager,
)
from tapir.subscriptions.services.order_confirmation_mail_sender import (
    OrderConfirmationMailSender,
)
from tapir.wirgarten.models import CoopShareTransaction
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    CoopShareTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestAutomaticConfirmationManager(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        # wednesday
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(value=2)
        # saturday
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        ).update(value=5)

    def setUp(self) -> None:
        self.now = mock_timezone(self, datetime.datetime(year=2025, month=1, day=17))
        self.yesterday = self.now.date() - datetime.timedelta(days=1)

    @patch.object(OrderConfirmationMailSender, "send_confirmation_mail_if_necessary")
    def test_confirm_subscriptionsAlreadyConfirmed_confirmationTimestampNotUpdated(
        self, mock_send_confirmation_mail_if_necessary: Mock
    ):
        confirmation_time = make_timezone_aware(
            datetime.datetime(year=2024, month=12, day=25)
        )
        subscription_1 = SubscriptionFactory.create(
            admin_confirmed=confirmation_time, start_date=self.yesterday
        )
        subscription_2 = SubscriptionFactory.create(
            auto_confirmed=confirmation_time, start_date=self.yesterday
        )
        subscription_3 = SubscriptionFactory.create(
            admin_confirmed=confirmation_time,
            auto_confirmed=confirmation_time,
            start_date=self.yesterday,
        )

        AutomaticConfirmationManager.confirm_subscriptions_and_coop_share_purchases_if_necessary()

        self.refresh_object_and_check_timestamps(
            obj=subscription_1, admin_confirmed=confirmation_time, auto_confirmed=None
        )
        self.refresh_object_and_check_timestamps(
            obj=subscription_2, admin_confirmed=None, auto_confirmed=confirmation_time
        )
        self.refresh_object_and_check_timestamps(
            obj=subscription_3,
            admin_confirmed=confirmation_time,
            auto_confirmed=confirmation_time,
        )

        mock_send_confirmation_mail_if_necessary.assert_called_once_with(
            confirm_creation_ids=[], confirm_purchase_ids=[]
        )

    @patch.object(OrderConfirmationMailSender, "send_confirmation_mail_if_necessary")
    def test_confirm_transactionsAlreadyConfirmed_confirmationTimestampNotUpdated(
        self, mock_send_confirmation_mail_if_necessary: Mock
    ):
        confirmation_time = make_timezone_aware(
            datetime.datetime(year=2024, month=12, day=25)
        )
        transaction_1 = CoopShareTransactionFactory.create(
            admin_confirmed=confirmation_time,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=self.yesterday,
        )
        transaction_2 = CoopShareTransactionFactory.create(
            auto_confirmed=confirmation_time,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=self.yesterday,
        )
        transaction_3 = CoopShareTransactionFactory.create(
            admin_confirmed=confirmation_time,
            auto_confirmed=confirmation_time,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            valid_at=self.yesterday,
        )

        AutomaticConfirmationManager.confirm_subscriptions_and_coop_share_purchases_if_necessary()

        self.refresh_object_and_check_timestamps(
            obj=transaction_1, admin_confirmed=confirmation_time, auto_confirmed=None
        )
        self.refresh_object_and_check_timestamps(
            obj=transaction_2, admin_confirmed=None, auto_confirmed=confirmation_time
        )
        self.refresh_object_and_check_timestamps(
            obj=transaction_3,
            admin_confirmed=confirmation_time,
            auto_confirmed=confirmation_time,
        )

        mock_send_confirmation_mail_if_necessary.assert_called_once_with(
            confirm_creation_ids=[], confirm_purchase_ids=[]
        )

    @patch.object(OrderConfirmationMailSender, "send_confirmation_mail_if_necessary")
    def test_confirm_subscriptionStartsAfterThreshold_confirmationTimestampNotUpdated(
        self, mock_send_confirmation_mail_if_necessary: Mock
    ):
        subscription = SubscriptionFactory.create(
            admin_confirmed=None,
            auto_confirmed=None,
            start_date=datetime.date(year=2025, month=1, day=19),
        )

        AutomaticConfirmationManager.confirm_subscriptions_and_coop_share_purchases_if_necessary()

        self.refresh_object_and_check_timestamps(
            obj=subscription, admin_confirmed=None, auto_confirmed=None
        )

        mock_send_confirmation_mail_if_necessary.assert_called_once_with(
            confirm_creation_ids=[], confirm_purchase_ids=[]
        )

    @patch.object(OrderConfirmationMailSender, "send_confirmation_mail_if_necessary")
    def test_confirm_transactionStartsAfterThreshold_confirmationTimestampNotUpdated(
        self, mock_send_confirmation_mail_if_necessary: Mock
    ):
        transaction = CoopShareTransactionFactory.create(
            admin_confirmed=None,
            auto_confirmed=None,
            valid_at=datetime.date(year=2025, month=1, day=17),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        )

        AutomaticConfirmationManager.confirm_subscriptions_and_coop_share_purchases_if_necessary()

        self.refresh_object_and_check_timestamps(
            obj=transaction, admin_confirmed=None, auto_confirmed=None
        )

        mock_send_confirmation_mail_if_necessary.assert_called_once_with(
            confirm_creation_ids=[], confirm_purchase_ids=[]
        )

    @patch.object(OrderConfirmationMailSender, "send_confirmation_mail_if_necessary")
    def test_confirm_subscriptionStartsBeforeThreshold_confirmationTimestampUpdated(
        self, mock_send_confirmation_mail_if_necessary: Mock
    ):
        subscription = SubscriptionFactory.create(
            admin_confirmed=None,
            auto_confirmed=None,
            start_date=datetime.date(year=2025, month=1, day=19),
        )
        # thursday
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        ).update(value=3)

        AutomaticConfirmationManager.confirm_subscriptions_and_coop_share_purchases_if_necessary()

        self.refresh_object_and_check_timestamps(
            obj=subscription, admin_confirmed=None, auto_confirmed=self.now
        )

        mock_send_confirmation_mail_if_necessary.assert_called_once_with(
            confirm_creation_ids=[subscription.id], confirm_purchase_ids=[]
        )

    @patch.object(OrderConfirmationMailSender, "send_confirmation_mail_if_necessary")
    def test_confirm_transactionStartsBeforeThreshold_confirmationTimestampUpdated(
        self, mock_send_confirmation_mail_if_necessary: Mock
    ):
        transaction = CoopShareTransactionFactory.create(
            admin_confirmed=None,
            auto_confirmed=None,
            valid_at=datetime.date(year=2025, month=1, day=19),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        )
        # thursday
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        ).update(value=3)

        AutomaticConfirmationManager.confirm_subscriptions_and_coop_share_purchases_if_necessary()

        self.refresh_object_and_check_timestamps(
            obj=transaction, admin_confirmed=None, auto_confirmed=self.now
        )

        mock_send_confirmation_mail_if_necessary.assert_called_once_with(
            confirm_creation_ids=[], confirm_purchase_ids=[transaction.id]
        )

    @patch.object(OrderConfirmationMailSender, "send_confirmation_mail_if_necessary")
    def test_confirm_subscriptionStartsAfterThresholdButInThePast_confirmationTimestampUpdated(
        self, mock_send_confirmation_mail_if_necessary: Mock
    ):
        subscription = SubscriptionFactory.create(
            admin_confirmed=None,
            auto_confirmed=None,
            start_date=datetime.date(year=2025, month=1, day=16),
        )

        AutomaticConfirmationManager.confirm_subscriptions_and_coop_share_purchases_if_necessary()

        self.refresh_object_and_check_timestamps(
            obj=subscription, admin_confirmed=None, auto_confirmed=self.now
        )

        mock_send_confirmation_mail_if_necessary.assert_called_once_with(
            confirm_creation_ids=[subscription.id], confirm_purchase_ids=[]
        )

    @patch.object(OrderConfirmationMailSender, "send_confirmation_mail_if_necessary")
    def test_confirm_transactionStartsAfterThresholdButInThePast_confirmationTimestampUpdated(
        self, mock_send_confirmation_mail_if_necessary: Mock
    ):
        transaction = CoopShareTransactionFactory.create(
            admin_confirmed=None,
            auto_confirmed=None,
            valid_at=datetime.date(year=2025, month=1, day=16),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
        )

        AutomaticConfirmationManager.confirm_subscriptions_and_coop_share_purchases_if_necessary()

        self.refresh_object_and_check_timestamps(
            obj=transaction, admin_confirmed=None, auto_confirmed=self.now
        )

        mock_send_confirmation_mail_if_necessary.assert_called_once_with(
            confirm_creation_ids=[], confirm_purchase_ids=[transaction.id]
        )

    def refresh_object_and_check_timestamps(self, obj, admin_confirmed, auto_confirmed):
        obj.refresh_from_db()
        self.assertEqual(admin_confirmed, obj.admin_confirmed)
        self.assertEqual(auto_confirmed, obj.auto_confirmed)
