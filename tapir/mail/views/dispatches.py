import datetime
import logging
from django.db import transaction
from django.db.models import Count, QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.response import Response
from tapir.mail.models import EmailConfigurationDispatch, EmailDispatch, ReleaseStatus
from tapir.mail.permissions import HasEmailManagePermission
from tapir.mail.serializers import (
    EmailConfigurationDispatchSerializer,
    EmailDispatchSerializer,
    EmailDispatchWithRetriesSerializer,
    GroupedEmailDispatchSerializer,
)
from tapir.mail.services.email_dispatch import RetryEmailDispatch
from tapir.mail.services.tracking import track_email_opening

LOG = logging.getLogger(__name__)


class EmailConfigurationDispatchViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]
    queryset = EmailConfigurationDispatch.objects.select_related(
        "email_configuration_version"
    ).all()
    serializer_class = EmailConfigurationDispatchSerializer
    pagination_class = LimitOffsetPagination
    DEFAULT_LIMIT = 10

    @staticmethod
    def with_serializer_relations(queryset: QuerySet, path_to_dispatch: str = ""):
        # Loads what EmailConfigurationDispatchSerializer reads from relations
        version = f"{path_to_dispatch}email_configuration_version"
        return queryset.select_related(
            f"{version}__email_configuration"
        ).prefetch_related(
            f"{version}__static_segments_additive",
            f"{version}__static_segments_subtractive",
            f"{version}__mail_categories_additive",
        )

    @extend_schema(
        responses={200: EmailConfigurationDispatchSerializer(many=True)},
    )
    @action(detail=False)
    def last_sent(self, request: Request):
        pagination = self.pagination_class()
        queryset = self.with_serializer_relations(
            EmailConfigurationDispatch.objects.filter(is_sent=True).order_by(
                "-scheduled_time"
            )
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
        queryset = self.with_serializer_relations(
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


class EmailDispatchViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated, HasEmailManagePermission]
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
        queryset = EmailConfigurationDispatchViewSet.with_serializer_relations(
            EmailDispatch.objects.filter(next_retry__isnull=True)
            .select_related("previous_retry")
            .order_by(
                "-created_at",
                "-sent_time",
                "-opened_time",
                "recipient",
            ),
            path_to_dispatch="email_configuration_dispatch__",
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
