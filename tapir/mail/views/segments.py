from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from tapir.accounts.services.email_normaliser import EmailNormaliser
from tapir.mail.models import StaticSegment, StaticSegmentRecipient, MailCategory
from tapir.mail.permissions import HasEmailManagePermission
from tapir.mail.registries import get_mail_segment_definitions
from tapir.mail.serializers import (
    SegmentDataSerializer,
    StaticSegmentSerializer,
    StaticSegmentRecipientSerializer,
    AvailableSegmentsResponseSerializer,
    SegmentOptionSerializer,
)
from tapir.mail.services.segment import resolve_segments


class SegmentAndFilterViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]

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
                cache={},
            )
            return Response(
                {
                    "count": len(combined),
                    "recipients": [
                        {
                            "name": (
                                f"{r.recipient} (zusätzliche Adresse)"
                                if r.is_extra_address
                                else f"{r.recipient}"
                            ),
                            "email": r.email,
                        }
                        for r in combined
                    ],
                },
                status=status.HTTP_200_OK,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StaticSegmentViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]
    queryset = StaticSegment.objects.all()
    serializer_class = StaticSegmentSerializer


class StaticSegmentRecipientViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]
    queryset = StaticSegmentRecipient.objects.all()
    serializer_class = StaticSegmentRecipientSerializer

    def perform_create(self, serializer: StaticSegmentRecipientSerializer):
        serializer.save(**self._normalised_email(serializer))

    def perform_update(self, serializer: StaticSegmentRecipientSerializer):
        serializer.save(**self._normalised_email(serializer))

    @staticmethod
    def _normalised_email(serializer: StaticSegmentRecipientSerializer) -> dict:
        if "email" not in serializer.validated_data:
            return {}
        return {"email": EmailNormaliser.normalise(serializer.validated_data["email"])}
