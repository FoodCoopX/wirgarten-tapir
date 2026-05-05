from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestSubscriptionPriceOverrideApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_post_normalMemberTriesToEditPrice_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        subscription = SubscriptionFactory.create(member=member, price_override=5)
        self.client.force_login(member)

        post_data = {"subscription_id": subscription.id, "price_override": 123}
        response = self.client.post(
            reverse("subscriptions:subscription_price_override"), data=post_data
        )

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        subscription.refresh_from_db()
        self.assertEqual(5, subscription.price_override)

    def test_post_sendingNoOverride_priceOverrideSetToNone(self):
        member = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(member=member, price_override=5)
        self.client.force_login(member)

        post_data = {"subscription_id": subscription.id, "price_override": ""}
        response = self.client.post(
            reverse("subscriptions:subscription_price_override"), data=post_data
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])
        self.assertIsNone(response_content["error"])
        subscription.refresh_from_db()
        self.assertIsNone(subscription.price_override)

    def test_post_sendingOverrideNegative_returnsError(self):
        member = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(member=member, price_override=123)
        self.client.force_login(member)

        post_data = {"subscription_id": subscription.id, "price_override": -6}
        response = self.client.post(
            reverse("subscriptions:subscription_price_override"), data=post_data
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertFalse(response_content["order_confirmed"])
        self.assertEqual("Der Preis darf nicht negativ sein", response_content["error"])
        subscription.refresh_from_db()
        self.assertEqual(123, subscription.price_override)

    def test_post_sendingOverridePositive_setsOverride(self):
        member = MemberFactory.create(is_superuser=True)
        subscription = SubscriptionFactory.create(member=member, price_override=5)
        self.client.force_login(member)

        post_data = {"subscription_id": subscription.id, "price_override": 123}
        response = self.client.post(
            reverse("subscriptions:subscription_price_override"), data=post_data
        )

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertTrue(response_content["order_confirmed"])
        self.assertIsNone(response_content["error"])
        subscription.refresh_from_db()
        self.assertEqual(123, subscription.price_override)
