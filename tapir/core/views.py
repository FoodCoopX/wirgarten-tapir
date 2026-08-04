from typing import Literal, Any

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
    PermissionDenied,
)
from django.core.validators import validate_email
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView, RedirectView
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import status, serializers, permissions
from rest_framework.exceptions import (
    ValidationError as RestValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.models import MailCategory, InternalRecipientCategoryRegistration
from tapir_mail.registries import get_mail_segments
from tapir_mail.serializers import MailCategorySerializer
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.parameter import get_parameter_value
from tapir.core.serializers import (
    MemberMailCategoryRequestSerializer,
    MemberExtraMailDataSerializer,
    MemberExtraEmailCreateRequest,
    MemberExtraEmailUpdateRequest,
    MailingListSerializer,
    MailingListRecipientSerializer,
    MailingListCreateSerializer,
    MailingListSubscribeExternalRecipientRequestSerializer,
    MailingListSubscribeInternalRecipientRequestSerializer,
)
from tapir.core.services.internal_recipient_manager import InternalRecipientManager
from tapir.core.services.mailman.mailing_list_provider import MailingListProvider
from tapir.core.services.mailman.mailing_lists_enabled_checker import (
    MailingListsEnabledChecker,
)
from tapir.core.services.mailman.mailman_request_sender import MailmanRequestSender
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.log.util import freeze_for_log
from tapir.wirgarten.constants import Permission
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
            and member in get_mail_segments()[category.dynamic_segment_name]()
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
    FEATURE_DISABLED_MESSAGE = "Dieses Funktionalität ist ausgeschaltet."

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

        extra_email_address = serializer.validated_data["extra_email"].strip()
        try:
            validate_email(extra_email_address)
        except DjangoValidationError:
            raise RestValidationError("Ungültige Adresse")

        if MemberExtraEmail.objects.filter(
            member=member, email=extra_email_address
        ).exists():
            raise RestValidationError("Diese zusätzliche Adresse existiert bereits")

        member_extra_email = MemberExtraEmail.objects.create(
            member=member,
            email=extra_email_address,
            first_name=serializer.validated_data["first_name"],
            last_name=serializer.validated_data["last_name"],
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

        member_extra_email.delete()

        return Response(True)


class ConfirmMemberExtraEmailApiView(RedirectView):
    permission_classes = []

    @transaction.atomic
    def get_redirect_url(self, *args, **kwargs):
        cache = {}
        if not get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
        ):
            raise PermissionDenied(MemberExtraEmailApiView.FEATURE_DISABLED_MESSAGE)

        secret = kwargs["secret"]
        member_extra_email = get_object_or_404(MemberExtraEmail, secret=secret)

        member_extra_email.confirmed_on = get_now(cache=cache)
        member_extra_email.save()

        MemberExtraEmailConfirmedLogEntry().populate_email(
            email=member_extra_email.email,
            user=member_extra_email.member,
            actor=self.request.user if self.request.user.is_authenticated else None,
        ).save()

        return reverse("core:member_extra_email_confirmed", kwargs={"secret": secret})


class MemberExtraEmailConfirmedView(TemplateView):
    template_name = "core/member_extra_email_confirmed.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        member_extra_email = get_object_or_404(
            MemberExtraEmail, secret=kwargs["secret"]
        )
        context_data["extra_mail_address"] = member_extra_email.email
        context_data["main_mail_address"] = member_extra_email.member.email
        context_data["site_name"] = get_parameter_value(
            ParameterKeys.SITE_NAME, cache={}
        )
        return context_data


class MailingListsBaseView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "core/mailing_lists_base_view.html"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.cache = {}

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        MailmanRequestSender.ensure_instance_domain_exists(cache=self.cache)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["cache"] = self.cache
        return context_data


class MailingListsListView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: MailingListSerializer(many=True)},
    )
    def get(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        cache = {}
        client = MailmanRequestSender.get_client(cache)
        domain = client.get_domain(mail_host=settings.EMAIL_HOST)

        mailing_lists = [
            {
                "name": mailing_list.fqdn_listname,
                "nb_recipients": len(mailing_list.members) + len(mailing_list.requests),
            }
            for mailing_list in domain.lists
        ]
        mailing_lists = sorted(
            mailing_lists, key=lambda mailing_list: mailing_list["name"]
        )
        return Response(
            MailingListSerializer(
                mailing_lists,
                many=True,
            ).data
        )


class MailingListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        request=MailingListCreateSerializer(),
        responses={200: MailingListSerializer()},
    )
    def post(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        create_serializer = MailingListSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)

        cache = {}
        domain = MailmanRequestSender.get_domain(cache)

        list_name: str = create_serializer.validated_data["name"]
        suffix = f"@{settings.EMAIL_HOST}"
        if list_name.endswith(suffix):
            list_name = list_name.replace(suffix, "")
        created_list = domain.create_list(list_name=list_name)

        return Response(
            MailingListSerializer(
                {
                    "name": created_list.fqdn_listname,
                    "nb_recipients": len(created_list.members)
                    + len(created_list.requests),
                }
            ).data
        )


class MailingListDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[OpenApiParameter(name="list_name", type=str, required=True)],
        responses={200: str},
    )
    def delete(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        list_name = request.query_params.get("list_name")
        cache = {}

        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=list_name, cache=cache
        )
        mailing_list.delete()
        return Response("deleted")


class MailingListRecipientListView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[OpenApiParameter(name="list_name", type=str, required=True)],
        responses={200: MailingListRecipientSerializer(many=True)},
    )
    def get(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        list_name = request.query_params.get("list_name")
        cache = {}

        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=list_name, cache=cache
        )
        recipients = [
            {
                "address": recipient.address,
                "user_confirmed": True,
            }
            for recipient in mailing_list.members
        ]
        recipients += [
            {"address": request["email"], "user_confirmed": False}
            for request in mailing_list.requests
        ]

        members_by_email_address = {
            member.email: member for member in Member.objects.all()
        }

        for recipient in recipients:
            member = members_by_email_address.get(recipient["address"], None)
            recipient["link_to_member_profile"] = (
                reverse("wirgarten:member_detail", kwargs={"pk": member.id})
                if member is not None
                else None
            )

        recipients = sorted(recipients, key=lambda recipient: recipient["address"])
        return Response(MailingListRecipientSerializer(recipients, many=True).data)


class MailingListSubscribeExternalRecipientView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        request=MailingListSubscribeExternalRecipientRequestSerializer(),
        responses={200: str},
    )
    def post(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        serializer = MailingListSubscribeExternalRecipientRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        cache = {}

        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=serializer.validated_data["list_name"], cache=cache
        )
        mailing_list.subscribe(
            address=serializer.validated_data["address"],
            invitation=True,
        )

        return Response("OK")


class MailingListSubscribeInternalRecipientView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        request=MailingListSubscribeInternalRecipientRequestSerializer(),
        responses={200: str},
    )
    def post(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        serializer = MailingListSubscribeInternalRecipientRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        cache = {}

        member = get_object_or_404(Member, id=serializer.validated_data["member_id"])
        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=serializer.validated_data["list_name"], cache=cache
        )
        mailing_list.subscribe(
            address=member.email,
            invitation=True,
        )

        return Response("OK")


class MailingListUnsubscribeRecipientView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        request=MailingListSubscribeExternalRecipientRequestSerializer(),
        responses={200: str},
    )
    def post(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        serializer = MailingListSubscribeExternalRecipientRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        cache = {}

        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=serializer.validated_data["list_name"], cache=cache
        )
        address = serializer.validated_data["address"]
        if address in {member.address for member in mailing_list.members}:
            mailing_list.unsubscribe(
                email=serializer.validated_data["address"], pre_confirmed=True
            )
            return Response("OK")

        list_requests = {
            request["email"]: request["token"] for request in mailing_list.requests
        }
        if address in list_requests:
            mailing_list.discard_request(request_id=list_requests[address])
            return Response("OK")

        raise Http404(
            f"Keine passende Empfänger gefunden, Email:{address}, Liste:{serializer.validated_data["list_name"]}"
        )
