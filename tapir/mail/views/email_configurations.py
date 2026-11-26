import logging
from django.core.cache import cache
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from tapir.mail.models import (
    EmailConfiguration,
    EmailConfigurationDispatch,
    EmailConfigurationVersion,
    EmailTemplate,
    EmailTemplateType,
    ReleaseStatus,
    StaticSegment,
    MailCategory,
)
from tapir.mail.permissions import HasEmailManagePermission
from tapir.mail.serializers import (
    BundledEmailConfigurationSerializer,
    EmailConfigurationSerializer,
    EmailConfigurationVersionSerializer,
    RecipientSerializer,
    PreviewSerializer,
    PreviewResponseSerializer,
)
from tapir.mail.services.email import prepare_email
from tapir.mail.services.layout import apply_layout, render_email_mjml
from tapir.mail.services.mail_content_validator import MailContentValidator
from tapir.mail.services.mjml import mjml2html
from tapir.mail.services.token import replace_tokens
from tapir.mail.services.triggers import Trigger

LOG = logging.getLogger(__name__)


class EmailConfigurationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]
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
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]
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
        email_configuration.description = serializer.validated_data.get(
            "description", None
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
