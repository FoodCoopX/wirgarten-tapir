import datetime
from dataclasses import dataclass

from rest_framework import serializers

from tapir.mail.service.triggers import Trigger


@dataclass
class TimeTriggerData:
    scheduled_time: datetime.datetime


class TimeTrigger(Trigger[TimeTriggerData]):
    @classmethod
    def get_scheduled_date(
        cls, email_configuration_version, data: TimeTriggerData
    ) -> datetime.datetime:
        return data.scheduled_time

    @classmethod
    def get_id(cls) -> str:
        return "time_trigger"

    @classmethod
    def get_display_name(cls) -> str:
        return "Festgelegter Zeitpunkt"

    @classmethod
    def get_field_definitions(cls) -> [Trigger.FieldDefinition]:
        return [
            cls.FieldDefinition(
                field_name="scheduled_time", type="datetime", label="Scheduled time"
            )
        ]

    @classmethod
    def _on_create(cls, email_configuration_version, trigger_data: TimeTriggerData):
        cls.fire_version(
            email_configuration_version,
            trigger_data,
        )

    @classmethod
    def validate_field_values_and_return_object(cls, trigger_field_values):
        try:
            scheduled_time = datetime.datetime.fromisoformat(
                trigger_field_values["scheduled_time"]
            )
        except ValueError as ve:
            raise serializers.ValidationError(
                f"Invalid value for scheduled_time: {trigger_field_values['scheduled_time']}, error: {ve}"
            )
        return TimeTriggerData(scheduled_time=scheduled_time)
