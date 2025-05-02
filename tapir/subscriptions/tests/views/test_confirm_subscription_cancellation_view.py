from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.models import Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory, NOW
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestConfirmSubscriptionCancellationView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        cls.subscription_1 = SubscriptionFactory.create(cancellation_ts=NOW)
        cls.subscription_2 = SubscriptionFactory.create(cancellation_ts=NOW)
        cls.subscription_3 = SubscriptionFactory.create(cancellation_ts=NOW)

    def test_post_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        url = reverse("subscriptions:confirm_subscription_cancellation")
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_post_someSubscriptionIdsDontExist_returns404AndDontConfirmAnything(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        url = reverse("subscriptions:confirm_subscription_cancellation")
        url = f"{url}?subscription_ids={self.subscription_1.id}&subscription_ids={self.subscription_2.id}&subscription_ids=invalid"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)
        self.assertFalse(
            Subscription.objects.filter(
                cancellation_admin_confirmed__isnull=False
            ).exists()
        )

    def test_post_default_confirmSelection(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        url = reverse("subscriptions:confirm_subscription_cancellation")
        url = f"{url}?subscription_ids={self.subscription_1.id}&subscription_ids={self.subscription_3.id}"
        response = self.client.post(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        confirmed_cancellations = Subscription.objects.filter(
            cancellation_admin_confirmed__isnull=False
        )
        self.assertIn(self.subscription_1, confirmed_cancellations)
        self.assertIn(self.subscription_3, confirmed_cancellations)
        self.assertNotIn(self.subscription_2, confirmed_cancellations)
