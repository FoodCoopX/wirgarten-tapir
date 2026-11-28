from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from tapir.core.services.subscription_management_link_provider import (
    SubscriptionManagementLinkProvider,
)

from tapir.mail.models import (
    EmailConfigurationDispatch,
    EmailDispatch,
    ReleaseStatus,
)
from tapir.mail.services.email_dispatch import ResolveAndCreateEmailDispatches
from tapir.mail.services.token import register_tokens
from tapir.mail.tests.factories import (
    EmailConfigurationVersionFactory,
    StaticSegmentFactory,
    StaticSegmentRecipientFactory,
    MailSegmentFactory,
)
from tapir.mail.tests.test_utils import mock_timezone_now, add_mail_segment_provider
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, MemberExtraEmailFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestResolveAndCreateEmailDispatchesCreateEmailDispatches(TapirIntegrationTest):
    NOW = datetime(2023, 9, 10, 12, 30, tzinfo=timezone.utc)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        mock_timezone_now(self, self.NOW)
        self.email_config_version = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED
        )

    def test_createEmailDispatches_noRecipients_raisesValueError(self):
        config_dispatch = self._create_email_config_dispatch(scheduled_time=self.NOW)
        config_dispatch.override_recipients = []
        config_dispatch.save()
        with self.assertRaises(ValueError):
            ResolveAndCreateEmailDispatches._create_email_dispatches(
                config_dispatch=config_dispatch, cache={}
            )

    @patch.object(
        SubscriptionManagementLinkProvider,
        "build_link_for_address",
        autospec=True,
        side_effect=lambda address, cache: f"https://link.for/{address}",
    )
    def test_createEmailDispatches_someRecipientsHaveExtraAddresses_createsADispatchPerAddressWithOverriddenTokens(
        self, _: MagicMock
    ):
        self._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)
        add_mail_segment_provider(
            self,
            lambda: {
                "Test: all members": MailSegmentFactory.build(
                    get_queryset=Member.objects.all
                )
            },
        )
        config_dispatch = self._create_email_config_dispatch(scheduled_time=self.NOW)
        self.email_config_version.content = "FirstName:{{Empfänger.Vorname}} LastName:{{Empfänger.Nachname}} Email:{{Empfänger.Email}} IBAN:{{Empfänger.IBAN}} Link:{{Empfänger (extra).Newsletter - Verwaltungslink}}"
        self.email_config_version.dynamic_segments_additive = ["Test: all members"]
        self.email_config_version.save()
        static_segment = StaticSegmentFactory.create()
        self.email_config_version.static_segments_additive.set([static_segment])
        register_tokens(
            user_tokens={
                "Vorname": "first_name",
                "Nachname": "last_name",
                "IBAN": "iban",
                "Email": "email",
            },
            dynamic_tokens={},
            general_tokens={},
        )
        StaticSegmentRecipientFactory.create(
            segment=static_segment,
            email="static@example.com",
            first_name="FN-static",
            last_name="LN-static",
        )
        MemberFactory.create(
            email="noextra@example.com",
            first_name="FN-noextra",
            last_name="LN-noextra",
            iban="IBANNOEXTRA",
        )
        dynamic_recipient_with_extras = MemberFactory.create(
            email="withextra@example.com",
            first_name="FN-withextra",
            last_name="LN-withextra",
            iban="IBANWITHEXTRA",
        )

        for index in [1, 2]:
            MemberExtraEmailFactory.create(
                member=dynamic_recipient_with_extras,
                email=f"extra{index}@example.com",
                first_name=f"FN-extra{index}",
                last_name=f"LN-extra{index}",
                confirmed_on=self.NOW,
            )

        ResolveAndCreateEmailDispatches._create_email_dispatches(
            config_dispatch=config_dispatch, cache={}
        )

        self.assertEqual(5, EmailDispatch.objects.count())
        actual_addresses = set(
            EmailDispatch.objects.values_list("recipient", flat=True)
        )
        expected_addresses = {
            "static@example.com",
            "noextra@example.com",
            "withextra@example.com",
            "extra1@example.com",
            "extra2@example.com",
        }
        self.assertEqual(expected_addresses, actual_addresses)

        email_dispatches = {
            key: EmailDispatch.objects.get(recipient=f"{key}@example.com")
            for key in ["static", "noextra", "withextra", "extra1", "extra2"]
        }

        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-static",
                "last_name": "LN-static",
                "email": "static@example.com",
                "iban": "",
            },
            email_dispatches["static"].recipient_tokens,
        )
        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-noextra",
                "last_name": "LN-noextra",
                "email": "noextra@example.com",
                "iban": "IBANNOEXTRA",
            },
            email_dispatches["noextra"].recipient_tokens,
        )
        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-withextra",
                "last_name": "LN-withextra",
                "email": "withextra@example.com",
                "iban": "IBANWITHEXTRA",
            },
            email_dispatches["withextra"].recipient_tokens,
        )
        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-extra1",
                "last_name": "LN-extra1",
                "email": "withextra@example.com",
                "iban": "IBANWITHEXTRA",
            },
            email_dispatches["extra1"].recipient_tokens,
        )
        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-extra2",
                "last_name": "LN-extra2",
                "email": "withextra@example.com",
                "iban": "IBANWITHEXTRA",
            },
            email_dispatches["extra2"].recipient_tokens,
        )
        self._assert_management_links_are_built_for_their_own_address(
            email_dispatches=email_dispatches
        )

    def _create_email_config_dispatch(
        self, scheduled_time: datetime, is_sent: bool = False
    ) -> EmailConfigurationDispatch:
        return EmailConfigurationDispatch.objects.create(
            email_configuration_version=self.email_config_version,
            scheduled_time=scheduled_time,
            is_sent=is_sent,
        )

    def _assert_recipient_tokens_are_correct(
        self, expected_tokens: dict, actual_tokens: dict
    ):
        for token in ["first_name", "last_name", "email", "iban"]:
            self.assertEqual(expected_tokens[token], actual_tokens[token])

    def _assert_management_links_are_built_for_their_own_address(
        self, email_dispatches: dict[str, EmailDispatch]
    ):
        for email_dispatch in email_dispatches.values():
            self.assertEqual(
                f"https://link.for/{email_dispatch.recipient}",
                email_dispatch.recipient_tokens[
                    SubscriptionManagementLinkProvider.TOKEN_NAME
                ],
            )
