import datetime
import logging

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, QuerySet
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import FormView, TemplateView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.mail.config import MAIL_URL_PREFIX, TransactionalTriggerKeys
from tapir.mail.forms import RegisterToMailCategoryForm, ExternalRecipientManagementForm
from tapir.mail.models import (
    EmailConfiguration,
    EmailConfigurationDispatch,
    EmailConfigurationVersion,
    EmailDispatch,
    EmailTemplate,
    EmailTemplateType,
    ReleaseStatus,
    StaticSegment,
    StaticSegmentRecipient,
    MailCategory,
    ExternalRecipient,
    ExternalRecipientConfirmation,
)
from tapir.mail.registries import get_mail_segment_definitions
from tapir.mail.serializers import (
    BundledEmailConfigurationSerializer,
    EmailConfigurationDispatchSerializer,
    EmailConfigurationSerializer,
    EmailConfigurationVersionSerializer,
    EmailDispatchSerializer,
    EmailDispatchWithRetriesSerializer,
    EmailTemplateSerializer,
    GroupedEmailDispatchSerializer,
    RecipientSerializer,
    SegmentDataSerializer,
    TriggerDefinitionSerializer,
    StaticSegmentSerializer,
    StaticSegmentRecipientSerializer,
    MissingTriggerSerializer,
    CreateMissingTriggerMailSerializer,
    MailCategorySerializer,
    AvailableSegmentsResponseSerializer,
    SegmentOptionSerializer,
    PreviewSerializer,
    PreviewResponseSerializer,
)
from tapir.mail.service.email import prepare_email
from tapir.mail.service.layout import (
    BODY_PLACEHOLDER_SECTION_RE,
    BODY_TOKEN_RE,
    apply_layout,
    render_email_mjml,
)
from tapir.mail.service.mjml import mjml2html
from tapir.mail.service.email_dispatch import RetryEmailDispatch
from tapir.mail.service.external_recipient_manager import ExternalRecipientManager
from tapir.mail.service.mail_content_validator import MailContentValidator
from tapir.mail.service.segment import (
    resolve_segments,
)
from tapir.mail.service.token import replace_tokens, token_registry
from tapir.mail.service.tracking import track_email_opening
from tapir.mail.service.triggers import Trigger, trigger_registry
from tapir.mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

LOG = logging.getLogger(__name__)


class EmailTemplateViewSet(viewsets.ModelViewSet):
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer

    def perform_create(self, serializer):
        self.validate_layout(serializer)
        self.save_with_single_default_layout(serializer)

    def perform_update(self, serializer):
        self.validate_layout(serializer)
        self.save_with_single_default_layout(serializer)

    @staticmethod
    def validate_layout(serializer):
        template_type = serializer.validated_data.get(
            "template_type",
            getattr(serializer.instance, "template_type", EmailTemplateType.START),
        )
        content = serializer.validated_data.get(
            "content", getattr(serializer.instance, "content", "")
        )
        is_default_layout = serializer.validated_data.get(
            "is_default_layout",
            getattr(serializer.instance, "is_default_layout", False),
        )

        if template_type == EmailTemplateType.LAYOUT:
            body_section_count = len(BODY_PLACEHOLDER_SECTION_RE.findall(content))
            if body_section_count != 1:
                raise ValidationError(
                    {
                        "content": "Eine Layout-Vorlage muss genau einen E-Mail-Inhalt-Block enthalten."
                    }
                )
            MailContentValidator.validate_tokens(
                mail_content=BODY_TOKEN_RE.sub("", content),
                trigger_datas=[],
            )
        elif is_default_layout:
            raise ValidationError(
                {
                    "is_default_layout": "Nur Layout-Vorlagen können als Standard markiert werden."
                }
            )

    @staticmethod
    def save_with_single_default_layout(serializer):
        with transaction.atomic():
            if serializer.validated_data.get("is_default_layout"):
                EmailTemplate.objects.filter(is_default_layout=True).exclude(
                    id=getattr(serializer.instance, "id", None)
                ).update(is_default_layout=False)
            serializer.save()


class PaginatedEmailTemplateViewSet(EmailTemplateViewSet):
    pagination_class = LimitOffsetPagination


class EmailConfigurationViewSet(viewsets.ModelViewSet):
    queryset = EmailConfiguration.objects.all().distinct()
    filterset_fields = ["versions__status"]
    serializer_class = EmailConfigurationSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return super().get_queryset().order_by("-updated_at")

    @extend_schema(
        responses={200: EmailConfigurationVersionSerializer(many=True)},
    )
    @action(detail=True, methods=["GET"])
    def versions(self, request, pk=None):
        email_configuration = get_object_or_404(EmailConfiguration, id=pk)
        pagination = self.pagination_class()
        queryset = email_configuration.versions.all().order_by("-updated_at")
        pagination.count = pagination.limit = queryset.count()
        pagination.offset = 0
        serializer = EmailConfigurationVersionSerializer(queryset, many=True)
        return pagination.get_paginated_response(serializer.data)

    @extend_schema(
        responses={200: EmailConfigurationSerializer(many=False)},
    )
    @action(detail=True, methods=["GET"])
    def duplicate(self, request, pk=None):
        copy_source = get_object_or_404(EmailConfiguration, id=pk)

        base_name = f"Kopie von: {copy_source.name}"
        indexed_name = base_name
        counter = 0
        while EmailConfiguration.objects.filter(name=indexed_name).exists():
            counter += 1
            indexed_name = f"{base_name} ({counter})"

        with transaction.atomic():
            copy_destination = EmailConfiguration.objects.create(
                name=indexed_name,
                description=copy_source.description,
            )
            self.duplication_best_version(copy_source, copy_destination)

        serializer = EmailConfigurationSerializer(copy_destination, many=False)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def duplication_best_version(
        configuration_copy_source: EmailConfiguration,
        configuration_copy_destination: EmailConfiguration,
    ):
        versions = configuration_copy_source.versions.order_by("-updated_at")
        if not versions.exists():
            return

        version_copy_source = versions.filter(status=ReleaseStatus.RELEASED).first()
        if not version_copy_source:
            version_copy_source = versions.filter(status=ReleaseStatus.DRAFT).first()
        if not version_copy_source:
            version_copy_source = versions.filter(status=ReleaseStatus.ARCHIVED).first()
        if not version_copy_source:
            version_copy_source = versions.first()
        if not version_copy_source:
            return

        fields_to_copy = [
            "content",
            "subject",
            "triggers",
            "dynamic_segments_additive",
            "dynamic_segments_subtractive",
            "layout_template",
            "layout_enabled",
        ]
        version_copy_destination = EmailConfigurationVersion.objects.create(
            **{
                field_name: getattr(version_copy_source, field_name)
                for field_name in fields_to_copy
            },
            email_configuration=configuration_copy_destination,
            status=ReleaseStatus.DRAFT,
        )
        version_copy_destination.static_segments_additive.set(
            version_copy_source.static_segments_additive.all()
        )
        version_copy_destination.static_segments_subtractive.set(
            version_copy_source.static_segments_subtractive.all()
        )
        version_copy_destination.mail_categories_additive.set(
            version_copy_source.mail_categories_additive.all()
        )

    @classmethod
    def does_email_configuration_version_have_trigger(
        cls, trigger_id: str, email_configuration_version: EmailConfigurationVersion
    ):
        for trigger_data in email_configuration_version.triggers:
            if trigger_data["trigger_id"] == trigger_id:
                return True

        return False

    @classmethod
    def filter_email_configurations_by_trigger_id(
        cls, queryset: QuerySet[EmailConfiguration], trigger_id: str
    ):
        email_configuration_ids_with_trigger = []
        for email_configuration in EmailConfiguration.objects.all():
            last_version = email_configuration.versions.order_by("updated_at").last()
            if cls.does_email_configuration_version_have_trigger(
                trigger_id=trigger_id,
                email_configuration_version=last_version,
            ):
                email_configuration_ids_with_trigger.append(email_configuration.id)

        return queryset.filter(id__in=email_configuration_ids_with_trigger)

    @extend_schema(
        responses={200: EmailConfigurationSerializer(many=True)},
        parameters=[
            OpenApiParameter(name="trigger_id", required=False, type=OpenApiTypes.STR),
        ],
    )
    @action(detail=False, methods=["GET"])
    def filter_by_trigger(self, request, *args, **kwargs):
        queryset: QuerySet[EmailConfiguration] = self.filter_queryset(
            self.get_queryset()
        )

        trigger_id = request.query_params.get("trigger_id", None)
        if trigger_id is not None:
            queryset = self.filter_email_configurations_by_trigger_id(
                queryset, trigger_id
            )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    send_email=extend_schema(
        operation_id="email_configuration_version_send_test_email",
        request={
            "type": "object",
            "properties": {
                "recipients": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["recipients"],
        },
    ),
)
class EmailConfigurationVersionViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = EmailConfigurationVersion.objects.all()
    serializer_class = BundledEmailConfigurationSerializer

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = BundledEmailConfigurationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create EmailConfiguration
        email_configuration = EmailConfiguration.objects.get_or_create(
            name=serializer.validated_data["name"],
        )[0]
        email_configuration.description = (
            (serializer.validated_data["description"],)
            if "description" in serializer.validated_data
            else None
        )
        email_configuration.save()

        release_status = serializer.validated_data["release_status"]

        # Create EmailConfigurationVersion
        MailContentValidator.validate_tokens(
            mail_content=serializer.validated_data["content"],
            trigger_datas=serializer.validated_data.get("triggers", []),
        )
        segment_data = serializer.validated_data.get("segment_data", {})
        new_version = EmailConfigurationVersion.objects.create(
            email_configuration=email_configuration,
            content=serializer.validated_data["content"],
            subject=serializer.validated_data.get("subject", None),
            status=release_status,
            triggers=serializer.validated_data.get("triggers", None),
            dynamic_segments_additive=segment_data.get(
                "dynamic_segment_names_additive", []
            ),
            dynamic_segments_subtractive=segment_data.get(
                "dynamic_segment_names_subtractive", []
            ),
        )
        new_version.static_segments_additive.set(
            StaticSegment.objects.filter(
                id__in=segment_data.get("static_segment_ids_additive", [])
            )
        )
        new_version.static_segments_subtractive.set(
            StaticSegment.objects.filter(
                id__in=segment_data.get("static_segment_ids_subtractive", [])
            )
        )
        new_version.mail_categories_additive.set(
            MailCategory.objects.filter(
                id__in=segment_data.get("mail_category_ids_additive", [])
            )
        )

        layout_template_id = serializer.validated_data.get("layout_template_id", None)
        has_default_layout = EmailTemplate.objects.filter(
            template_type=EmailTemplateType.LAYOUT, is_default_layout=True
        ).exists()
        new_version.layout_template_id = layout_template_id
        new_version.layout_enabled = serializer.validated_data.get(
            "layout_enabled",
            layout_template_id is not None or has_default_layout,
        )
        if not new_version.layout_enabled:
            new_version.layout_template_id = None
        new_version.save()

        if release_status == ReleaseStatus.RELEASED:
            new_version.release()

        Trigger.on_email_configuration_version_save(new_version)

        return Response({"id": new_version.id}, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, pk=None, *args, **kwargs):
        updated_version: EmailConfigurationVersion = self.get_object()

        email_configuration = updated_version.email_configuration

        initial_data = {
            "name": email_configuration.name,
            "description": email_configuration.description,
            "content": updated_version.content,
            "subject": updated_version.subject,
            "release_status": updated_version.status,
            "triggers": updated_version.triggers,
        }
        serializer = BundledEmailConfigurationSerializer(
            data=request.data, initial=initial_data
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Update EmailConfiguration
        email_configuration.name = serializer.validated_data["name"]
        email_configuration.description = serializer.validated_data.get(
            "description", None
        )
        email_configuration.save()

        release_status = serializer.validated_data["release_status"]

        # Update EmailConfigurationVersion
        MailContentValidator.validate_tokens(
            mail_content=serializer.validated_data["content"],
            trigger_datas=serializer.validated_data.get("triggers", []),
        )
        updated_version.content = serializer.validated_data["content"]
        updated_version.subject = serializer.validated_data.get("subject", None)
        updated_version.status = release_status
        updated_version.triggers = serializer.validated_data.get("triggers", None)

        segment_data = serializer.validated_data.get("segment_data", {})
        updated_version.dynamic_segments_additive = segment_data.get(
            "dynamic_segment_names_additive", []
        )
        updated_version.dynamic_segments_subtractive = segment_data.get(
            "dynamic_segment_names_subtractive", []
        )
        updated_version.static_segments_additive.set(
            StaticSegment.objects.filter(
                id__in=segment_data.get("static_segment_ids_additive", [])
            )
        )
        updated_version.static_segments_subtractive.set(
            StaticSegment.objects.filter(
                id__in=segment_data.get("static_segment_ids_subtractive", [])
            )
        )
        updated_version.mail_categories_additive.set(
            MailCategory.objects.filter(
                id__in=segment_data.get("mail_category_ids_additive", [])
            )
        )

        if "layout_template_id" in serializer.validated_data:
            updated_version.layout_template_id = serializer.validated_data[
                "layout_template_id"
            ]
        updated_version.layout_enabled = serializer.validated_data.get(
            "layout_enabled", updated_version.layout_enabled
        )
        if not updated_version.layout_enabled:
            updated_version.layout_template_id = None
        updated_version.save()

        if release_status == ReleaseStatus.RELEASED:
            updated_version.release()

        Trigger.on_email_configuration_version_save(updated_version)

        return Response(serializer.data)

    @extend_schema(responses={200: BundledEmailConfigurationSerializer})
    @action(detail=True, methods=["GET"])
    def get_bundled_info(self, request, pk=None):
        version: EmailConfigurationVersion = self.get_object()
        email_configuration = version.email_configuration

        serializer = BundledEmailConfigurationSerializer(
            {
                "name": email_configuration.name,
                "description": email_configuration.description,
                "content": version.content,
                "subject": version.subject,
                "updated_at": version.updated_at,
                "release_status": version.status,
                "segment_data": {
                    "dynamic_segment_names_additive": version.dynamic_segments_additive,
                    "dynamic_segment_names_subtractive": version.dynamic_segments_subtractive,
                    "static_segment_ids_additive": version.static_segments_additive.values_list(
                        "id", flat=True
                    ),
                    "static_segment_ids_subtractive": version.static_segments_subtractive.values_list(
                        "id", flat=True
                    ),
                    "mail_category_ids_additive": version.mail_categories_additive.values_list(
                        "id", flat=True
                    ),
                },
                "layout_template_id": version.layout_template_id,
                "layout_enabled": version.layout_enabled,
                "triggers": version.triggers,
            }
        )

        return Response(serializer.data)

    @transaction.atomic
    def destroy(self, request, pk=None, *args, **kwargs):
        version = self.get_object()
        EmailConfigurationDispatch.objects.filter(
            email_configuration_version=version
        ).delete()
        version.delete()

        if (
            EmailConfigurationVersion.objects.filter(
                email_configuration=version.email_configuration
            ).count()
            == 0
        ):
            version.email_configuration.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=["POST"])
    def release(self, request, pk=None):
        version = self.get_object()
        version.release()
        return Response({"status": ReleaseStatus.RELEASED})

    @extend_schema(
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=["POST"])
    def archive(self, request, pk=None):
        version = self.get_object()
        version.archive()
        return Response({"status": ReleaseStatus.ARCHIVED})

    @extend_schema(
        request=None,
        responses={200: OpenApiTypes.OBJECT},
    )
    @action(detail=True, methods=["POST"])
    def draft(self, request, pk=None):
        version = self.get_object()
        version.status = ReleaseStatus.DRAFT
        version.save()
        return Response({"status": ReleaseStatus.DRAFT})

    @extend_schema(
        request=RecipientSerializer,
        responses={200: OpenApiTypes.OBJECT},
        operation_id="email_configuration_version_send_test_email",
    )
    @action(detail=True, methods=["post"])
    def send_test_email(self, request, pk=None):
        email_version_configuration = get_object_or_404(
            EmailConfigurationVersion, id=pk
        )
        recipients = request.data.get("recipients", [])

        if len(recipients) == 0:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"message": "Recipients parameter is required"},
            )

        try:
            recipients_list = [email.strip() for email in recipients]
        except Exception as e:
            return Response(
                status=status.HTTP_400_BAD_REQUEST,
                data={"message": f"Invalid recipients parameter: {str(e)}"},
            )

        cache = {}
        for email in recipients_list:
            mjml = replace_tokens(
                render_email_mjml(email_version_configuration),
                {"email": email},
                strict_token_validation=False,
                cache=cache,
            )
            email = prepare_email(
                mjml=mjml,
                subject=email_version_configuration.subject,
                recipients=[email],
            )
            email.send()

        LOG.info("Test email sent to: " + ", ".join(recipients_list))

        return Response(
            status=status.HTTP_200_OK,
            data={"message": f"Test email sent to: {', '.join(recipients_list)}"},
        )

    @extend_schema(
        request=PreviewSerializer,
        responses={200: PreviewResponseSerializer},
        operation_id="email_configuration_version_preview",
    )
    @action(detail=False, methods=["post"])
    def preview(self, request):
        serializer = PreviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        content = serializer.validated_data["content"]
        layout_template_id = serializer.validated_data.get("layout_template_id", None)
        layout_enabled = serializer.validated_data.get("layout_enabled", True)

        if not layout_enabled:
            effective_mjml = content
        elif layout_template_id:
            layout_template = EmailTemplate.objects.filter(
                id=layout_template_id, template_type=EmailTemplateType.LAYOUT
            ).first()
            if layout_template is None:
                return Response(
                    {"message": f"Unknown layout template: {layout_template_id}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            effective_mjml = apply_layout(content, layout_template.content)
        else:
            default_layout = EmailTemplate.objects.filter(
                template_type=EmailTemplateType.LAYOUT, is_default_layout=True
            ).first()
            effective_mjml = (
                apply_layout(content, default_layout.content)
                if default_layout is not None
                else content
            )

        try:
            mjml = replace_tokens(effective_mjml, strict_token_validation=False)
            html = mjml2html(mjml)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            PreviewResponseSerializer({"html": html}).data,
            status=status.HTTP_200_OK,
        )


class EmailConfigurationDispatchViewSet(viewsets.ModelViewSet):
    queryset = EmailConfigurationDispatch.objects.select_related(
        "email_configuration_version"
    ).all()
    serializer_class = EmailConfigurationDispatchSerializer
    pagination_class = LimitOffsetPagination
    DEFAULT_LIMIT = 10

    @extend_schema(
        responses={200: EmailConfigurationDispatchSerializer(many=True)},
    )
    @action(detail=False)
    def last_sent(self, request: Request):
        pagination = self.pagination_class()
        queryset = EmailConfigurationDispatch.objects.filter(is_sent=True).order_by(
            "-scheduled_time"
        )
        objects = pagination.paginate_queryset(queryset, request)
        serializer = EmailConfigurationDispatchSerializer(objects, many=True)
        return pagination.get_paginated_response(serializer.data)

    @extend_schema(
        responses={200: EmailConfigurationDispatchSerializer(many=True)},
        description="Returns the list of email config dispatch that will be sent next.",
    )
    @action(detail=False)
    def next_sends(self, request):
        pagination = self.pagination_class()
        queryset = (
            EmailConfigurationDispatch.objects.filter(is_sent=False)
            .exclude(email_configuration_version__status=ReleaseStatus.ARCHIVED)
            .order_by("scheduled_time")
        )
        objects = pagination.paginate_queryset(queryset, request)
        serializer = EmailConfigurationDispatchSerializer(objects, many=True)
        return pagination.get_paginated_response(serializer.data)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(detail=True, methods=["post"], url_path="retryall")
    def retry_all_failed(self, request, pk=None):
        email_configuration_dispatch = self.get_object()
        try:
            count = RetryEmailDispatch.retry_all_failed(email_configuration_dispatch)
            return Response({"count": count}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TriggerListView(viewsets.ViewSet):
    @extend_schema(
        responses={
            200: TriggerDefinitionSerializer,
        },
        description="Get a list of available triggers.",
    )
    def list(self, request):
        serializer = TriggerDefinitionSerializer(
            [
                {
                    "id": trigger.get_id(),
                    "name": trigger.get_display_name(),
                    "field_definitions": trigger.get_field_definitions(),
                }
                for trigger in trigger_registry.values()
            ],
            many=True,
        )
        return Response(serializer.data)


class EmailDispatchViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmailDispatch.objects.filter(next_retry__isnull=True).order_by(
        "-sent_time"
    )
    serializer_class = EmailDispatchSerializer
    pagination_class = LimitOffsetPagination

    @extend_schema(
        responses={200: EmailDispatchWithRetriesSerializer(many=True)},
        parameters=[
            OpenApiParameter(name="dispatch_status", required=False),
            OpenApiParameter(name="config_dispatch_id", required=False),
        ],
    )
    def list(self, request, *args, **kwargs):
        queryset = EmailDispatch.objects.filter(next_retry__isnull=True).order_by(
            "-created_at",
            "-sent_time",
            "-opened_time",
            "recipient",
        )
        config_dispatch_id = request.query_params.get("config_dispatch_id")
        if config_dispatch_id:
            queryset = queryset.filter(
                email_configuration_dispatch__id=config_dispatch_id
            )

        dispatch_status = request.query_params.get("dispatch_status")
        if dispatch_status == EmailDispatch.DispatchStatus.OPENED:
            queryset = queryset.filter(opened_time__isnull=False)
        elif dispatch_status == EmailDispatch.DispatchStatus.ERROR:
            queryset = queryset.filter(error_message__isnull=False)
        elif dispatch_status == EmailDispatch.DispatchStatus.BOUNCED:
            queryset = queryset.filter(bounce_message__isnull=False)
        elif dispatch_status == EmailDispatch.DispatchStatus.SENDING:
            queryset = queryset.filter(
                error_message__isnull=True, sent_time__isnull=True
            )
        elif dispatch_status == EmailDispatch.DispatchStatus.DELIVERED:
            queryset = queryset.filter(dsn_delivered_time__isnull=False)
        elif dispatch_status == EmailDispatch.DispatchStatus.UNKNOWN:
            queryset = queryset.filter(
                opened_time__isnull=True,
                error_message__isnull=True,
                bounce_message__isnull=True,
            )

        pagination = self.pagination_class()
        objects = pagination.paginate_queryset(queryset, request)
        serializer = EmailDispatchWithRetriesSerializer(objects, many=True)
        return pagination.get_paginated_response(serializer.data)

    @extend_schema(responses={200: EmailDispatchSerializer(many=False)})
    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        email_dispatch = get_object_or_404(EmailDispatch, pk=pk)
        try:
            retry_dispatch = RetryEmailDispatch.retry(email_dispatch)
            serialized_retry_dispatch = EmailDispatchSerializer(retry_dispatch)
            return Response(
                data=serialized_retry_dispatch.data, status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={200: GroupedEmailDispatchSerializer(many=True)},
        parameters=[
            OpenApiParameter(name="start_date", required=False, type=datetime.datetime),
            OpenApiParameter(name="end_date", required=False, type=datetime.datetime),
        ],
    )
    @action(detail=False)
    def recipients_with_errors(self, request):
        dispatches = self.get_failed_dispatches_between_dates(request)
        dispatch_count_per_recipient = (
            dispatches.values("recipient")
            .annotate(count=Count("recipient"))
            .order_by("-count")
        )

        pagination = self.pagination_class()
        dispatches = pagination.paginate_queryset(dispatch_count_per_recipient, request)
        serializer = GroupedEmailDispatchSerializer(
            dispatches,
            many=True,
        )
        return pagination.get_paginated_response(serializer.data)

    def get_failed_dispatches_between_dates(self, request):
        dispatches = EmailDispatch.objects.with_error(True)
        start_date = request.query_params.get("start_date", None)
        if start_date:
            dispatches = dispatches.filter(sent_time__gte=start_date)
        end_date = request.query_params.get("end_date", None)
        if end_date:
            dispatches = dispatches.filter(sent_time__lte=end_date)
        return dispatches

    @extend_schema(
        responses={200: EmailDispatchSerializer(many=True)},
        parameters=[
            OpenApiParameter(name="start_date", required=False, type=datetime.datetime),
            OpenApiParameter(name="end_date", required=False, type=datetime.datetime),
            OpenApiParameter(name="recipient", required=True, type=str),
        ],
    )
    @action(detail=False)
    def get_failed_dispatches(self, request):
        dispatches = self.get_failed_dispatches_between_dates(request)
        dispatches = dispatches.filter(recipient=request.query_params.get("recipient"))

        pagination = self.pagination_class()
        objects = pagination.paginate_queryset(dispatches, request)
        serializer = EmailDispatchSerializer(objects, many=True)
        return pagination.get_paginated_response(serializer.data)


class SegmentAndFilterViewSet(viewsets.ViewSet):
    @extend_schema(
        responses={
            200: AvailableSegmentsResponseSerializer,
        },
        description="Get a list of available segments.",
    )
    @action(detail=False, methods=["GET"])
    def available_segments(self, request):
        segments = [
            {
                "id": segment_name,
                "type": SegmentOptionSerializer.TYPE_DYNAMIC,
                "label": segment.label,
                "group": segment.group,
                "description": segment.description,
            }
            for segment_name, segment in get_mail_segment_definitions().items()
        ]

        segments.extend(
            {
                "id": segment.id,
                "type": SegmentOptionSerializer.TYPE_STATIC,
                "label": segment.name,
                "group": "Statische Segmente",
                "description": "",
            }
            for segment in StaticSegment.objects.filter(
                recipients__isnull=False, mailcategory__isnull=True
            ).distinct()
        )

        segments.extend(
            {
                "id": category.id,
                "type": SegmentOptionSerializer.TYPE_CATEGORY,
                "label": category.name,
                "group": "Kategorien",
                "description": "",
            }
            for category in MailCategory.objects.all()
        )

        return Response(
            AvailableSegmentsResponseSerializer({"segments": segments}).data
        )

    @extend_schema(
        request=SegmentDataSerializer,
        responses={
            200: {
                "type": "object",
                "properties": {
                    "count": {"type": "integer"},
                    "recipients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        description="Combine segments and filters and get the result.",
    )
    @action(detail=False, methods=["POST"])
    def combine(self, request):
        serializer = SegmentDataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            combined = resolve_segments(
                dynamic_segment_names_additive=data["dynamic_segment_names_additive"],
                dynamic_segment_names_subtractive=data[
                    "dynamic_segment_names_subtractive"
                ],
                static_segment_ids_additive=data["static_segment_ids_additive"],
                static_segment_ids_subtractive=data["static_segment_ids_subtractive"],
                mail_category_ids_additive=data["mail_category_ids_additive"],
            )
            return Response(
                {
                    "count": len(combined),
                    "recipients": [
                        {"name": f"{r}", "email": r.email} for r in combined
                    ],
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TokensView(viewsets.ViewSet):
    @extend_schema(
        responses={200: {"type": "object"}},
    )
    @action(detail=False, methods=["get"])
    def get_tokens(self, request, *args, **kwargs):
        all_tokens = {}
        for token_type, tokens in token_registry.items():
            all_tokens[token_type] = list(tokens.keys())

        return Response(all_tokens, status=status.HTTP_200_OK)


class TrackingView(viewsets.ViewSet):
    permission_classes = []

    @extend_schema(
        responses={200: None},
    )
    @action(detail=True, methods=["GET"], url_path="track")
    def track(self, request, pk=None, *args, **kwargs):
        try:
            with transaction.atomic():
                try:
                    email_dispatch = EmailDispatch.objects.get(id=pk)
                except EmailDispatch.DoesNotExist:
                    LOG.error(f"EmailDispatch with id {pk} not found")
                    return Response(None, status=status.HTTP_200_OK)

                track_email_opening(email_dispatch)

        except Exception as e:
            LOG.error(f"Error while tracking email opening: {type(e)}: {str(e)}")

        return Response(None, status=status.HTTP_200_OK)


class TransactionalTriggerTokenView(viewsets.ViewSet):
    @extend_schema(
        responses={200: {"type": "object"}},
    )
    @action(detail=False, methods=["get"])
    def get_tokens(self, request, *args, **kwargs):
        trigger_tokens = {}
        for trigger_id, tokens in TransactionalTrigger.trigger_tokens.items():
            trigger_tokens[trigger_id] = {
                TransactionalTrigger.transactional_trigger_registry[trigger_id]: list(
                    tokens.keys()
                )
            }
        return Response(trigger_tokens, status=status.HTTP_200_OK)


class StaticSegmentViewSet(viewsets.ModelViewSet):
    queryset = StaticSegment.objects.all()
    serializer_class = StaticSegmentSerializer


class StaticSegmentRecipientViewSet(viewsets.ModelViewSet):
    queryset = StaticSegmentRecipient.objects.all()
    serializer_class = StaticSegmentRecipientSerializer


class MissingTriggersView(APIView):
    @extend_schema(
        responses={200: MissingTriggerSerializer(many=True)},
    )
    def get(self, request):
        released_versions = list(
            EmailConfigurationVersion.objects.filter(status=ReleaseStatus.RELEASED)
        )
        keys_without_released_version = []
        cache = {}
        for key in TransactionalTrigger.required_triggers.keys():
            if not TransactionalTrigger.is_trigger_required(key=key, cache=cache):
                continue
            if not self.does_trigger_show_in_given_versions(
                trigger_key=key, released_versions=released_versions
            ):
                keys_without_released_version.append(key)

        draft_versions = list(
            EmailConfigurationVersion.objects.filter(status=ReleaseStatus.DRAFT)
        )
        keys_with_draft_version = []
        for key in keys_without_released_version:
            if self.does_trigger_show_in_given_versions(
                trigger_key=key, released_versions=draft_versions
            ):
                keys_with_draft_version.append(key)

        data = [
            {
                "key": key,
                "name": TransactionalTrigger.transactional_trigger_registry[key],
                "draft_version_exists": key in keys_with_draft_version,
            }
            for key in keys_without_released_version
        ]
        return Response(
            MissingTriggerSerializer(data, many=True).data,
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def does_trigger_show_in_given_versions(trigger_key, released_versions):
        for version in released_versions:
            if not version.triggers:
                continue
            for trigger in version.triggers:
                if (
                    trigger["trigger_id"] == TransactionalTrigger.get_id()
                    and trigger.get("trigger_field_values", {}).get("key", None)
                    == trigger_key
                ):
                    return True
        return False


class CreateMissingTriggerMailView(APIView):
    @extend_schema(
        responses={200: str},
        request=CreateMissingTriggerMailSerializer,
    )
    @transaction.atomic
    def post(self, request):
        serializer = CreateMissingTriggerMailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        trigger_key = serializer.validated_data["trigger_key"]
        if (
            TransactionalTrigger.required_trigger_to_default_content_map.get(
                trigger_key, None
            )
            is None
        ):
            raise ValueError(f"No default content available for key {trigger_key}")

        email_configuration = EmailConfiguration.objects.create(
            name=f"Entwurf für wichtige Trigger: {TransactionalTrigger.transactional_trigger_registry[trigger_key]}, "
            + timezone.now().strftime("%d.%m.%Y %H:%M:%S")
        )

        content = serializer.validated_data["empty_mjml"]
        insert_index = content.find("</mj-body>")
        content = (
            content[:insert_index]
            + TransactionalTrigger.required_trigger_to_default_content_map[trigger_key]
            + content[insert_index:]
        )

        EmailConfigurationVersion.objects.create(
            content=content,
            subject="TODO",
            email_configuration=email_configuration,
            status=ReleaseStatus.DRAFT,
            triggers=[
                {
                    "trigger_id": TransactionalTrigger.get_id(),
                    "trigger_field_values": {"key": trigger_key},
                }
            ],
            layout_enabled=EmailTemplate.objects.filter(
                template_type=EmailTemplateType.LAYOUT,
                is_default_layout=True,
            ).exists(),
        )

        return Response("OK", status=status.HTTP_200_OK)


class MailCategoryViewSet(viewsets.ModelViewSet):
    queryset = MailCategory.objects.order_by("name")
    serializer_class = MailCategorySerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = MailCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        static_segment = StaticSegment.objects.create(
            name=f"Mail-Kategorie:{data["name"]}"
        )

        category = MailCategory.objects.create(
            name=data["name"],
            mode=data["mode"],
            available_for_external_recipients=data["available_for_external_recipients"],
            static_segment=static_segment,
        )

        return Response(
            MailCategorySerializer(category).data,
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        instance: MailCategory = self.get_object()
        static_segment = instance.static_segment
        instance.delete()
        static_segment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(xframe_options_exempt, name="dispatch")
class RegisterToMailCategoryView(FormView):
    form_class = RegisterToMailCategoryForm
    template_name = "tapir_mail/external.html"

    def __init__(self):
        super().__init__()
        self.category = None

    def get_category(self):
        if self.category is None:
            self.category = get_object_or_404(
                MailCategory,
                id=self.kwargs["category_id"],
                available_for_external_recipients=True,
            )

        return self.category

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["category_name"] = self.get_category().name
        return context_data

    def get_success_url(self):
        return reverse(
            "confirmation_mail_sent",
            args=[self.get_category().id],
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"category": self.get_category()})
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        email_address = form.cleaned_data["email"]
        first_name = form.cleaned_data["first_name"]

        external_recipient, _ = ExternalRecipient.objects.get_or_create(
            email=email_address, defaults={"first_name": first_name}
        )
        external_recipient_confirmation, _ = (
            ExternalRecipientConfirmation.objects.get_or_create(
                external_recipient=external_recipient, mail_category=self.get_category()
            )
        )
        self.external_recipient_confirmation = external_recipient_confirmation

        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=TransactionalTriggerKeys.MAIL_CATEGORY_REGISTRATION_CONFIRMATION_LINK,
                token_data={
                    "category_name": self.get_category().name,
                    "confirmation_link": settings.SITE_URL
                    + reverse(
                        "user_confirms_registration",
                        args=[external_recipient_confirmation.confirmation_secret],
                    ),
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=email_address, first_name=first_name, last_name=""
                ),
            )
        )

        return response


@method_decorator(xframe_options_exempt, name="get")
class ConfirmationMailSentView(TemplateView):
    template_name = "tapir_mail/confirmation_mail_sent.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["category_name"] = get_object_or_404(
            MailCategory, id=self.kwargs["category_id"]
        ).name
        return context_data


class ConfirmRegistrationToMailCategoryView(TemplateView):
    template_name = "tapir_mail/confirmation_registration_complete.html"

    def get_external_recipient_confirmation(self):
        return get_object_or_404(
            ExternalRecipientConfirmation, confirmation_secret=self.kwargs["secret"]
        )

    @transaction.atomic
    def get(self, request, *args, **kwargs):
        external_recipient_confirmation = self.get_external_recipient_confirmation()
        if external_recipient_confirmation.confirmed_at is not None:
            return super().get(request, *args, **kwargs)

        external_recipient_confirmation.confirmed_at = datetime.datetime.now()
        external_recipient_confirmation.save()

        ExternalRecipientManager.register_external_recipient_to_category(
            mail_category=external_recipient_confirmation.mail_category,
            external_recipient=external_recipient_confirmation.external_recipient,
        )

        external_recipient = external_recipient_confirmation.external_recipient
        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=TransactionalTriggerKeys.MAIL_CATEGORY_REGISTRATION_CONFIRMED,
                token_data={
                    "category_name": external_recipient_confirmation.mail_category.name,
                    "management_link": settings.SITE_URL
                    + reverse(
                        "external_recipient_manager",
                        kwargs={"recipient_secret": external_recipient.secret_key},
                    ),
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=external_recipient.email,
                    first_name=external_recipient.first_name,
                    last_name="",
                ),
            )
        )

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["mail_category_name"] = (
            self.get_external_recipient_confirmation().mail_category.name
        )
        return context_data


class MailUiView(TemplateView):
    template_name = "tapir_mail/ui.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["env_vars"] = {
            "REACT_APP_API_ROOT": f"{settings.SITE_URL}/{MAIL_URL_PREFIX}",
            "REACT_APP_BASENAME": f"/{MAIL_URL_PREFIX}",
        }
        return context_data


class ExternalRecipientManagementView(FormView):
    form_class = ExternalRecipientManagementForm
    template_name = "tapir_mail/management.html"

    def __init__(self):
        super().__init__()
        self.external_recipient = None

    def get_external_recipient(self):
        if self.external_recipient is None:
            self.external_recipient = ExternalRecipient.objects.get(
                secret_key=self.kwargs.get("recipient_secret")
            )

        return self.external_recipient

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs.update({"external_recipient": self.get_external_recipient()})
        return form_kwargs

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["first_name"] = self.get_external_recipient().first_name
        return context_data

    def form_valid(self, form):
        messages.success(self.request, "Änderungen gespeichert")

        external_recipient = self.get_external_recipient()
        external_recipient.first_name = form.cleaned_data["first_name"]
        external_recipient.save()

        at_least_one_enabled = False
        for mail_category in MailCategory.objects.all():
            enabled = form.cleaned_data.get(
                ExternalRecipientManagementForm.build_field_key_for_category(
                    mail_category
                ),
                False,
            )
            if enabled:
                at_least_one_enabled = True
                ExternalRecipientManager.register_external_recipient_to_category(
                    mail_category=mail_category, external_recipient=external_recipient
                )

            else:
                ExternalRecipientManager.remove_external_recipient_from_category(
                    mail_category=mail_category, external_recipient=external_recipient
                )

        if not at_least_one_enabled:
            external_recipient.delete()

        return super().form_valid(form)

    def get_success_url(self):
        recipient_secret = self.kwargs.get("recipient_secret")
        if ExternalRecipient.objects.filter(secret_key=recipient_secret).exists():
            return reverse(
                "external_recipient_manager", args=[self.kwargs.get("recipient_secret")]
            )

        return settings.SITE_URL
