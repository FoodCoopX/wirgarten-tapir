import datetime
from unittest.mock import patch, Mock

from django.urls import reverse
from rest_framework import status
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.coop.models import CoopSharesRevokedLogEntry
from tapir.subscriptions.models import SubscriptionsRevokedLogEntry
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Subscription, CoopShareTransaction, WaitingListEntry
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    MemberFactory,
    CoopShareTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone
from tapir.wirgarten.utils import get_now, format_subscription_list_html


class TestRevokeChangesAPIView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(self, datetime.datetime(year=2024, month=6, day=1))

    def test_post_loggedInAsNormalUser_returns403(self):
        actor = MemberFactory.create(is_superuser=False)
        self.client.force_login(actor)

        subscription = SubscriptionFactory.create()

        url = reverse("subscriptions:revoke_changes")
        url = f"{url}?subscription_creation_ids={subscription.id}&coop_share_purchase_ids="
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_subscriptionIdAlreadyConfirmed_returns404(self):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)

        subscription = SubscriptionFactory.create(
            admin_confirmed=get_now(),
            start_date=self.now.date() + datetime.timedelta(days=1),
        )

        url = reverse("subscriptions:revoke_changes")
        url = f"{url}?subscription_creation_ids={subscription.id}&coop_share_purchase_ids="
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_post_shareTransactionIdAlreadyConfirmed_returns404(self):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)

        transaction = CoopShareTransactionFactory.create(
            admin_confirmed=get_now(),
            valid_at=self.now.date() + datetime.timedelta(days=1),
        )

        url = reverse("subscriptions:revoke_changes")
        url = (
            f"{url}?subscription_creation_ids=&coop_share_purchase_ids={transaction.id}"
        )
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_post_subscriptionIdAlreadyStarted_returns404(self):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)

        subscription = SubscriptionFactory.create(
            admin_confirmed=None,
            start_date=self.now.date() - datetime.timedelta(days=1),
        )

        url = reverse("subscriptions:revoke_changes")
        url = f"{url}?subscription_creation_ids={subscription.id}&coop_share_purchase_ids="
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_post_shareTransactionIdAlreadyValid_returns404(self):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)

        transaction = CoopShareTransactionFactory.create(
            admin_confirmed=get_now(),
            valid_at=self.now.date() - datetime.timedelta(days=1),
        )

        url = reverse("subscriptions:revoke_changes")
        url = (
            f"{url}?subscription_creation_ids=&coop_share_purchase_ids={transaction.id}"
        )
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_putOnWaitingList_deleteSubscriptionAndTransactionAndCreateWaitingListEntry(
        self, mock_fire_action: Mock
    ):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)

        member = MemberFactory.create(phone_number="017726254538")
        subscription_1 = SubscriptionFactory.create(
            admin_confirmed=None,
            member=member,
            quantity=2,
            start_date=self.now.date() + datetime.timedelta(days=1),
        )
        subscription_2 = SubscriptionFactory.create(
            admin_confirmed=None,
            member=member,
            quantity=3,
            start_date=self.now.date() + datetime.timedelta(days=1),
        )
        subscription_other_member = SubscriptionFactory.create(
            admin_confirmed=None,
            start_date=self.now.date() + datetime.timedelta(days=1),
        )
        transaction = CoopShareTransactionFactory.create(
            admin_confirmed=None,
            member=member,
            quantity=7,
            valid_at=self.now.date() + datetime.timedelta(days=1),
        )
        transaction_other_member = CoopShareTransactionFactory.create(
            admin_confirmed=None,
            valid_at=self.now.date() + datetime.timedelta(days=1),
        )

        url = reverse("subscriptions:revoke_changes")
        url = f"{url}?subscription_creation_ids={subscription_1.id}&subscription_creation_ids={subscription_2.id}&coop_share_purchase_ids={transaction.id}&put_on_waiting_list=true"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        subscription_ids = Subscription.objects.values_list("id", flat=True)
        self.assertIn(subscription_other_member.id, subscription_ids)
        self.assertNotIn(subscription_1, subscription_ids)
        self.assertNotIn(subscription_2, subscription_ids)

        transaction_ids = CoopShareTransaction.objects.values_list("id", flat=True)
        self.assertIn(transaction_other_member.id, transaction_ids)
        self.assertNotIn(transaction, transaction_ids)

        waiting_list_entry = WaitingListEntry.objects.prefetch_related(
            "product_wishes"
        ).first()
        self.assertIsNotNone(waiting_list_entry)
        self.assertEqual(member.id, waiting_list_entry.member_id)
        self.assertEqual(7, waiting_list_entry.number_of_coop_shares)

        product_wishes = waiting_list_entry.product_wishes.all()
        self.assertEqual(2, len(product_wishes))
        wish_first_subscription = product_wishes.get(
            product_id=subscription_1.product_id
        )
        self.assertEqual(2, wish_first_subscription.quantity)
        wish_second_subscription = product_wishes.get(
            product_id=subscription_2.product_id
        )
        self.assertEqual(3, wish_second_subscription.quantity)

        mock_fire_action.assert_not_called()

    @patch.object(TransactionalTrigger, "fire_action")
    def test_post_dontPutOnWaitingList_deleteSubscriptionAndTransactionAndSendMailToMembers(
        self, mock_fire_action: Mock
    ):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)

        member = MemberFactory.create(phone_number="017726254538")
        subscription_1 = SubscriptionFactory.create(
            admin_confirmed=None,
            member=member,
            quantity=2,
            product__name="P1",
            start_date=self.now.date() + datetime.timedelta(days=1),
        )
        subscription_2 = SubscriptionFactory.create(
            admin_confirmed=None,
            member=member,
            quantity=3,
            product__name="P2",
            start_date=self.now.date() + datetime.timedelta(days=1),
        )
        subscription_other_member = SubscriptionFactory.create(
            admin_confirmed=None,
            start_date=self.now.date() + datetime.timedelta(days=1),
        )
        transaction = CoopShareTransactionFactory.create(
            admin_confirmed=None,
            member=member,
            quantity=7,
            valid_at=self.now.date() + datetime.timedelta(days=1),
        )
        transaction_other_member = CoopShareTransactionFactory.create(
            admin_confirmed=None,
            valid_at=self.now.date() + datetime.timedelta(days=1),
        )

        url = reverse("subscriptions:revoke_changes")
        url = f"{url}?subscription_creation_ids={subscription_1.id}&subscription_creation_ids={subscription_2.id}&coop_share_purchase_ids={transaction.id}&put_on_waiting_list=false"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        subscription_ids = Subscription.objects.values_list("id", flat=True)
        self.assertIn(subscription_other_member.id, subscription_ids)
        self.assertNotIn(subscription_1, subscription_ids)
        self.assertNotIn(subscription_2, subscription_ids)

        transaction_ids = CoopShareTransaction.objects.values_list("id", flat=True)
        self.assertIn(transaction_other_member.id, transaction_ids)
        self.assertNotIn(transaction, transaction_ids)

        self.assertEqual(0, WaitingListEntry.objects.count())

        mock_fire_action.assert_called_once()
        call = mock_fire_action.call_args_list[0]
        transactional_trigger_data: TransactionalTriggerData = call.args[0]
        self.assertEqual(transactional_trigger_data.key, Events.ORDER_REVOKED)
        self.assertIn(
            transactional_trigger_data.recipient_id_in_base_queryset,
            [member.id],
        )
        self.assertEqual(
            7, transactional_trigger_data.token_data["number_of_coop_shares"]
        )
        self.assertIn(
            "2 × P1",
            transactional_trigger_data.token_data["contract_list"],
        )
        self.assertIn(
            "3 × P2",
            transactional_trigger_data.token_data["contract_list"],
        )

    def test_post_default_createsLogEntries(self):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)

        member = MemberFactory.create()
        subscription_1 = SubscriptionFactory.create(
            admin_confirmed=None,
            member=member,
            quantity=2,
            product__name="P1",
            start_date=self.now.date() + datetime.timedelta(days=1),
        )
        subscription_2 = SubscriptionFactory.create(
            admin_confirmed=None,
            member=member,
            quantity=3,
            product__name="P2",
            start_date=self.now.date() + datetime.timedelta(days=1),
        )

        transaction = CoopShareTransactionFactory.create(
            admin_confirmed=None,
            member=member,
            quantity=7,
            valid_at=self.now.date() + datetime.timedelta(days=1),
        )

        url = reverse("subscriptions:revoke_changes")
        url = f"{url}?subscription_creation_ids={subscription_1.id}&subscription_creation_ids={subscription_2.id}&coop_share_purchase_ids={transaction.id}&put_on_waiting_list=false"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        self.assertEqual(1, SubscriptionsRevokedLogEntry.objects.count())
        subscriptions_log_entry = SubscriptionsRevokedLogEntry.objects.get()
        self.assertEqual(member.id, subscriptions_log_entry.user_id)
        self.assertEqual(
            format_subscription_list_html([subscription_1, subscription_2]),
            subscriptions_log_entry.subscriptions,
        )

        self.assertEqual(1, CoopSharesRevokedLogEntry.objects.count())
        transactions_log_entry = CoopSharesRevokedLogEntry.objects.get()
        self.assertEqual(member.id, transactions_log_entry.user_id)
        self.assertEqual(
            CoopSharesRevokedLogEntry.format_coop_share_transactions([transaction]),
            transactions_log_entry.coop_share_transactions,
        )
