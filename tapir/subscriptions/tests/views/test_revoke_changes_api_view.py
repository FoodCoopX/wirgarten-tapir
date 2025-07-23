from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.models import Subscription, CoopShareTransaction, WaitingListEntry
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    SubscriptionFactory,
    MemberFactory,
    CoopShareTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_now


class TestRevokeChangesAPIView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

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

        subscription = SubscriptionFactory.create(admin_confirmed=get_now())

        url = reverse("subscriptions:revoke_changes")
        url = f"{url}?subscription_creation_ids={subscription.id}&coop_share_purchase_ids="
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_post_shareTransactionIdAlreadyConfirmed_returns404(self):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)

        transaction = CoopShareTransactionFactory.create(admin_confirmed=get_now())

        url = reverse("subscriptions:revoke_changes")
        url = (
            f"{url}?subscription_creation_ids=&coop_share_purchase_ids={transaction.id}"
        )
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_post_default_deleteSubscriptionAndTransactionAndCreateWaitingListEntry(
        self,
    ):
        actor = MemberFactory.create(is_superuser=True)
        self.client.force_login(actor)

        member = MemberFactory.create(phone_number="017726254538")
        subscription_1 = SubscriptionFactory.create(
            admin_confirmed=None, member=member, quantity=2
        )
        subscription_2 = SubscriptionFactory.create(
            admin_confirmed=None, member=member, quantity=3
        )
        subscription_other_member = SubscriptionFactory.create(admin_confirmed=None)
        transaction = CoopShareTransactionFactory.create(
            admin_confirmed=None, member=member, quantity=7
        )
        transaction_other_member = CoopShareTransactionFactory.create(
            admin_confirmed=None
        )

        url = reverse("subscriptions:revoke_changes")
        url = f"{url}?subscription_creation_ids={subscription_1.id}&subscription_creation_ids={subscription_2.id}&coop_share_purchase_ids={transaction.id}"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        subscription_ids = Subscription.objects.values_list("id", flat=True)
        self.assertIn(subscription_other_member.id, subscription_ids)
        self.assertNotIn(subscription_1, subscription_ids)
        self.assertNotIn(subscription_2, subscription_ids)

        transaction_ids = CoopShareTransaction.objects.values_list("id", flat=True)
        self.assertIn(transaction_other_member.id, transaction_ids)
        self.assertNotIn(transaction, transaction_ids)

        waiting_list_entry = WaitingListEntry.objects.first()
        self.assertIsNotNone(waiting_list_entry)
        self.assertEqual(member.id, waiting_list_entry.member.id)
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
