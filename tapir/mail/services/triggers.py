import datetime
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Generic, TypeVar

from django.utils import timezone

TriggerData = TypeVar("TriggerData")

LOG = logging.getLogger(__name__)


class Trigger(Generic[TriggerData], ABC):
    @dataclass
    class FieldDefinition:
        label: str
        type: str
        field_name: str
        additional_data: dict = field(default_factory=dict)

    @dataclass
    class DropdownFieldDefinition(FieldDefinition):
        @dataclass
        class Choice:
            label: str
            value: str

        type: str = field(init=False, default="dropdown")
        choices: list[Choice] = field(default_factory=list)

        def __post_init__(self):
            self.additional_data["choices"] = [
                choice.__dict__ for choice in self.choices
            ]

    @classmethod
    def fire_all_released_configs(cls, data: TriggerData):
        from tapir.mail.models import EmailConfigurationVersion, ReleaseStatus

        for version in EmailConfigurationVersion.objects.filter(
            status=ReleaseStatus.RELEASED
        ):
            if cls.get_id() not in [
                trigger["trigger_id"] for trigger in version.triggers
            ]:
                continue
            cls.fire_version(email_configuration_version=version, data=data)

    @classmethod
    def fire_version(cls, email_configuration_version, data: TriggerData):
        from tapir.mail.models import EmailConfigurationDispatch

        EmailConfigurationDispatch.objects.create(
            email_configuration_version=email_configuration_version,
            override_recipients=cls.get_recipients_override(
                email_configuration_version=email_configuration_version, data=data
            ),
            scheduled_time=cls.get_scheduled_date(email_configuration_version, data),
            is_sent=False,
        )

    @classmethod
    def get_scheduled_date(
        cls, email_configuration_version, data: TriggerData
    ) -> datetime.datetime:
        return timezone.now()

    @classmethod
    def get_recipients_override(
        cls, email_configuration_version, data: TriggerData
    ) -> list:
        return []

    @classmethod
    @abstractmethod
    def get_id(cls) -> str:
        pass

    @classmethod
    @abstractmethod
    def get_display_name(cls) -> str:
        pass

    @classmethod
    def get_field_definitions(cls) -> list[FieldDefinition]:
        return []

    @staticmethod
    def on_email_configuration_version_save(email_configuration_version):
        from tapir.mail.models import ReleaseStatus, EmailConfigurationDispatch

        if email_configuration_version.status != ReleaseStatus.RELEASED:
            EmailConfigurationDispatch.objects.filter(
                email_configuration_version=email_configuration_version, is_sent=False
            ).delete()
            return

        EmailConfigurationDispatch.objects.filter(
            email_configuration_version__email_configuration=email_configuration_version.email_configuration,
            is_sent=False,
        ).delete()

        if not email_configuration_version.triggers:
            return

        for trigger_data in email_configuration_version.triggers:
            trigger_id = trigger_data["trigger_id"]
            if trigger_id not in trigger_registry.keys():
                LOG.warning(
                    f"EmailConfigurationVersion "
                    f"{email_configuration_version.id} {email_configuration_version.email_configuration.name} "
                    f"has an unknown trigger : {trigger_id}"
                )
                continue
            trigger_class = trigger_registry[trigger_id]
            trigger_class._on_create(
                email_configuration_version,
                trigger_class.validate_field_values_and_return_object(
                    trigger_data["trigger_field_values"]
                ),
            )

    @classmethod
    def _on_create(cls, email_configuration_version, trigger_data: TriggerData):
        # Override this method if your trigger must for example fire on create
        pass

    @classmethod
    def after_mail_sent(cls, email_configuration_dispatch):
        # Override this if you want to repeat the trigger after it's been sent,
        # for example for a weekly trigger
        pass

    @classmethod
    def validate_field_values_and_return_object(cls, trigger_field_values):
        # Override this if you want to validate the content of the trigger_field_values variable
        # from EmailConfigurationVersion
        return None


trigger_registry: Dict[str, type[Trigger]] = {}


def register_trigger(trigger: type[Trigger]):
    trigger_registry[trigger.get_id()] = trigger
