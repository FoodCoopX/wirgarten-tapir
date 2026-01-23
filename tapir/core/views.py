from typing import Literal

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.models import MailCategory
from tapir_mail.serializers import MailCategorySerializer
from tapir_mail.service.external_recipient_manager import ExternalRecipientManager

from tapir.configuration.parameter import get_parameter_value
from tapir.core.serializers import MemberMailCategoryRequestSerializer
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import check_permission_or_self


class GetThemeView(APIView):
    permission_classes = ()

    @extend_schema(
        responses={200: Literal["l2g", "biotop", "wirgarten", "mm"]},
    )
    def get(self, request):
        return Response(
            (get_parameter_value(ParameterKeys.ORGANISATION_THEME)),
            status=status.HTTP_200_OK,
        )


class MemberMailCategoryDataApiView(APIView):
    @extend_schema(
        responses={
            200: inline_serializer(
                name="member_mail_category_data",
                fields={
                    "categories": MailCategorySerializer(many=True),
                    "categories_registered_to": serializers.DictField(
                        child=serializers.BooleanField()
                    ),
                },
            )
        },
        parameters=[
            OpenApiParameter("member_id", type=str),
        ],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)

        member = get_object_or_404(Member, id=member_id)
        mail_categories = MailCategory.objects.select_related("static_segment")

        categories_registered_to = {
            category.id: ExternalRecipientManager.is_email_address_registered_to_category(
                mail_category=category, email=member.email
            )
            for category in mail_categories
        }

        return Response(
            {
                "categories": MailCategorySerializer(mail_categories, many=True).data,
                "categories_registered_to": categories_registered_to,
            }
        )

    @extend_schema(
        responses={200: bool},
        request=MemberMailCategoryRequestSerializer,
    )
    @transaction.atomic
    def post(self, request):
        serializer = MemberMailCategoryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member_id = serializer.validated_data["member_id"]
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        for category_id, enabled in serializer.validated_data[
            "categories_registered_to"
        ].items():
            mail_category = get_object_or_404(MailCategory, id=category_id)
            if enabled:
                ExternalRecipientManager.register_static_recipient_to_category(
                    mail_category=mail_category,
                    email=member.email,
                    first_name=member.first_name,
                )
            else:
                ExternalRecipientManager.remove_static_recipient_from_category(
                    mail_category=mail_category, email=member.email
                )

        return Response(True)
