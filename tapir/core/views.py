from typing import Literal

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import status, serializers
from rest_framework.exceptions import ValidationError as RestValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.models import MailCategory, InternalRecipientCategoryRegistration
from tapir_mail.registries import segment_registry
from tapir_mail.serializers import MailCategorySerializer
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.parameter import get_parameter_value
from tapir.core.serializers import (
    MemberMailCategoryRequestSerializer,
    MemberExtraMailDataSerializer,
)
from tapir.core.services.internal_recipient_manager import InternalRecipientManager
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    MemberExtraEmail,
    MemberExtraEmailCreatedLogEntry,
    MemberExtraEmailDeletedLogEntry,
    MemberExtraEmailConfirmedLogEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import check_permission_or_self, get_now


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


class MemberExtraEmailApiView(APIView):
    @extend_schema(
        responses={200: MemberExtraMailDataSerializer},
        parameters=[
            OpenApiParameter(name="member_id", type=str),
        ],
    )
    @transaction.atomic
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        cache = {}

        return Response(
            MemberExtraMailDataSerializer(
                {
                    "extra_mails": MemberExtraEmail.objects.filter(member=member),
                    "explanation_text": get_parameter_value(
                        ParameterKeys.EXPLANATION_TEXT_EXTRA_MAIL_ADDRESSES, cache=cache
                    ),
                }
            ).data
        )

    @extend_schema(
        responses={200: bool},
        parameters=[
            OpenApiParameter(name="extra_email", type=str),
            OpenApiParameter(name="member_id", type=str),
        ],
    )
    @transaction.atomic
    def post(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        extra_email = request.query_params.get("extra_email").strip()
        try:
            validate_email(extra_email)
        except DjangoValidationError:
            raise RestValidationError("Ungültige Adresse")

        if MemberExtraEmail.objects.filter(member=member, email=extra_email).exists():
            raise RestValidationError("Diese zusätzliche Adresse existiert bereits")

        MemberExtraEmail.objects.create(member=member, email=extra_email)

        MemberExtraEmailCreatedLogEntry().populate_email(
            email=extra_email, user=member, actor=request.user
        ).save()

        confirmation_link = (
            f"{settings.SITE_URL}{reverse('wirgarten:member_extra_email_confirm')}"
        )
        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=Events.EXTRA_MAIL_CONFIRMATION,
                token_data={
                    "confirmation_link": confirmation_link,
                    "main_mail_address": member.email,
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=extra_email,
                    first_name=member.first_name,
                    last_name=member.last_name,
                ),
            ),
        )

        return Response(True)

    @extend_schema(
        responses={200: bool},
        parameters=[
            OpenApiParameter(name="extra_email_id", type=str),
        ],
    )
    @transaction.atomic
    def delete(self, request):
        extra_email_id = request.query_params.get("extra_email_id")
        member_extra_email = get_object_or_404(MemberExtraEmail, id=extra_email_id)
        check_permission_or_self(pk=member_extra_email.member_id, request=request)

        MemberExtraEmailDeletedLogEntry().populate_email(
            email=member_extra_email.email,
            user=member_extra_email.member,
            actor=request.user,
        ).save()

        member_extra_email.delete()

        return Response(True)


class ConfirmMemberExtraEmailApiView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: bool},
        parameters=[
            OpenApiParameter(name="secret", type=str),
        ],
    )
    @transaction.atomic
    def get(self, request):
        secret = request.query_params.get("secret")
        member_extra_email = get_object_or_404(MemberExtraEmail, secret=secret)

        member_extra_email.confirmed_on = get_now(cache={})
        member_extra_email.save()

        MemberExtraEmailConfirmedLogEntry().populate_email(
            email=member_extra_email.email,
            user=member_extra_email.member,
            actor=request.user,
        ).save()

        return Response(True)
