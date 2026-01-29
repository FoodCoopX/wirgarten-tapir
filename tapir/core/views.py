from typing import Literal

from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.models import MailCategory, InternalRecipientCategoryRegistration
from tapir_mail.registries import segment_registry
from tapir_mail.serializers import MailCategorySerializer

from tapir.configuration.parameter import get_parameter_value
from tapir.core.serializers import MemberMailCategoryRequestSerializer
from tapir.core.services.internal_recipient_manager import InternalRecipientManager
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

        mail_categories = [
            category
            for category in mail_categories
            if category.dynamic_segment_name != ""
            and member in segment_registry[category.dynamic_segment_name]()
        ]

        categories_registered_to = {
            category.id: InternalRecipientManager.is_member_registered_to_mail_category(
                mail_category=category, member=member
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

        InternalRecipientCategoryRegistration.objects.filter(
            internal_recipient_id=member.id,
        ).delete()

        for category_id, enabled in serializer.validated_data[
            "categories_registered_to"
        ].items():
            mail_category = get_object_or_404(MailCategory, id=category_id)
            if enabled:
                InternalRecipientCategoryRegistration.objects.create(
                    mail_category=mail_category,
                    internal_recipient_id=member.id,
                    is_registered=True,
                )
            else:
                InternalRecipientCategoryRegistration.objects.create(
                    mail_category=mail_category,
                    internal_recipient_id=member.id,
                    is_registered=False,
                )

        return Response(True)
