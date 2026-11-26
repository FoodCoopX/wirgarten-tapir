from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir.mail.models import (
    EmailConfiguration,
    EmailConfigurationVersion,
    EmailTemplate,
    EmailTemplateType,
    ReleaseStatus,
)
from tapir.mail.permissions import HasEmailManagePermission
from tapir.mail.serializers import (
    TriggerDefinitionSerializer,
    MissingTriggerSerializer,
    CreateMissingTriggerMailSerializer,
)
from tapir.mail.services.token import token_registry
from tapir.mail.services.triggers import trigger_registry
from tapir.mail.triggers.transactional_trigger import TransactionalTrigger


class TriggerListView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]

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


class TokensView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]

    @extend_schema(
        responses={200: {"type": "object"}},
    )
    @action(detail=False, methods=["get"])
    def get_tokens(self, request, *args, **kwargs):
        all_tokens = {}
        for token_type, tokens in token_registry.items():
            all_tokens[token_type] = list(tokens.keys())

        return Response(all_tokens, status=status.HTTP_200_OK)


class TransactionalTriggerTokenView(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]

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


class MissingTriggersView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]

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
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]

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
