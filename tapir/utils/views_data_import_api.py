from django.urls import reverse
from drf_spectacular.utils import extend_schema
from rest_framework import parsers, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.utils.exceptions import TapirDataImportException
from tapir.utils.serializers_data_import import (
    ActivationResponseSerializer,
    ApplyRequestSerializer,
    ApplyResponseSerializer,
    DataImportCellEditRequestSerializer,
    ImportTypeSerializer,
    MappingErrorResponseSerializer,
    MappingRequestSerializer,
    ReviewResponseSerializer,
    UploadRequestSerializer,
    UploadResponseSerializer,
)
from tapir.utils.services.data_import_service import IMPORT_TYPES, ActivationMailService
from tapir.utils.services.data_import_wizard_service import DataImportWizardService


class DataImportApiBase(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @staticmethod
    def error(detail, code=status.HTTP_400_BAD_REQUEST):
        return Response({"detail": detail}, status=code)


class DataImportTypesApi(DataImportApiBase):
    @extend_schema(
        responses={200: ImportTypeSerializer(many=True)}, tags=["data import"]
    )
    def get(self, request):
        return Response(
            [
                {
                    "key": key,
                    "name": value.name,
                    "template_url": reverse("utils:data_import_template", args=[key]),
                }
                for key, value in IMPORT_TYPES.items()
            ]
        )


class DataImportUploadApi(DataImportApiBase):
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    @extend_schema(
        request=UploadRequestSerializer,
        responses={200: UploadResponseSerializer},
        tags=["data import"],
    )
    def post(self, request):
        serializer = UploadRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            _, response = DataImportWizardService.upload(**serializer.validated_data)
        except TapirDataImportException as error:
            return self.error(str(error))
        return Response(response)


class DataImportMappingApi(DataImportApiBase):
    @extend_schema(
        request=MappingRequestSerializer,
        responses={200: ReviewResponseSerializer, 400: MappingErrorResponseSerializer},
        tags=["data import"],
    )
    def post(self, request):
        serializer = MappingRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result, error = DataImportWizardService.map(
            token=serializer.validated_data["token"],
            mapping_items=serializer.validated_data["mapping"],
            default_items=serializer.validated_data.get("defaults", []),
            pickup_location_mapping_items=serializer.validated_data.get(
                "pickup_location_mapping", []
            ),
            options=serializer.validated_data.get("options", {}),
            update_existing=serializer.validated_data.get("update_existing"),
        )
        if error:
            return Response(error, status=400)
        return Response(result)


class DataImportApplyApi(DataImportApiBase):
    @extend_schema(
        request=ApplyRequestSerializer,
        responses={200: ApplyResponseSerializer},
        tags=["data import"],
    )
    def post(self, request):
        serializer = ApplyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result, error = DataImportWizardService.apply(**serializer.validated_data)
        if error:
            return Response(error, status=400)
        return Response(result)


class DataImportActivationApi(DataImportApiBase):
    @extend_schema(responses={200: ActivationResponseSerializer}, tags=["data import"])
    def get(self, request):
        return Response(
            {
                "members_without_login": ActivationMailService.get_members_without_login(
                    cache={}
                ).count()
            }
        )

    @extend_schema(
        request=None,
        responses={200: ActivationResponseSerializer},
        tags=["data import"],
    )
    def post(self, request):
        sent, errors = ActivationMailService.send(actor=request.user)
        return Response({"sent": sent, "errors": errors})


class DataImportCellEditApi(DataImportApiBase):
    @extend_schema(
        request=DataImportCellEditRequestSerializer,
        responses={200: ReviewResponseSerializer},
        tags=["data import"],
    )
    def post(self, request):
        serializer = DataImportCellEditRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result, error = DataImportWizardService.edit_cell(**serializer.validated_data)
        if error:
            return Response(error, status=400)
        return Response(result)
