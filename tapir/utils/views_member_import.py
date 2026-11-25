from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import parsers, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.serializers_member_import import (
    MemberImportApplySerializer,
    MemberImportPreviewSerializer,
    MemberImportResultSerializer,
    MemberImportUploadSerializer,
)
from tapir.utils.services.member_import_service import MemberImportService
from tapir.wirgarten.constants import Permission


class MemberImportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "utils/member_import.html"
    extra_context = {"page_title": "Mitglieder importieren"}


class MemberImportPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    parser_classes = [parsers.MultiPartParser]

    @extend_schema(
        request=MemberImportUploadSerializer,
        responses={200: MemberImportPreviewSerializer},
        operation_id="member_import_preview",
        tags=["member import"],
    )
    def post(self, request):
        serializer = MemberImportUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token, result = MemberImportService.preview(
                file=serializer.validated_data["file"], user_id=request.user.pk
            )
        except TapirDataImportException as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(
            MemberImportPreviewSerializer({"token": token, "result": result}).data
        )


class MemberImportApplyView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        request=MemberImportApplySerializer,
        responses={200: MemberImportResultSerializer},
        operation_id="member_import_apply",
        tags=["member import"],
    )
    def post(self, request):
        serializer = MemberImportApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = MemberImportService.apply(
                user_id=request.user.pk, token=serializer.validated_data["token"]
            )
        except TapirDataImportException as error:
            raise ValidationError({"detail": str(error)}) from error
        return Response(MemberImportResultSerializer(result).data)


class MemberImportTemplateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = Permission.Coop.MANAGE

    def get(self, request):
        response = HttpResponse(
            MemberImportService.build_template(), content_type="text/csv; charset=utf-8"
        )
        response["Content-Disposition"] = (
            'attachment; filename="Mitglieder-Vorlage.csv"'
        )
        return response
