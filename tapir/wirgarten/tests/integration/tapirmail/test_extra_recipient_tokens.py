import datetime

from tapir_mail.models import EmailDispatch, EmailConfigurationDispatch, ReleaseStatus
from tapir_mail.service.email_dispatch import ResolveAndCreateEmailDispatches
from tapir_mail.service.token import register_tokens
from tapir_mail.tests.factories import EmailConfigurationVersionFactory

from tapir.wirgarten.models import MemberExtraEmail
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tapirmail import Segments, configure_mail_module
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestExtraRecipientTokens(TapirIntegrationTest):

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, value=True)

    def test_createEmailDispatches_someRecipientsHaveExtraAddresses_createsADispatchForEachRecipientAndExtras(
        self,
    ):
        now = mock_timezone(
            test=self,
            now=datetime.datetime(2023, 9, 10, 12, 30, tzinfo=datetime.timezone.utc),
        )
        configure_mail_module()
        email_config_version = EmailConfigurationVersionFactory.create(
            status=ReleaseStatus.RELEASED,
            content="FirstName:{{Empfänger.Vorname}} LastName:{{Empfänger.Nachname}} Email:{{Empfänger.Email}} IBAN:{{Empfänger.IBAN}}",
            dynamic_segments_additive=[Segments.ALL_USERS],
        )
        config_dispatch = EmailConfigurationDispatch.objects.create(
            email_configuration_version=email_config_version,
            scheduled_time=now,
            is_sent=False,
        )

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
        original_recipient = MemberFactory.create(
            email="original@example.com",
            first_name="FN-original",
            last_name="LN-original",
            iban="IBANORIGINAL",
        )
        MemberExtraEmail.objects.create(
            member=original_recipient,
            email="extra@example.com",
            confirmed_on=now,
            first_name="FN-extra",
            last_name="LN-extra",
        )

        ResolveAndCreateEmailDispatches._create_email_dispatches(config_dispatch)

        self.assertEqual(2, EmailDispatch.objects.count())
        actual_addresses = set(
            EmailDispatch.objects.values_list("recipient", flat=True)
        )
        expected_addresses = {
            "original@example.com",
            "extra@example.com",
        }
        self.assertEqual(expected_addresses, actual_addresses)

        email_dispatches = {
            key: EmailDispatch.objects.get(recipient=f"{key}@example.com")
            for key in ["original", "extra"]
        }

        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-original",
                "last_name": "LN-original",
                "email": "original@example.com",
                "iban": "IBANORIGINAL",
            },
            email_dispatches["original"].recipient_tokens,
        )
        self._assert_recipient_tokens_are_correct(
            {
                "first_name": "FN-extra",
                "last_name": "LN-extra",
                "email": "original@example.com",
                "iban": "IBANORIGINAL",
            },
            email_dispatches["extra"].recipient_tokens,
        )

    def _assert_recipient_tokens_are_correct(
        self, expected_tokens: dict, actual_tokens: dict
    ):
        for token in ["first_name", "last_name", "email", "iban"]:
            self.assertEqual(expected_tokens[token], actual_tokens[token])
