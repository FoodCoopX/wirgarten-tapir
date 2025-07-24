from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status

from tapir.subscriptions.services.order_confirmation_mail_sender import (
    OrderConfirmationMailSender,
)
from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    NOW,
    CoopShareTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestConfirmSubscriptionChangesView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        self.now = mock_timezone(self, NOW)

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        url = reverse("subscriptions:confirm_subscription_changes")
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_someCancelledSubscriptionIdsDontExist_returns404AndDontConfirmAnything(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        subscription_1 = SubscriptionFactory.create(cancellation_ts=self.now)
        subscription_2 = SubscriptionFactory.create(
            cancellation_ts=self.now, cancellation_admin_confirmed=self.now
        )

        url = reverse("subscriptions:confirm_subscription_changes")
        url = f"{url}?confirm_cancellation_ids={subscription_1.id}&confirm_cancellation_ids={subscription_2.id}"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)
        subscription_1.refresh_from_db()
        self.assertIsNone(subscription_1.cancellation_admin_confirmed)

    def test_post_someCreatedSubscriptionIdsDontExist_returns404AndDontConfirmAnything(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        subscription_1 = SubscriptionFactory.create(cancellation_ts=self.now)
        subscription_2 = SubscriptionFactory.create(admin_confirmed=self.now)

        url = reverse("subscriptions:confirm_subscription_changes")
        url = f"{url}?confirm_cancellation_ids={subscription_1.id}&confirm_creation_ids={subscription_2.id}"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            Subscription.objects.filter(
                cancellation_admin_confirmed__isnull=False
            ).exists()
        )

    def test_post_someCoopPurchaseIdsDontExist_returns404AndDontConfirmAnything(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        subscription = SubscriptionFactory.create(admin_confirmed=None)
        purchase = CoopShareTransactionFactory.create(admin_confirmed=self.now)

        url = reverse("subscriptions:confirm_subscription_changes")
        url = f"{url}?confirm_creation_ids={subscription.id}&confirm_purchase_ids={purchase.id}"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            Subscription.objects.filter(
                cancellation_admin_confirmed__isnull=False
            ).exists()
        )

    @patch.object(OrderConfirmationMailSender, "send_confirmation_mail_if_necessary")
    def test_post_default_confirmSelectionAndSendConfirmationMails(
        self, mock_send_confirmation_mail_if_necessary: Mock
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        subscription_1 = SubscriptionFactory.create(
            cancellation_ts=self.now, admin_confirmed=self.now
        )
        subscription_2 = SubscriptionFactory.create()
        purchase = CoopShareTransactionFactory.create(admin_confirmed=None)

        url = reverse("subscriptions:confirm_subscription_changes")
        url = f"{url}?confirm_cancellation_ids={subscription_1.id}&confirm_creation_ids={subscription_2.id}&confirm_purchase_ids={purchase.id}"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        subscription_1.refresh_from_db()
        self.assertEqual(self.now, subscription_1.cancellation_admin_confirmed)
        subscription_2.refresh_from_db()
        self.assertIsNotNone(self.now, subscription_2.admin_confirmed)
        purchase.refresh_from_db()
        self.assertIsNotNone(self.now, purchase.admin_confirmed)

        mock_send_confirmation_mail_if_necessary.assert_called_once_with(
            confirm_creation_ids=[subscription_2.id], confirm_purchase_ids=[purchase.id]
        )
