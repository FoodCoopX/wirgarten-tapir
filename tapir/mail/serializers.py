import datetime

from django.conf import settings
from django.urls import reverse
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from tapir.mail.models import (
    EmailConfiguration,
    EmailConfigurationDispatch,
    EmailConfigurationVersion,
    EmailDispatch,
    EmailTemplate,
    ReleaseStatus,
    EmailTemplateType,
    StaticSegment,
    StaticSegmentRecipient,
    MailCategory,
)
from tapir.mail.registries import get_mail_segments
from tapir.mail.services.mail_category_recipients_resolver import (
    MailCategoryRecipientResolver,
)
from tapir.mail.services.segment import BASE_QUERYSET
from tapir.mail.services.triggers import Trigger, trigger_registry


class TriggerDataSerializer(serializers.Serializer):
    trigger_id = serializers.CharField()
    trigger_field_values = serializers.DictField(child=serializers.CharField())

    @staticmethod
    def validate_trigger_id(trigger_id: str):
        if trigger_id not in trigger_registry.keys():
            raise serializers.ValidationError(f"Invalid trigger id : {trigger_id}")
        return trigger_id

    def validate(self, data: dict):
        trigger_id = data.get("trigger_id", None)
        if not trigger_id:
            return None

        trigger_class = trigger_registry.get(data["trigger_id"], None)
        if not trigger_class:
            raise serializers.ValidationError(f"Unknown trigger: {trigger_id}")

        trigger_values = data.get("trigger_field_values", {})
        self.check_for_missing_fields(trigger_class, trigger_values)

        trigger_class.validate_field_values_and_return_object(trigger_values)

        return data

    @staticmethod
    def check_for_missing_fields(trigger_class: type[Trigger], trigger_field_values):
        expected_fields = [
            field.field_name for field in trigger_class.get_field_definitions()
        ]
        received_fields = trigger_field_values.keys()
        missing_fields = [
            field for field in expected_fields if field not in received_fields
        ]
        if missing_fields:
            raise serializers.ValidationError(
                f"Invalid trigger data. Missing fields: {missing_fields}"
            )


class TriggersSerializationMixin(metaclass=serializers.SerializerMetaclass):
    triggers = serializers.ListSerializer(child=TriggerDataSerializer(), required=False)


class EmailTemplateSerializer(serializers.ModelSerializer):
    # Declared explicitly so DRF does not attach an auto-generated UniqueValidator
    # for the partial "single default layout" UniqueConstraint. That rule is enforced
    # in EmailTemplateViewSet.
    is_default_layout = serializers.BooleanField(required=False)

    class Meta:
        model = EmailTemplate
        fields = "__all__"
        validators = []


class EmailConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailConfiguration
        fields = "__all__"

    released_date = serializers.SerializerMethodField()
    last_updated_draft_date = serializers.SerializerMethodField()
    can_be_deleted = serializers.SerializerMethodField()

    @staticmethod
    def get_released_date(obj: EmailConfiguration) -> datetime.datetime | None:
        released_version = obj.versions.filter(status=ReleaseStatus.RELEASED).first()
        return released_version.updated_at if released_version else None

    @staticmethod
    def get_last_updated_draft_date(
        obj: EmailConfiguration,
    ) -> datetime.datetime | None:
        last_updated_draft = (
            obj.versions.filter(status=ReleaseStatus.DRAFT)
            .order_by("-updated_at")
            .first()
        )
        return last_updated_draft.updated_at if last_updated_draft else None

    @staticmethod
    def get_can_be_deleted(configuration: EmailConfiguration) -> bool:
        for version in configuration.versions.all():
            if not EmailConfigurationVersionSerializer.get_can_be_deleted(version):
                return False
        return True


class SegmentDataSerializer(serializers.Serializer):
    dynamic_segment_names_additive = serializers.ListField(
        child=serializers.CharField()
    )
    dynamic_segment_names_subtractive = serializers.ListField(
        child=serializers.CharField()
    )
    static_segment_ids_additive = serializers.ListField(child=serializers.CharField())
    static_segment_ids_subtractive = serializers.ListField(
        child=serializers.CharField()
    )
    mail_category_ids_additive = serializers.ListField(child=serializers.CharField())

    def validate_dynamic_segment_names_additive(
        self, dynamic_segment_names_additive: list[str]
    ):
        return self.validate_segments(dynamic_segment_names_additive)

    def validate_dynamic_segment_names_subtractive(
        self, dynamic_segment_names_subtractive: list[str]
    ):
        return self.validate_segments(dynamic_segment_names_subtractive)

    @staticmethod
    def validate_segments(segment_names: list[str]):
        invalid_segment_names = [
            segment_name
            for segment_name in segment_names
            if segment_name not in get_mail_segments().keys()
        ]
        if invalid_segment_names:
            raise serializers.ValidationError(
                f"The following segment names are not registered: {invalid_segment_names}"
            )
        return segment_names

    def validate_static_segment_ids_additive(
        self, static_segment_ids_additive: list[str]
    ):
        return self.validate_static_segments_general(static_segment_ids_additive)

    def validate_static_segment_ids_subtractive(
        self, static_segment_ids_subtractive: list[str]
    ):
        return self.validate_static_segments_general(static_segment_ids_subtractive)

    @staticmethod
    def validate_static_segments_general(static_segment_ids):
        existing_segment_ids = set(StaticSegment.objects.values_list("id", flat=True))
        invalid_segment_ids = [
            segment_id
            for segment_id in static_segment_ids
            if segment_id not in existing_segment_ids
        ]
        if invalid_segment_ids:
            raise serializers.ValidationError(
                f"The following static segment ids don't exist: {invalid_segment_ids}"
            )
        return static_segment_ids

    @staticmethod
    def validate_mail_category_ids_additive(mail_category_ids: list[str]):
        valid_ids = set(MailCategory.objects.values_list("id", flat=True))
        invalid_ids = {
            category_id
            for category_id in mail_category_ids
            if category_id not in valid_ids
        }
        if len(invalid_ids) > 0:
            raise serializers.ValidationError(
                f"The following mail category ids are invalid: {mail_category_ids}"
            )
        return mail_category_ids


class EmailConfigurationVersionSerializer(
    TriggersSerializationMixin, serializers.ModelSerializer
):
    class Meta:
        model = EmailConfigurationVersion
        fields = "__all__"

    email_configuration = EmailConfigurationSerializer()
    can_be_deleted = serializers.SerializerMethodField()

    @staticmethod
    def get_can_be_deleted(version: EmailConfigurationVersion) -> bool:
        return not version.emailconfigurationdispatch_set.filter(is_sent=True).exists()


class RecipientSerializer(serializers.Serializer):
    recipients = serializers.ListField(child=serializers.EmailField(), required=True)


class BundledEmailConfigurationSerializer(
    TriggersSerializationMixin, serializers.Serializer
):
    # EmailConfiguration fields
    name = serializers.CharField()
    description = serializers.CharField(
        allow_null=True, allow_blank=True, required=False
    )

    # EmailConfigurationVersion fields
    content = serializers.CharField()
    subject = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    release_status = serializers.CharField()
    updated_at = serializers.DateTimeField(allow_null=True, required=False)
    segment_data = SegmentDataSerializer()
    layout_template_id = serializers.CharField(
        allow_null=True, allow_blank=True, required=False
    )
    layout_enabled = serializers.BooleanField(required=False)

    def validate_layout_template_id(self, value):
        if value in (None, ""):
            return None
        if not EmailTemplate.objects.filter(
            id=value, template_type=EmailTemplateType.LAYOUT
        ).exists():
            raise serializers.ValidationError("Unbekannte Layout-Vorlage.")
        return value


class PreviewSerializer(serializers.Serializer):
    content = serializers.CharField()
    layout_template_id = serializers.CharField(
        allow_null=True, allow_blank=True, required=False
    )
    layout_enabled = serializers.BooleanField(required=False)


class PreviewResponseSerializer(serializers.Serializer):
    html = serializers.CharField()


class EmailConfigurationDispatchSerializer(serializers.Serializer):
    class Meta:
        model = EmailConfigurationDispatch

    id = serializers.CharField()
    email_configuration_version = EmailConfigurationVersionSerializer()
    scheduled_time = serializers.DateTimeField()
    override_recipients = serializers.JSONField()
    override_recipients_display = serializers.SerializerMethodField()
    sent_count = serializers.SerializerMethodField()
    opened_count = serializers.SerializerMethodField()
    delivered_count = serializers.SerializerMethodField()
    error_count = serializers.SerializerMethodField()

    @staticmethod
    def get_sent_count(obj) -> int:
        return obj.emaildispatch_set.filter(
            sent_time__isnull=False, next_retry__isnull=True
        ).count()

    @staticmethod
    def get_opened_count(obj) -> int:
        return obj.emaildispatch_set.filter(
            opened_time__isnull=False, next_retry__isnull=True
        ).count()

    @staticmethod
    def get_delivered_count(obj) -> int:
        return obj.emaildispatch_set.filter(
            dsn_delivered_time__isnull=False,
            next_retry__isnull=True,
            opened_time__isnull=True,
        ).count()

    @staticmethod
    def get_error_count(obj) -> int:
        return (
            obj.emaildispatch_set.filter(next_retry__isnull=True)
            .with_error(True)
            .distinct()
            .count()
        )

    def get_override_recipients_display(
        self, obj: EmailConfigurationDispatch
    ) -> str | None:
        if not obj.override_recipients:
            return None

        if not isinstance(obj.override_recipients, list):
            return str(obj.override_recipients)

        return ", ".join(
            [
                self.get_recipient_display(recipient)
                for recipient in obj.override_recipients
            ]
        )

    @staticmethod
    def get_recipient_display(recipient: dict) -> str:
        if not isinstance(recipient, dict):
            return str(recipient)

        recipient_id_in_base_queryset = recipient.get(
            "recipient_id_in_base_queryset", None
        )
        if recipient_id_in_base_queryset is not None:
            recipient = BASE_QUERYSET.filter(id=recipient_id_in_base_queryset).first()
            if recipient is None:
                return f"Recipient with ID {recipient_id_in_base_queryset}"
            return f"{recipient.first_name} {recipient.last_name} {recipient.email}"

        recipient_outside_of_base_queryset = recipient.get(
            "recipient_outside_of_base_queryset", None
        )
        if recipient_outside_of_base_queryset is None or not isinstance(
            recipient_outside_of_base_queryset, dict
        ):
            return str(recipient)

        return f"{recipient_outside_of_base_queryset.get('first_name', "")} {recipient_outside_of_base_queryset.get('last_name', "")} {recipient_outside_of_base_queryset.get('email', "")}"


class TriggerFieldDefinitionSerializer(serializers.Serializer):
    label = serializers.CharField()
    type = serializers.CharField()
    field_name = serializers.CharField()
    additional_data = serializers.JSONField(required=False, default=dict)


class TriggerDefinitionSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    field_definitions = TriggerFieldDefinitionSerializer(many=True)


class EmailDispatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailDispatch
        fields = "__all__"

    email_configuration_dispatch = EmailConfigurationDispatchSerializer()
    dispatch_status = serializers.ChoiceField(
        choices=EmailDispatch.DispatchStatus.choices, source="get_dispatch_status"
    )


class EmailDispatchWithRetriesSerializer(EmailDispatchSerializer):
    previous_retries = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListSerializer(child=EmailDispatchSerializer()))
    def get_previous_retries(self, obj) -> list[EmailDispatchSerializer]:
        previous_retries = obj.get_previous_retries()
        return EmailDispatchSerializer(previous_retries, many=True).data


class GroupedEmailDispatchSerializer(serializers.Serializer):
    recipient = serializers.CharField(required=True)
    count = serializers.IntegerField(required=True)


class StaticSegmentRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticSegmentRecipient
        fields = "__all__"


class StaticSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaticSegment
        fields = ["id", "name", "recipients", "belongs_to_a_category"]

    recipients = StaticSegmentRecipientSerializer(many=True, read_only=True)
    belongs_to_a_category = serializers.SerializerMethodField()

    @staticmethod
    def get_belongs_to_a_category(obj: StaticSegment) -> bool:
        return getattr(obj, "mailcategory", None) is not None


class MissingTriggerSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    draft_version_exists = serializers.BooleanField()


class CreateMissingTriggerMailSerializer(serializers.Serializer):
    trigger_key = serializers.CharField()
    empty_mjml = serializers.CharField()


class MailCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MailCategory
        fields = [
            "id",
            "name",
            "mode",
            "available_for_external_recipients",
            "nb_recipients",
            "registration_form_link",
            "dynamic_segment_name",
        ]

    nb_recipients = serializers.SerializerMethodField()
    registration_form_link = serializers.SerializerMethodField()

    def get_nb_recipients(self, obj: MailCategory) -> int:
        return len(
            MailCategoryRecipientResolver.resolve_recipients(
                mail_category=obj, cache=self.context["cache"]
            )
        )

    @staticmethod
    def get_registration_form_link(obj: MailCategory) -> str:
        return settings.SITE_URL + reverse(
            "category_registration_external_form", args=[obj.id]
        )


class SegmentOptionSerializer(serializers.Serializer):
    TYPE_DYNAMIC = "dynamic"
    TYPE_STATIC = "static"
    TYPE_CATEGORY = "category"

    id = serializers.CharField()
    type = serializers.ChoiceField(choices=[TYPE_DYNAMIC, TYPE_STATIC, TYPE_CATEGORY])
    label = serializers.CharField()
    group = serializers.CharField()
    description = serializers.CharField(allow_blank=True)


class AvailableSegmentsResponseSerializer(serializers.Serializer):
    segments = SegmentOptionSerializer(many=True)
