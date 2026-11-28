import datetime
from unittest.mock import MagicMock, patch

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from tapir.mail.models import (
    EmailConfigurationVersion,
    ReleaseStatus,
)
from tapir.mail.tests.test_utils import mock_timezone_now
from tapir.wirgarten.tests.test_utils import TapirUnitTest
from tapir.mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)


class TransactionalTriggerTest(TapirUnitTest):
    NOW = datetime.datetime(
        year=2023, month=9, day=10, hour=12, minute=30, tzinfo=datetime.UTC
    )
    maxDiff = 1000

    def setUp(self):
        mock_timezone_now(self, self.NOW)
        TransactionalTrigger.transactional_trigger_registry = {}
        TransactionalTrigger.trigger_tokens = {}
        TransactionalTrigger.required_triggers = {}
        TransactionalTrigger.required_trigger_to_default_content_map = {}

    def test_registerAction_validInput_actionRegistered(self):
        TransactionalTrigger.register_action("test_action", "test_key")
        self.assertIn("test_key", TransactionalTrigger.transactional_trigger_registry)

    def test_registerAction_duplicateKey_lastActionRegistered(self):
        TransactionalTrigger.register_action("first_action", "duplicate_key")
        TransactionalTrigger.register_action("second_action", "duplicate_key")
        self.assertEqual(
            TransactionalTrigger.transactional_trigger_registry["duplicate_key"],
            "second_action",
        )

    def test_fireAction_unregisteredKey_exceptionRaised(self):
        with self.assertRaises(ValueError):
            TransactionalTrigger.fire_action(
                TransactionalTriggerData(
                    key="test_key", recipient_id_in_base_queryset="test_id"
                )
            )

    @patch(
        "tapir.mail.triggers.transactional_trigger.TransactionalTrigger.fire_all_released_configs"
    )
    def test_fireAction_registeredKey_fireAllCalled(self, mock_fire_all):
        TransactionalTrigger.register_action("test_action", "test_key")
        data = TransactionalTriggerData(
            key="test_key", recipient_id_in_base_queryset="test_id"
        )
        TransactionalTrigger.fire_action(data)
        mock_fire_all.assert_called_once_with(data)

    @patch("tapir.mail.models.EmailConfigurationVersion.objects.filter")
    @patch(
        "tapir.mail.triggers.transactional_trigger.TransactionalTrigger.fire_version"
    )
    def test_fireAction_differentConfigs_correctConfigFired(
        self, mock_fire_version, mock_filter
    ):
        version_1 = MagicMock(
            spec=EmailConfigurationVersion, status=ReleaseStatus.RELEASED
        )
        version_1.triggers = [
            {
                "trigger_id": TransactionalTrigger.get_id(),
                "trigger_field_values": {"key": "test_key_1"},
            }
        ]
        version_2 = MagicMock(
            spec=EmailConfigurationVersion, status=ReleaseStatus.RELEASED
        )
        version_2.triggers = [
            {
                "trigger_id": TransactionalTrigger.get_id(),
                "trigger_field_values": {"key": "test_key_2"},
            }
        ]

        mock_filter.return_value = [version_1, version_2]

        TransactionalTrigger.register_action("test_action_1", "test_key_1")
        TransactionalTrigger.register_action("test_action_2", "test_key_2")
        data = TransactionalTriggerData(
            key="test_key_1",
            recipient_id_in_base_queryset="test_id",
            token_data={},
        )
        TransactionalTrigger.fire_all_released_configs(data=data)

        mock_fire_version.assert_called_once_with(
            version_1,
            data,
        )

    @patch("tapir.mail.models.EmailConfigurationDispatch.objects.create")
    def test_fireVersion_validInput_createDispatchCalled(self, mock_create_dispatch):
        data = TransactionalTriggerData(
            key="test_key", recipient_id_in_base_queryset="test_id"
        )
        version = MagicMock(spec=EmailConfigurationVersion)
        TransactionalTrigger.fire_version(version, data)

        expected_params = {
            "email_configuration_version": version,
            "override_recipients": [{"recipient_id_in_base_queryset": "test_id"}],
            "scheduled_time": self.NOW - relativedelta(minutes=10),
            "is_sent": False,
            "additional_tokens": {},
        }

        mock_create_dispatch.assert_called_once_with(**expected_params)

    @patch("tapir.mail.models.EmailConfigurationVersion.objects.filter")
    @patch(
        "tapir.mail.triggers.transactional_trigger.TransactionalTrigger.fire_version"
    )
    def test_fireAllReleasedConfigs_multipleVersions_onlyReleasedFired(
        self, mock_fire_version, mock_filter
    ):
        released_version = MagicMock(
            spec=EmailConfigurationVersion, status=ReleaseStatus.RELEASED
        )
        unreleased_version = MagicMock(
            spec=EmailConfigurationVersion, status=ReleaseStatus.DRAFT
        )
        released_version.triggers = [
            {
                "trigger_id": TransactionalTrigger.get_id(),
                "trigger_field_values": {"key": "test_key"},
            }
        ]
        unreleased_version.triggers = []

        mock_filter.return_value = [released_version, unreleased_version]

        TransactionalTrigger.register_action("test_action", "test_key")
        data = TransactionalTriggerData(
            key="test_key",
            recipient_id_in_base_queryset="test_id",
        )
        TransactionalTrigger.fire_all_released_configs(data)

        mock_fire_version.assert_called_once_with(
            released_version,
            data,
        )

    def test_getRecipientsOverride_recipientFromQueryset_correctRecipientReturned(self):
        recipients = TransactionalTrigger.get_recipients_override(
            None,
            TransactionalTriggerData(
                key="test",
                recipient_id_in_base_queryset="test_id",
            ),
        )
        self.assertEqual(recipients, [{"recipient_id_in_base_queryset": "test_id"}])

    def test_getRecipientsOverride_recipientOutsideOfQueryset_correctRecipientReturned(
        self,
    ):
        recipients = TransactionalTrigger.get_recipients_override(
            None,
            TransactionalTriggerData(
                key="test",
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email="test@test.de", first_name="Max", last_name="Mustermann"
                ),
            ),
        )
        self.assertEqual(
            recipients,
            [
                {
                    "recipient_outside_of_base_queryset": {
                        "email": "test@test.de",
                        "first_name": "Max",
                        "last_name": "Mustermann",
                    }
                }
            ],
        )

    def test_getScheduledDate_validData_correctDateCalculated(self):
        scheduled_date = TransactionalTrigger.get_scheduled_date(
            None,
            TransactionalTriggerData(
                key="test",
                recipient_id_in_base_queryset="test_id",
            ),
        )
        expected_date = timezone.now() - relativedelta(minutes=10)
        self.assertAlmostEqual(
            scheduled_date, expected_date, delta=datetime.timedelta(seconds=1)
        )

    def test_getFieldDefinitions_validRegistry_correctDefinitionsReturned(self):
        TransactionalTrigger.transactional_trigger_registry = {
            "test_key_1": "test_action_1",
            "test_key_2": "test_action_2",
        }

        field_definitions = TransactionalTrigger.get_field_definitions()
        self.assertEqual(len(field_definitions), 1)
        dropdown_field = field_definitions[0]
        self.assertEqual(dropdown_field.field_name, "key")
        self.assertEqual(dropdown_field.label, "Aktion auswählen")

        expected_choices = [
            TransactionalTrigger.DropdownFieldDefinition.Choice(
                value="test_key_1", label="test_action_1"
            ),
            TransactionalTrigger.DropdownFieldDefinition.Choice(
                value="test_key_2", label="test_action_2"
            ),
        ]

        for expected_choice, actual_choice in zip(
            expected_choices, dropdown_field.choices
        ):
            self.assertEqual(expected_choice.value, actual_choice.value)
            self.assertEqual(expected_choice.label, actual_choice.label)

    def test_fireAction_wrongTokens_throwsException(self):
        action_key = "test_action_with_token"
        TransactionalTrigger.register_action(
            "Test Trigger",
            action_key,
            {"Transactional Token Label": "transactional_token"},
        )
        self.assertEqual(
            TransactionalTrigger.trigger_tokens[action_key],
            {"Transactional Token Label": "transactional_token"},
        )

        with self.assertRaises(ValueError):
            TransactionalTrigger.fire_action(
                TransactionalTriggerData(
                    key=action_key,
                    recipient_id_in_base_queryset="test_id",
                    token_data={},
                )
            )

        with self.assertRaises(ValueError):
            TransactionalTrigger.fire_action(
                TransactionalTriggerData(
                    key=action_key,
                    recipient_id_in_base_queryset="test_id",
                    token_data={"wrong_token": "test_token_value"},
                )
            )

    @patch(
        "tapir.mail.triggers.transactional_trigger.TransactionalTrigger.fire_all_released_configs"
    )
    def test_fireAction_correctTokens_tokensPersisted(
        self, mock_fire_all_released_configs
    ):
        action_key = "test_action_with_token"
        TransactionalTrigger.register_action(
            "Test Trigger",
            action_key,
            {"Transactional Token Label": "transactional_token"},
        )

        data = TransactionalTriggerData(
            key=action_key,
            recipient_id_in_base_queryset="test_id",
            token_data={"transactional_token": "test_token_value"},
        )

        TransactionalTrigger.fire_action(trigger_data=data)

        mock_fire_all_released_configs.assert_called_once_with(data)

    def test_isTriggerRequired_requiredIsCallable_callsItWithGivenCache(self):
        received_caches = []

        def required(cache: dict):
            received_caches.append(cache)
            return True

        TransactionalTrigger.required_triggers = {"test_key": required}
        given_cache = {}

        result = TransactionalTrigger.is_trigger_required(
            key="test_key", cache=given_cache
        )

        self.assertTrue(result)
        self.assertEqual(1, len(received_caches))
        self.assertIs(given_cache, received_caches[0])

    def test_isTriggerRequired_requiredIsBool_returnsIt(self):
        TransactionalTrigger.required_triggers = {"test_key": False}

        self.assertFalse(
            TransactionalTrigger.is_trigger_required(key="test_key", cache={})
        )
