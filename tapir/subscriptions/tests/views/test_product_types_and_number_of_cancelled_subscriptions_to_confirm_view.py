import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductTypeFactory,
    SubscriptionFactory,
    NOW,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestProductTypesAndNumberOfCancelledSubscriptionsToConfirmView(
    TapirIntegrationTest
):
    maxDiff = 1500

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

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        url = reverse(
            "subscriptions:product_types_and_number_of_cancelled_subscriptions"
        )
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_loggedInAsAdmin_returnsCorrectData(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        url = reverse(
            "subscriptions:product_types_and_number_of_cancelled_subscriptions"
        )
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()
        self.assertEqual([2, 1], response_content["number_of_subscriptions"])
        self.assertEqual(2, len(response_content["product_types"]))
        self.assertEqual(
            self.product_type_1.id, response_content["product_types"][0]["id"]
        )
        self.assertEqual(
            self.product_type_2.id, response_content["product_types"][1]["id"]
        )
