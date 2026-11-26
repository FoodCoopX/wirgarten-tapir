import datetime
from dataclasses import dataclass, field
from typing import Callable

from dateutil.relativedelta import relativedelta
from django.utils import timezone

from tapir.mail.services.triggers import Trigger


@dataclass
class TransactionalTriggerData:
    @dataclass
    class RecipientOutsideOfBaseQueryset:
        email: str
        first_name: str
        last_name: str

    key: str
    recipient_id_in_base_queryset: str | None = None
    recipient_outside_of_base_queryset: RecipientOutsideOfBaseQueryset | None = None
    token_data: dict = field(default_factory=dict)


@dataclass
class TransactionalTriggerDataDropdownFieldChoice(
    Trigger.DropdownFieldDefinition.Choice
):
    tokens: dict


class TransactionalTrigger(Trigger[TransactionalTriggerData]):
    transactional_trigger_registry = {}
    trigger_tokens = {}
    required_triggers: dict[str, bool | Callable] = {}
    required_trigger_to_default_content_map = {}

    @classmethod
    def register_action(
        cls,
        name,
        key,
        tokens: dict = None,
        required: bool | Callable = False,
        default_content=None,
    ):
        if tokens is None:
            tokens = {}
        cls.transactional_trigger_registry[key] = name
        if tokens:
            cls.trigger_tokens[key] = tokens

        cls.required_triggers[key] = required
        cls.required_trigger_to_default_content_map[key] = default_content

        must_check_has_default_content = callable(required) or required
        if must_check_has_default_content and default_content is None:
            raise ValueError(
                "If the trigger is required, the default content must be valid MJML content"
            )

    @classmethod
    def is_trigger_required(cls, key: str, cache: dict) -> bool:
        required = cls.required_triggers[key]
        if callable(required):
            required = required(cache)
        return required

    @classmethod
    def fire_action(cls, trigger_data: TransactionalTriggerData):
        if (
            trigger_data.recipient_id_in_base_queryset is None
            and trigger_data.recipient_outside_of_base_queryset is None
        ):
            raise ValueError(
                "At least one of [base_queryset_object_id, recipient_outside_of_base_queryset] must be set"
            )

        if (
            trigger_data.recipient_id_in_base_queryset is not None
            and trigger_data.recipient_outside_of_base_queryset is not None
        ):
            raise ValueError(
                "At most one of [base_queryset_object_id, recipient_outside_of_base_queryset] must be set"
            )

        if trigger_data.key not in cls.transactional_trigger_registry:
            raise ValueError(
                f"Action '{trigger_data.key}' not registered. Available: {set(cls.transactional_trigger_registry.keys())}"
            )

        known_tokens = cls.trigger_tokens.get(trigger_data.key, {})
        for label, token_key in known_tokens.items():
            if token_key not in trigger_data.token_data:
                raise ValueError(
                    f"Token '{token_key}' ({label}) is required for action '{trigger_data.key}'."
                )

        for token_key in trigger_data.token_data:
            if token_key not in known_tokens.values():
                raise ValueError(
                    f"Token '{token_key}' not known for action '{trigger_data.key}'. Available: {set(known_tokens.values())}"
                )

        cls.fire_all_released_configs(trigger_data)

    @classmethod
    def fire_all_released_configs(cls, data: TransactionalTriggerData):
        from tapir.mail.models import EmailConfigurationVersion, ReleaseStatus

        for version in EmailConfigurationVersion.objects.filter(
            status=ReleaseStatus.RELEASED,
        ):
            for trigger in (
                t for t in version.triggers or [] if t.get("trigger_id") == cls.get_id()
            ):
                if trigger["trigger_field_values"]["key"] == data.key:
                    cls.fire_version(
                        version,
                        data,
                    )

    @classmethod
    def fire_version(cls, email_configuration_version, data: TransactionalTriggerData):
        from tapir.mail.models import EmailConfigurationDispatch

        translated_token_data = {}
        trigger_tokens = cls.trigger_tokens.get(data.key, {})
        for key, value in data.token_data.items():
            translated_token_data[
                cls.transactional_trigger_registry[data.key]
                + "."
                + [k for k, value in trigger_tokens.items() if value == key][0]
            ] = value

        EmailConfigurationDispatch.objects.create(
            email_configuration_version=email_configuration_version,
            override_recipients=cls.get_recipients_override(
                email_configuration_version=email_configuration_version, data=data
            ),
            scheduled_time=cls.get_scheduled_date(email_configuration_version, data),
            is_sent=False,
            additional_tokens=translated_token_data,
        )

    @classmethod
    def get_recipients_override(
        cls, email_configuration_version, data: TransactionalTriggerData
    ) -> list:
        if data.recipient_id_in_base_queryset is not None:
            return [
                {"recipient_id_in_base_queryset": data.recipient_id_in_base_queryset}
            ]
        if data.recipient_outside_of_base_queryset is not None:
            return [
                {
                    "recipient_outside_of_base_queryset": {
                        "email": data.recipient_outside_of_base_queryset.email,
                        "first_name": data.recipient_outside_of_base_queryset.first_name,
                        "last_name": data.recipient_outside_of_base_queryset.last_name,
                    }
                }
            ]
        return []

    @classmethod
    def get_scheduled_date(
        cls, email_configuration_version, data: TransactionalTriggerData
    ) -> datetime.datetime:
        return timezone.now() - relativedelta(
            minutes=10
        )  # give it higher priority to be send before mass emails

    @classmethod
    def get_id(cls) -> str:
        return "transactional_trigger"

    @classmethod
    def get_display_name(cls) -> str:
        return "Bei Aktion senden"

    @classmethod
    def get_field_definitions(cls) -> list[Trigger.FieldDefinition]:
        return [
            cls.DropdownFieldDefinition(
                field_name="key",
                label="Aktion auswählen",
                choices=[
                    Trigger.DropdownFieldDefinition.Choice(value=key, label=label)
                    for key, label in cls.transactional_trigger_registry.items()
                ],
            )
        ]
