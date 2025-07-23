from django.urls import reverse
from rest_framework import status

from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    NOW,
    PickupLocationFactory,
    MemberPickupLocationFactory,
    CoopShareTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberDataToConfirmView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_loggedInAsNormalUser_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(reverse("subscriptions:member_data_to_confirm"))

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_loggedInAsAdmin_returnsCorrectData(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        member = MemberFactory.create()
        pickup_location = PickupLocationFactory.create()
        MemberPickupLocationFactory.create(
            member=member, pickup_location=pickup_location
        )

        created_subscription = self.create_unconfirmed_creation(member=member)
        cancelled_subscription = self.create_unconfirmed_cancellation(member=member)
        changed_subscription_before = self.create_unconfirmed_cancellation(
            member=member
        )
        changed_subscription_after = self.create_unconfirmed_creation(
            member=member, product=changed_subscription_before.product
        )
        purchase = CoopShareTransactionFactory.create(
            member=member, quantity=3, admin_confirmed=None
        )

        response = self.client.get(reverse("subscriptions:member_data_to_confirm"))

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertEqual(1, len(response_content))

        member_data = response_content[0]
        self.assertEqual(member_data["member"]["id"], member.id)
        self.assertEqual(member_data["pickup_location"]["id"], pickup_location.id)

        self.assertEqual(1, len(member_data["subscription_cancellations"]))
        self.assertEqual(
            cancelled_subscription.id,
            member_data["subscription_cancellations"][0]["id"],
        )
        self.assertEqual(1, len(member_data["subscription_creations"]))
        self.assertEqual(
            created_subscription.id, member_data["subscription_creations"][0]["id"]
        )

        self.assertEqual(1, len(member_data["subscription_changes"]))
        change_data = member_data["subscription_changes"][0]
        self.assertEqual(
            changed_subscription_before.product.type.id,
            change_data["product_type"]["id"],
        )
        self.assertEqual(
            changed_subscription_before.id,
            change_data["subscription_cancellations"][0]["id"],
        )
        self.assertEqual(
            changed_subscription_after.id,
            change_data["subscription_creations"][0]["id"],
        )

        self.assertEqual(1, len(member_data["share_purchases"]))
        self.assertEqual(
            purchase.id,
            member_data["share_purchases"][0]["id"],
        )

    def test_get_memberHasOnlySharePurchasesToConfirm_memberIsInTheReturnedData(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        member = MemberFactory.create()
        purchase = CoopShareTransactionFactory.create(
            member=member, quantity=3, admin_confirmed=None
        )

        response = self.client.get(reverse("subscriptions:member_data_to_confirm"))

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertEqual(1, len(response_content))

        member_data = response_content[0]

        self.assertEqual(1, len(member_data["share_purchases"]))
        self.assertEqual(
            purchase.id,
            member_data["share_purchases"][0]["id"],
        )

    @staticmethod
    def create_unconfirmed_creation(**kwargs):
        return SubscriptionFactory.create(admin_confirmed=None, **kwargs)

    @staticmethod
    def create_unconfirmed_cancellation(**kwargs):
        return SubscriptionFactory.create(
            admin_confirmed=NOW,
            cancellation_admin_confirmed=None,
            cancellation_ts=NOW,
            **kwargs
        )
