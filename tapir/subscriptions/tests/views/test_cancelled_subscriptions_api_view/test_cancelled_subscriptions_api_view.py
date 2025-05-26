import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductTypeFactory,
    SubscriptionFactory,
    NOW,
    MemberPickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCancelledSubscriptionsAPIView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()
        cls.product_type_1 = ProductTypeFactory.create()
        cls.product_type_2 = ProductTypeFactory.create()
        cls.subscription_1 = SubscriptionFactory.create(
            product__type=cls.product_type_1,
            cancellation_ts=NOW - datetime.timedelta(days=1),
        )
        cls.subscription_2 = SubscriptionFactory.create(
            product__type=cls.product_type_1, cancellation_ts=NOW
        )
        cls.subscription_3 = SubscriptionFactory.create(
            product__type=cls.product_type_2, cancellation_ts=NOW
        )
        for member in Member.objects.all():
            MemberPickupLocationFactory.create(member=member)

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        url = reverse("subscriptions:cancelled_subscriptions")
        url = f"{url}?limit=10&offset=0&product_type_id={self.product_type_1.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_loggedInAsAdmin_returnsCorrectData(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        url = reverse("subscriptions:cancelled_subscriptions")
        url = f"{url}?limit=10&offset=0&product_type_id={self.product_type_1.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        # cls.subscription_3 should not be included because it's not from the right product_type
        self.assertEqual(2, response_content["count"])

        # cls.subscription_1 should be first because it was cancelled first
        first_results = response_content["results"][0]
        self.assertEqual(self.subscription_1.id, first_results["subscription"]["id"])
        self.assertEqual(self.subscription_1.member_id, first_results["member"]["id"])
        second_results = response_content["results"][1]
        self.assertEqual(self.subscription_2.id, second_results["subscription"]["id"])
        self.assertEqual(self.subscription_2.member_id, second_results["member"]["id"])
