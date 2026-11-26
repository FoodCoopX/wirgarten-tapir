import datetime
from dataclasses import dataclass

from django.utils import timezone
from rest_framework import serializers

from tapir.mail.models import EmailConfigurationDispatch
from tapir.mail.serializers import TriggersSerializationMixin
from tapir.mail.service.triggers import Trigger


class DummySerializer(TriggersSerializationMixin, serializers.Serializer):
    pass


@dataclass
class DummyTriggerData:
    a_number: float


class DummyTrigger(Trigger[DummyTriggerData]):
    @classmethod
    def get_id(cls) -> str:
        return "dummy_trigger"

    @classmethod
    def get_display_name(cls) -> str:
        return "Dummy trigger"

    @classmethod
    def get_field_definitions(cls) -> [Trigger.FieldDefinition]:
        return [
            cls.FieldDefinition(field_name="a_number", type="number", label="A number")
        ]

    @classmethod
    def validate_field_values_and_return_object(cls, trigger_field_values):
        if not trigger_field_values["a_number"].isnumeric():
            raise serializers.ValidationError("a_number is not a valid number")

        return DummyTriggerData(a_number=float(trigger_field_values["a_number"]))

    @classmethod
    def after_mail_sent(cls, email_configuration_dispatch: EmailConfigurationDispatch):
        EmailConfigurationDispatch.objects.create(
            email_configuration_version=email_configuration_dispatch.email_configuration_version,
            scheduled_time=timezone.now() + datetime.timedelta(days=1),
        )
