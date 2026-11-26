from rest_framework import serializers

from tapir.mail.service.triggers import register_trigger
from tapir.mail.tests.integration.triggers.DummyTriggerClasses import (
    DummySerializer,
    DummyTrigger,
)
from tapir.mail.tests.test_utils import build_time_trigger_dict
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestTriggerSerializationMixin(TapirIntegrationTest):
    def test_isValid_invalidTriggerName_raisesException(self):
        serializer = DummySerializer(
            data={
                "triggers": [
                    {
                        "trigger_id": "invalid_id",
                        "trigger_field_values": {"a_number": "123"},
                    }
                ]
            }
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_isValid_missingFieldInTriggerData_raisesException(self):
        register_trigger(DummyTrigger)
        serializer = DummySerializer(
            data={
                "triggers": [
                    {"trigger_id": DummyTrigger.get_id(), "trigger_field_values": {}}
                ]
            }
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_isValid_triggerDataFieldHasInvalidValue_raisesException(self):
        register_trigger(DummyTrigger)
        serializer = DummySerializer(
            data={
                "triggers": [
                    {
                        "trigger_id": DummyTrigger.get_id(),
                        "trigger_field_values": {"a_number": "aaa"},
                    }
                ]
            }
        )
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_isValid_serializerHasValidData_returnsTrue(self):
        register_trigger(DummyTrigger)
        valid_trigger = {
            "trigger_id": DummyTrigger.get_id(),
            "trigger_field_values": {"a_number": "123"},
        }
        serializer = DummySerializer(data={"triggers": [valid_trigger]})

        self.assertTrue(serializer.is_valid(raise_exception=True))
        self.assertEqual(
            [valid_trigger], serializer.validated_data.get("triggers", None)
        )

    def test_isValid_multipleTriggers_returnsTrue(self):
        register_trigger(DummyTrigger)
        dummy_trigger = {
            "trigger_id": DummyTrigger.get_id(),
            "trigger_field_values": {"a_number": "123"},
        }
        triggers = [dummy_trigger, build_time_trigger_dict()]
        serializer = DummySerializer(data={"triggers": triggers})

        self.assertTrue(serializer.is_valid(raise_exception=True))
        self.assertEqual(triggers, serializer.validated_data.get("triggers", None))
