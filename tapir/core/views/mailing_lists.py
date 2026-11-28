import logging
from typing import Any
from urllib.error import HTTPError

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from mailmanclient import MailmanConnectionError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.accounts.services.email_normaliser import EmailNormaliser
from tapir.core.serializers import (
    MailingListAdminSerializer,
    MailingListHeldMessageSerializer,
    MailingListModerateHeldMessageRequestSerializer,
    MailingListRecipientSerializer,
    MailingListCreateSerializer,
    MailingListSubscribeExternalRecipientRequestSerializer,
    MailingListSubscribeInternalRecipientRequestSerializer,
    MemberMailingListDataResponseSerializer,
)
from tapir.core.services.mailman.held_message_serializer_data_builder import (
    HeldMessageSerializerDataBuilder,
)
from tapir.core.services.mailman.mailing_list_join_validator import (
    MailingListJoinValidator,
)
from tapir.core.services.mailman.mailing_list_provider import MailingListProvider
from tapir.core.services.mailman.mailing_list_self_request_preparer import (
    MailingListSelfRequestPreparer,
)
from tapir.core.services.mailman.mailing_list_self_service import (
    MailingListSelfService,
)
from tapir.core.services.mailman.mailing_list_serializer_data_builder import (
    MailingListSerializerDataBuilder,
)
from tapir.core.services.mailman.mailing_list_settings_updater import (
    MailingListSettingsUpdater,
)
from tapir.core.services.mailman.mailing_lists_enabled_checker import (
    MailingListsEnabledChecker,
)
from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    Member,
    MemberExtraEmail,
)
from tapir.wirgarten.utils import check_permission_or_self

LOG = logging.getLogger(__name__)


class MailingListsBaseView(PermissionRequiredMixin, TemplateView):
    permission_required = Permission.Coop.MANAGE
    template_name = "core/mailing_lists_base_view.html"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.cache = {}
        self.connection_with_mailman_failed = False

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        try:
            TapirMailmanClient.ensure_instance_domain_exists(cache=self.cache)
        except MailmanConnectionError as error:
            LOG.exception(error)
            self.connection_with_mailman_failed = True

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["show_connection_error"] = self.connection_with_mailman_failed
        context_data["cache"] = self.cache
        return context_data


class MailingListsListView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: MailingListAdminSerializer(many=True)},
    )
    def get(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        cache = {}
        domain = TapirMailmanClient.get_domain(cache)
        mailing_lists = [
            MailingListSerializerDataBuilder.build_admin_serializer_data(mailing_list)
            for mailing_list in domain.lists
        ]
        mailing_lists = sorted(
            mailing_lists, key=lambda mailing_list: mailing_list["name"]
        )
        return Response(
            MailingListAdminSerializer(
                mailing_lists,
                many=True,
            ).data
        )


class MailingListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        request=MailingListCreateSerializer(),
        responses={200: MailingListAdminSerializer()},
    )
    def post(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        create_serializer = MailingListCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)

        cache = {}
        domain = TapirMailmanClient.get_domain(cache)

        list_name: str = create_serializer.validated_data["name"]
        suffix = f"@{settings.MAILING_LIST_DOMAIN}"
        if list_name.endswith(suffix):
            list_name = list_name.replace(suffix, "")
        created_list = domain.create_list(list_name=list_name)
        MailingListSettingsUpdater.update_settings(
            mailing_list=created_list,
            advertised=create_serializer.validated_data["advertised"],
            description=create_serializer.validated_data["description"],
            moderated=create_serializer.validated_data["moderated"],
        )

        return Response(
            MailingListAdminSerializer(
                MailingListSerializerDataBuilder.build_admin_serializer_data(
                    created_list
                )
            ).data
        )


class MailingListEditView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        request=MailingListCreateSerializer(),
        responses={200: MailingListAdminSerializer()},
    )
    def put(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        serializer = MailingListCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cache = {}
        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=serializer.validated_data["name"], cache=cache
        )
        MailingListSettingsUpdater.update_settings(
            mailing_list=mailing_list,
            advertised=serializer.validated_data["advertised"],
            description=serializer.validated_data["description"],
            moderated=serializer.validated_data["moderated"],
        )
        updated_list = MailingListProvider.get_list_by_name_or_404(
            list_name=serializer.validated_data["name"], cache=cache
        )

        return Response(
            MailingListAdminSerializer(
                MailingListSerializerDataBuilder.build_admin_serializer_data(
                    updated_list
                )
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
                "address": str(recipient.address),
                "user_confirmed": True,
            }
            for recipient in mailing_list.members
        ]
        recipients += [
            {"address": request["email"], "user_confirmed": False}
            for request in mailing_list.requests
        ]

        addresses = [
            EmailNormaliser.normalise(recipient["address"]) for recipient in recipients
        ]
        members_by_extra_address = {
            extra_email.email: extra_email.member
            for extra_email in MemberExtraEmail.objects.filter(
                email__in=addresses, confirmed_on__isnull=False
            ).select_related("member")
        }
        members_by_main_address = {
            member.email: member
            for member in Member.objects.filter(email__in=addresses)
        }

        for recipient in recipients:
            address = EmailNormaliser.normalise(recipient["address"])
            main_member = members_by_main_address.get(address)
            extra_email_member = members_by_extra_address.get(address)
            recipient["extra_email_member"] = (
                {
                    "display_name": extra_email_member.get_display_name(),
                    "email": extra_email_member.email,
                }
                if extra_email_member is not None
                else None
            )
            member = main_member or extra_email_member
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
        address = EmailNormaliser.normalise(serializer.validated_data["address"])
        MailingListJoinValidator.validate_address_can_join(address=address, cache=cache)
        mailing_list.subscribe(address=address, invitation=True)

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
        MailingListJoinValidator.validate_address_can_join(
            address=member.email, cache=cache
        )
        mailing_list.subscribe(address=member.email, invitation=True)

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
        if address in {str(member.address) for member in mailing_list.members}:
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
            f"Kein passender Empfänger gefunden, E-Mail:{address}, Liste:{serializer.validated_data["list_name"]}"
        )


class MailingListHeldMessagesView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        parameters=[OpenApiParameter(name="list_name", type=str, required=True)],
        responses={200: MailingListHeldMessageSerializer(many=True)},
    )
    def get(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        cache = {}
        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=request.query_params.get("list_name"), cache=cache
        )
        mailman_held_messages = mailing_list.held
        senders = {
            EmailNormaliser.normalise(held_message.sender)
            for held_message in mailman_held_messages
        }
        members_by_email = {
            member.email: member for member in Member.objects.filter(email__in=senders)
        }
        held_messages = [
            HeldMessageSerializerDataBuilder.build_serializer_data(
                held_message, members_by_email, cache=cache
            )
            for held_message in mailman_held_messages
        ]
        held_messages = sorted(
            held_messages, key=lambda held_message: held_message["hold_date"]
        )
        return Response(MailingListHeldMessageSerializer(held_messages, many=True).data)


class MailingListModerateHeldMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        request=MailingListModerateHeldMessageRequestSerializer(),
        responses={200: str},
    )
    def post(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        serializer = MailingListModerateHeldMessageRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cache = {}
        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=serializer.validated_data["list_name"], cache=cache
        )
        request_id = serializer.validated_data["request_id"]
        try:
            mailing_list.moderate_message(
                request_id, serializer.validated_data["moderation_action"]
            )
        except HTTPError as error:
            if error.code != status.HTTP_404_NOT_FOUND:
                raise
            raise Http404(
                f"Keine zurückgehaltene E-Mail mit ID {request_id} in Liste {mailing_list.fqdn_listname} gefunden"
            )

        return Response("OK")


class MemberMailingListDataView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter(name="member_id", type=str, required=True)],
        responses={200: MemberMailingListDataResponseSerializer()},
    )
    def get(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        member_id = request.query_params.get("member_id")
        check_permission_or_self(pk=member_id, request=request)
        member = get_object_or_404(Member, id=member_id)

        return Response(
            MemberMailingListDataResponseSerializer(
                MailingListSelfService.build_list_data(
                    email=member.email, include_advertised_lists=True, cache={}
                )
            ).data
        )


class MailingListMemberSelfSubscribeView(APIView):
    @extend_schema(
        request=MailingListSubscribeInternalRecipientRequestSerializer(),
        responses={200: str},
    )
    def post(self, request):
        mailing_list, member = MailingListSelfRequestPreparer.prepare(request)
        MailingListJoinValidator.validate_address_can_join(
            address=member.email, cache={}
        )
        MailingListSelfService.subscribe(email=member.email, mailing_list=mailing_list)
        return Response("OK")


class MailingListMemberSelfUnsubscribeView(APIView):
    @extend_schema(
        request=MailingListSubscribeInternalRecipientRequestSerializer(),
        responses={200: str},
    )
    def post(self, request):
        mailing_list, member = MailingListSelfRequestPreparer.prepare(request)
        MailingListSelfService.unsubscribe(
            email=member.email, mailing_list=mailing_list
        )
        return Response("Unsubscribed")


class MailingListMemberSelfConfirmView(APIView):
    @extend_schema(
        request=MailingListSubscribeInternalRecipientRequestSerializer(),
        responses={200: str},
    )
    def post(self, request):
        mailing_list, member = MailingListSelfRequestPreparer.prepare(request)
        MailingListJoinValidator.validate_address_can_join(
            address=member.email, cache={}
        )
        MailingListSelfService.accept_invitation(
            email=member.email, mailing_list=mailing_list
        )
        return Response("Confirmed")


class MailingListMemberSelfRejectView(APIView):
    @extend_schema(
        request=MailingListSubscribeInternalRecipientRequestSerializer(),
        responses={200: str},
    )
    def post(self, request):
        mailing_list, member = MailingListSelfRequestPreparer.prepare(request)
        MailingListSelfService.reject_invitation(
            email=member.email, mailing_list=mailing_list
        )
        return Response("Invite rejected")
