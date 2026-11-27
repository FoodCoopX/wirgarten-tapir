from django.utils import timezone

from tapir.core.services.subscription_management_request_resolver import (
    SubscriptionManagementRequestResolver,
)
from tapir.mail.models import ExternalRecipient
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestCanSubscribeToLists(TapirIntegrationTest):
    ADDRESS = "address@example.com"

    def test_canSubscribeToLists_addressIsAConfirmedExtra_returnsTrue(self):
        MemberExtraEmailFactory.create(email=self.ADDRESS, confirmed_on=timezone.now())

        self.assertTrue(
            SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                address=self.ADDRESS,
                cache=self._build_cache(extra_mail_addresses_enabled=True),
            )
        )

    def test_canSubscribeToLists_addressIsAnExternalRecipient_returnsTrue(self):
        ExternalRecipient.objects.create(email=self.ADDRESS, first_name="E")

        self.assertTrue(
            SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                address=self.ADDRESS,
                cache=self._build_cache(extra_mail_addresses_enabled=True),
            )
        )

    def test_canSubscribeToLists_addressIsAnUnconfirmedExtra_returnsFalse(self):
        MemberExtraEmailFactory.create(email=self.ADDRESS, confirmed_on=None)

        self.assertFalse(
            SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                address=self.ADDRESS,
                cache=self._build_cache(extra_mail_addresses_enabled=True),
            )
        )

    def test_canSubscribeToLists_unknownAddress_returnsFalse(self):
        self.assertFalse(
            SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                address=self.ADDRESS,
                cache=self._build_cache(extra_mail_addresses_enabled=True),
            )
        )

    def test_canSubscribeToLists_confirmedExtraButExtraMailAddressesDisabled_returnsFalse(
        self,
    ):
        MemberExtraEmailFactory.create(email=self.ADDRESS, confirmed_on=timezone.now())

        self.assertFalse(
            SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                address=self.ADDRESS,
                cache=self._build_cache(extra_mail_addresses_enabled=False),
            )
        )

    @staticmethod
    def _build_cache(extra_mail_addresses_enabled: bool) -> dict:
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES,
            value=extra_mail_addresses_enabled,
        )
        return cache
