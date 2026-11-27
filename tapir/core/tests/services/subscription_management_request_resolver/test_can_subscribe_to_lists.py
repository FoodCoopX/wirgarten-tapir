from django.utils import timezone

from tapir.core.services.subscription_management_request_resolver import (
    SubscriptionManagementRequestResolver,
)
from tapir.mail.models import ExternalRecipient
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCanSubscribeToLists(TapirIntegrationTest):
    ADDRESS = "address@example.com"

    def test_canSubscribeToLists_addressIsAConfirmedExtra_returnsTrue(self):
        MemberExtraEmailFactory.create(email=self.ADDRESS, confirmed_on=timezone.now())

        self.assertTrue(
            SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                address=self.ADDRESS
            )
        )

    def test_canSubscribeToLists_addressIsAnExternalRecipient_returnsTrue(self):
        ExternalRecipient.objects.create(email=self.ADDRESS, first_name="E")

        self.assertTrue(
            SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                address=self.ADDRESS
            )
        )

    def test_canSubscribeToLists_addressIsAnUnconfirmedExtra_returnsFalse(self):
        MemberExtraEmailFactory.create(email=self.ADDRESS, confirmed_on=None)

        self.assertFalse(
            SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                address=self.ADDRESS
            )
        )

    def test_canSubscribeToLists_unknownAddress_returnsFalse(self):
        self.assertFalse(
            SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                address=self.ADDRESS
            )
        )
