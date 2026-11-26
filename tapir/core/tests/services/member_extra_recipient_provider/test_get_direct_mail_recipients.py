from unittest.mock import MagicMock, patch

from tapir.core.services.member_extra_recipient_provider import (
    MemberExtraRecipientProvider,
)
from tapir.mail.addressed_recipient import AddressedRecipient
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.factories import MemberExtraEmailFactory, MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    TapirCache,
    "get_confirmed_member_extra_emails_for_member",
    autospec=True,
    return_value=[],
)
class TestGetDirectMailRecipients(TapirUnitTest):
    def test_getDirectMailRecipients_featureDisabled_returnsEmptyList(
        self, mock_get_confirmed_member_extra_emails_for_member: MagicMock
    ):
        member = MemberFactory.build()
        mock_get_confirmed_member_extra_emails_for_member.return_value = [
            MemberExtraEmailFactory.build(member=member)
        ]
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=False
        )

        result = MemberExtraRecipientProvider.get_direct_mail_recipients(
            member=member, cache=cache
        )

        self.assertEqual([], result)

    def test_getDirectMailRecipients_featureEnabled_returnsOneAddressedRecipientPerConfirmedExtra(
        self, mock_get_confirmed_member_extra_emails_for_member: MagicMock
    ):
        member = MemberFactory.build()
        extra_1 = MemberExtraEmailFactory.build(
            member=member, email="extra1@example.com", first_name="F1", last_name="L1"
        )
        extra_2 = MemberExtraEmailFactory.build(
            member=member, email="extra2@example.com", first_name="F2", last_name="L2"
        )
        mock_get_confirmed_member_extra_emails_for_member.return_value = [
            extra_1,
            extra_2,
        ]
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True
        )

        result = MemberExtraRecipientProvider.get_direct_mail_recipients(
            member=member, cache=cache
        )

        self.assertEqual(
            [
                AddressedRecipient(
                    recipient=member,
                    email="extra1@example.com",
                    token_overrides={"first_name": "F1", "last_name": "L1"},
                ),
                AddressedRecipient(
                    recipient=member,
                    email="extra2@example.com",
                    token_overrides={"first_name": "F2", "last_name": "L2"},
                ),
            ],
            result,
        )
        mock_get_confirmed_member_extra_emails_for_member.assert_called_once_with(
            member_id=member.id, cache=cache
        )

    def test_getDirectMailRecipients_extraDoesNotReceiveDirectMails_extraIsSkipped(
        self, mock_get_confirmed_member_extra_emails_for_member: MagicMock
    ):
        member = MemberFactory.build()
        mock_get_confirmed_member_extra_emails_for_member.return_value = [
            MemberExtraEmailFactory.build(
                member=member,
                email="direct@example.com",
                first_name="F1",
                last_name="L1",
                receives_direct_mails=True,
            ),
            MemberExtraEmailFactory.build(
                member=member,
                email="subscriptions_only@example.com",
                receives_direct_mails=False,
            ),
        ]
        cache = {}
        mock_parameter_value(
            cache=cache, key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True
        )

        result = MemberExtraRecipientProvider.get_direct_mail_recipients(
            member=member, cache=cache
        )

        self.assertEqual(
            [
                AddressedRecipient(
                    recipient=member,
                    email="direct@example.com",
                    token_overrides={"first_name": "F1", "last_name": "L1"},
                ),
            ],
            result,
        )
