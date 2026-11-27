import uuid

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import (
    ValidationError as RestValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir.mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.services.email_normaliser import EmailNormaliser
from tapir.configuration.parameter import get_parameter_value
from tapir.core.services.mailman.mailing_list_unsubscriber import (
    MailingListUnsubscriber,
)
from tapir.core.services.member_extra_email_confirmation_validator import (
    MemberExtraEmailConfirmationValidator,
)
from tapir.core.services.member_extra_email_registration_snapshotter import (
    MemberExtraEmailRegistrationSnapshotter,
)
from tapir.core.services.subscription_management_link_sender import (
    SubscriptionManagementLinkSender,
)
from tapir.core.serializers import (
    MemberExtraMailDataSerializer,
    MemberExtraEmailCreateRequest,
    MemberExtraEmailSendManagementLinkRequest,
    MemberExtraEmailUpdateRequest,
)
from tapir.log.util import freeze_for_log
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    MemberExtraEmail,
    MemberExtraEmailCreatedLogEntry,
    MemberExtraEmailDeletedLogEntry,
    MemberExtraEmailConfirmedLogEntry,
    MemberExtraEmailUpdatedLogEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import check_permission_or_self, get_now


class MemberExtraEmailApiView(APIView):
    FEATURE_DISABLED_MESSAGE = "Diese Funktion ist ausgeschaltet."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        responses={200: MemberExtraMailDataSerializer},
        parameters=[
            OpenApiParameter(name="member_id", type=str),
        ],
    )
    @transaction.atomic
    def get(self, request):
        if not get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=self.cache
        ):
            raise RestValidationError(self.FEATURE_DISABLED_MESSAGE)

        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        return Response(
            MemberExtraMailDataSerializer(
                {
                    "extra_mails": MemberExtraEmail.objects.filter(
                        member=member
                    ).order_by("email"),
                    "explanation_text": get_parameter_value(
                        ParameterKeys.EXPLANATION_TEXT_EXTRA_MAIL_ADDRESSES,
                        cache=self.cache,
                    ),
                }
            ).data
        )

    @extend_schema(
        responses={200: bool},
        request=MemberExtraEmailCreateRequest,
    )
    @transaction.atomic
    def post(self, request):
        if not get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=self.cache
        ):
            raise RestValidationError(self.FEATURE_DISABLED_MESSAGE)
        serializer = MemberExtraEmailCreateRequest(data=request.data)
        serializer.is_valid(raise_exception=True)

        member_id = serializer.validated_data["member_id"]
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        extra_email_address = EmailNormaliser.normalise(
            serializer.validated_data["extra_email"]
        )

        if extra_email_address == member.email:
            raise RestValidationError(
                "Diese Adresse ist bereits die Hauptadresse des Mitglieds"
            )

        if MemberExtraEmail.objects.filter(
            member=member, email=extra_email_address
        ).exists():
            raise RestValidationError("Diese zusätzliche Adresse existiert bereits")

        member_extra_email = MemberExtraEmail.objects.create(
            member=member,
            email=extra_email_address,
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
            receives_direct_mails=serializer.validated_data["receives_direct_mails"],
        )

        MemberExtraEmailCreatedLogEntry().populate_email(
            extra_email_object=member_extra_email, user=member, actor=request.user
        ).save()

        confirmation_link = f"{settings.SITE_URL}{reverse('core:member_extra_email_confirm', kwargs={"secret": member_extra_email.secret})}"
        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=Events.EXTRA_MAIL_CONFIRMATION,
                token_data={
                    "confirmation_link": confirmation_link,
                    "main_mail_address": member.email,
                },
                recipient_outside_of_base_queryset=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=extra_email_address,
                    first_name=member.first_name,
                    last_name=member.last_name,
                ),
            ),
        )

        return Response(True)

    @extend_schema(
        responses={200: bool},
        request=MemberExtraEmailUpdateRequest,
    )
    def patch(self, request):
        if not get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=self.cache
        ):
            raise RestValidationError(self.FEATURE_DISABLED_MESSAGE)
        serializer = MemberExtraEmailUpdateRequest(data=request.data)
        serializer.is_valid(raise_exception=True)

        extra_email_id = serializer.validated_data["extra_email_id"]
        extra_email = get_object_or_404(MemberExtraEmail, id=extra_email_id)
        check_permission_or_self(pk=extra_email.member_id, request=request)

        before_changes = freeze_for_log(extra_email)

        extra_email.first_name = serializer.validated_data["first_name"].strip()
        extra_email.last_name = serializer.validated_data["last_name"].strip()
        extra_email.receives_direct_mails = serializer.validated_data[
            "receives_direct_mails"
        ]

        with transaction.atomic():
            extra_email.save()

            MemberExtraEmailUpdatedLogEntry().populate(
                user=extra_email.member,
                actor=request.user,
                old_frozen=before_changes,
                new_model=extra_email,
            ).save()

        return Response(True)

    @extend_schema(
        responses={200: bool},
        parameters=[
            OpenApiParameter(name="extra_email_id", type=str),
        ],
    )
    @transaction.atomic
    def delete(self, request):
        if not get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=self.cache
        ):
            raise RestValidationError(self.FEATURE_DISABLED_MESSAGE)

        extra_email_id = request.query_params.get("extra_email_id")
        member_extra_email = get_object_or_404(MemberExtraEmail, id=extra_email_id)
        check_permission_or_self(pk=member_extra_email.member_id, request=request)

        MemberExtraEmailDeletedLogEntry().populate_email(
            email=member_extra_email.email,
            user=member_extra_email.member,
            actor=request.user,
        ).save()

        if member_extra_email.is_confirmed:
            email = member_extra_email.email
            transaction.on_commit(
                lambda: MailingListUnsubscriber.unsubscribe_if_address_unused(
                    email=email, cache=self.cache
                ),
                robust=True,
            )

        member_extra_email.delete()

        return Response(True)


class MemberExtraEmailSendManagementLinkApiView(APIView):
    @extend_schema(
        responses={200: bool},
        request=MemberExtraEmailSendManagementLinkRequest,
    )
    def post(self, request):
        cache = {}
        if not get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
        ):
            raise RestValidationError(MemberExtraEmailApiView.FEATURE_DISABLED_MESSAGE)
        serializer = MemberExtraEmailSendManagementLinkRequest(data=request.data)
        serializer.is_valid(raise_exception=True)

        extra_email = get_object_or_404(
            MemberExtraEmail, id=serializer.validated_data["extra_email_id"]
        )
        check_permission_or_self(pk=extra_email.member_id, request=request)
        if not extra_email.is_confirmed:
            raise RestValidationError("Diese Adresse ist noch nicht bestätigt")

        SubscriptionManagementLinkSender.send_link(
            address=extra_email.email, cache=cache
        )

        return Response(True)


class ConfirmMemberExtraEmailView(View):
    def get(self, request: HttpRequest, secret: uuid.UUID) -> HttpResponse:
        cache = {}
        member_extra_email = self._get_extra_email(secret=secret, cache=cache)
        if member_extra_email.is_confirmed:
            return redirect("core:member_extra_email_confirmed", secret=secret)

        refusal_page = self._build_refusal_page_if_address_taken(
            request=request, extra_email=member_extra_email, cache=cache
        )
        if refusal_page is not None:
            return refusal_page

        return render(
            request,
            "core/member_extra_email_confirm.html",
            {
                "extra_mail_address": member_extra_email.email,
                "main_mail_address": member_extra_email.member.email,
                "cache": cache,
            },
        )

    @transaction.atomic
    def post(self, request: HttpRequest, secret: uuid.UUID) -> HttpResponse:
        cache = {}
        member_extra_email = self._get_extra_email(secret=secret, cache=cache)
        if member_extra_email.is_confirmed:
            return redirect("core:member_extra_email_confirmed", secret=secret)

        refusal_page = self._build_refusal_page_if_address_taken(
            request=request, extra_email=member_extra_email, cache=cache
        )
        if refusal_page is not None:
            return refusal_page

        member_extra_email.confirmed_on = get_now(cache=cache)
        member_extra_email.save()

        if member_extra_email.receives_direct_mails:
            MemberExtraEmailRegistrationSnapshotter.snapshot(
                extra_email=member_extra_email, cache=cache
            )

        MemberExtraEmailConfirmedLogEntry().populate_email(
            email=member_extra_email.email,
            user=member_extra_email.member,
            actor=request.user if request.user.is_authenticated else None,
        ).save()

        return redirect("core:member_extra_email_confirmed", secret=secret)

    @staticmethod
    def _get_extra_email(secret: uuid.UUID, cache: dict) -> MemberExtraEmail:
        if not get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
        ):
            raise PermissionDenied(MemberExtraEmailApiView.FEATURE_DISABLED_MESSAGE)
        return get_object_or_404(MemberExtraEmail, secret=secret)

    @staticmethod
    def _build_refusal_page_if_address_taken(
        request: HttpRequest, extra_email: MemberExtraEmail, cache: dict
    ) -> HttpResponse | None:
        try:
            MemberExtraEmailConfirmationValidator.validate_address_is_free(
                extra_email=extra_email, cache=cache
            )
        except ValidationError as error:
            return render(
                request,
                "core/member_extra_email_confirmation_refused.html",
                {
                    "extra_mail_address": extra_email.email,
                    "refusal_reason": error.message,
                    "cache": cache,
                },
            )
        return None


class MemberExtraEmailConfirmedView(TemplateView):
    template_name = "core/member_extra_email_confirmed.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        cache = {}
        member_extra_email = get_object_or_404(
            MemberExtraEmail, secret=kwargs["secret"]
        )
        context_data["extra_mail_address"] = member_extra_email.email
        context_data["main_mail_address"] = member_extra_email.member.email
        context_data["site_name"] = get_parameter_value(
            ParameterKeys.SITE_NAME, cache=cache
        )
        context_data["cache"] = cache
        return context_data
