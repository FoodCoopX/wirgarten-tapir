import datetime

from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductTypeFactory,
    SubscriptionFactory,
    ProductFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetMemberSubscriptionDataApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.product_types = ProductTypeFactory.create_batch(size=3)
        cls.product = ProductFactory.create(type=cls.product_types[0])
        ProductPriceFactory.create(
            product=cls.product, valid_from=datetime.date(year=2023, month=1, day=1)
        )

    def setUp(self):
        super().setUp()
        self.target_member = MemberFactory.create(is_superuser=False)

        mock_timezone(test=self, now=datetime.datetime(year=2023, month=11, day=15))
        self.subscription_current = SubscriptionFactory.create(
            member=self.target_member,
            period__start_date=datetime.date(year=2023, month=1, day=1),
            product=self.product,
        )
        self.subscription_future = SubscriptionFactory.create(
            member=self.target_member,
            period__start_date=datetime.date(year=2024, month=1, day=1),
            product=self.product,
        )
        self.subscription_past = SubscriptionFactory.create(
            member=self.target_member,
            period__start_date=datetime.date(year=2022, month=1, day=1),
            product=self.product,
        )

    def test_get_memberGetsOwnData_returnsCorrectData(self):
        self.client.force_login(self.target_member)

        self.assert_returns_correct_data()

    def test_get_adminGetsDataOfAnotherMember_returnsCorrectData(self):
        admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(admin)

        self.assert_returns_correct_data()

    def test_get_memberGetsDataOfAnotherMember_returns403(self):
        logged_in_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_member)

        url = reverse("subscriptions:member_subscription_data")
        url = f"{url}?member_id={self.target_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def assert_returns_correct_data(self):
        url = reverse("subscriptions:member_subscription_data")
        url = f"{url}?member_id={self.target_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertEqual(3, len(response_content["product_types"]))
        product_type_ids = {
            product_type["id"] for product_type in response_content["product_types"]
        }
        for product_type in self.product_types:
            self.assertIn(product_type.id, product_type_ids)

        self.assertEqual(
            f"/bestell_wizard/bestell_wizard_product_type/{self.target_member.id}/product_type_id",
            response_content["bestell_wizard_url_template"],
        )

        self.assertEqual(2, len(response_content["subscriptions"]))
        subscription_ids = {
            subscription["id"] for subscription in response_content["subscriptions"]
        }
        self.assertIn(self.subscription_current.id, subscription_ids)
        self.assertIn(self.subscription_future.id, subscription_ids)
        self.assertNotIn(self.subscription_past.id, subscription_ids)
