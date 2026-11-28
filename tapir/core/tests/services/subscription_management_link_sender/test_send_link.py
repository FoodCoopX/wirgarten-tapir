from unittest.mock import ANY, MagicMock, patch

from django.utils import timezone

from tapir.core.services.subscription_management_link_provider import (
    SubscriptionManagementLinkProvider,
)
from tapir.core.services.subscription_management_link_sender import (
    SubscriptionManagementLinkSender,
)
from tapir.mail.models import ExternalRecipient
from tapir.mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


@patch.object(
    SubscriptionManagementLinkProvider,
    "build_link_for_address",
    autospec=True,
    return_value="https://management.link",
)
@patch.object(TransactionalTrigger, "fire_action", autospec=True)
class TestSendLink(TapirIntegrationTest):
    def test_sendLink_addressIsAMainAddress_sendsNothing(
        self, mock_fire_action: MagicMock, mock_build_link_for_address: MagicMock
    ):
        MemberFactory.create(email="main@example.com")
        ExternalRecipient.objects.create(email="main@example.com", first_name="Main")

        SubscriptionManagementLinkSender.send_link(
            address="main@example.com",
            cache=self._build_cache(extra_mail_addresses_enabled=True),
        )

        mock_fire_action.assert_not_called()
        mock_build_link_for_address.assert_not_called()

    def test_sendLink_addressIsAConfirmedExtra_sendsTheLinkWithTheExtraFirstName(
        self, mock_fire_action: MagicMock, mock_build_link_for_address: MagicMock
    ):
        MemberExtraEmailFactory.create(
            email="extra@example.com", first_name="Extra", confirmed_on=timezone.now()
        )
        ExternalRecipient.objects.create(
            email="extra@example.com", first_name="External"
        )

        SubscriptionManagementLinkSender.send_link(
            address="extra@example.com",
            cache=self._build_cache(extra_mail_addresses_enabled=True),
        )

        self._assert_link_sent(
            mock_fire_action=mock_fire_action,
            mock_build_link_for_address=mock_build_link_for_address,
            address="extra@example.com",
            first_name="Extra",
        )

    def test_sendLink_addressIsAnExternalRecipient_sendsTheLinkWithTheExternalFirstName(
        self, mock_fire_action: MagicMock, mock_build_link_for_address: MagicMock
    ):
        MemberExtraEmailFactory.create(email="external@example.com", confirmed_on=None)
        ExternalRecipient.objects.create(
            email="external@example.com", first_name="External"
        )

        SubscriptionManagementLinkSender.send_link(
            address="external@example.com",
            cache=self._build_cache(extra_mail_addresses_enabled=True),
        )

        self._assert_link_sent(
            mock_fire_action=mock_fire_action,
            mock_build_link_for_address=mock_build_link_for_address,
            address="external@example.com",
            first_name="External",
        )

    def test_sendLink_addressIsUnknown_sendsNothing(
        self, mock_fire_action: MagicMock, mock_build_link_for_address: MagicMock
    ):
        MemberExtraEmailFactory.create(email="unknown@example.com", confirmed_on=None)

        SubscriptionManagementLinkSender.send_link(
            address="unknown@example.com",
            cache=self._build_cache(extra_mail_addresses_enabled=True),
        )

        mock_fire_action.assert_not_called()
        mock_build_link_for_address.assert_not_called()

    def test_sendLink_confirmedExtraButExtraMailAddressesDisabled_sendsNothing(
        self, mock_fire_action: MagicMock, mock_build_link_for_address: MagicMock
    ):
        MemberExtraEmailFactory.create(
            email="extra@example.com", confirmed_on=timezone.now()
        )

        SubscriptionManagementLinkSender.send_link(
            address="extra@example.com",
            cache=self._build_cache(extra_mail_addresses_enabled=False),
        )

        mock_fire_action.assert_not_called()
        mock_build_link_for_address.assert_not_called()

    @staticmethod
    def _build_cache(extra_mail_addresses_enabled: bool) -> dict:
        cache = {}
        mock_parameter_value(
            cache=cache,
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES,
            value=extra_mail_addresses_enabled,
        )
        return cache

    @staticmethod
    def _assert_link_sent(
        mock_fire_action: MagicMock,
        mock_build_link_for_address: MagicMock,
        address: str,
        first_name: str,
    ):
        mock_fire_action.assert_called_once_with(
            TransactionalTriggerData(
                key=Events.SUBSCRIPTION_MANAGEMENT_LINK,
                token_data={
                    "management_link": "https://management.link",
                    "validity": "72 Stunden",
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=address, first_name=first_name, last_name=""
                ),
            )
        )
        mock_build_link_for_address.assert_called_once_with(address=address, cache=ANY)
