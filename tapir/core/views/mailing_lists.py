from typing import Any

from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpRequest, HttpResponse
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from mailmanclient import MailmanConnectionError, MailingList
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.core.serializers import (
    MailingListSerializer,
    MailingListRecipientSerializer,
    MailingListCreateSerializer,
    MailingListSubscribeExternalRecipientRequestSerializer,
    MailingListSubscribeInternalRecipientRequestSerializer,
    MemberMailingListDataResponseSerializer,
)
from tapir.core.services.mailman.mailing_list_provider import MailingListProvider
from tapir.core.services.mailman.mailing_list_serializer_data_builder import (
    MailingListSerializerDataBuilder,
)
from tapir.core.services.mailman.mailing_lists_enabled_checker import (
    MailingListsEnabledChecker,
)
from tapir.core.services.mailman.tapir_mailman_client import TapirMailmanClient
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    Member,
)
from tapir.wirgarten.utils import check_permission_or_self


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
        except MailmanConnectionError:
            self.connection_with_mailman_failed = True

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context_data = super().get_context_data(**kwargs)
        context_data["show_connection_error"] = self.connection_with_mailman_failed
        return context_data


class MailingListsListView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: MailingListSerializer(many=True)},
    )
    def get(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        cache = {}
        domain = TapirMailmanClient.get_domain(cache)
        mailing_lists = [
            MailingListSerializerDataBuilder.build_serializer_data(mailing_list)
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

        create_serializer = MailingListCreateSerializer(data=request.data)
        create_serializer.is_valid(raise_exception=True)

        cache = {}
        domain = TapirMailmanClient.get_domain(cache)

        list_name: str = create_serializer.validated_data["name"]
        suffix = f"@{settings.EMAIL_HOST}"
        if list_name.endswith(suffix):
            list_name = list_name.replace(suffix, "")
        created_list = domain.create_list(list_name=list_name)
        created_list.settings["advertised"] = create_serializer.validated_data[
            "advertised"
        ]
        created_list.settings["description"] = create_serializer.validated_data[
            "description"
        ]
        created_list.settings.save()

        return Response(
            MailingListSerializer(
                MailingListSerializerDataBuilder.build_serializer_data(created_list)
            ).data
        )


class MailingListEditView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        request=MailingListCreateSerializer(),
        responses={200: MailingListSerializer()},
    )
    def put(self, request):
        MailingListsEnabledChecker.check_mailing_lists_enabled()

        serializer = MailingListCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cache = {}
        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=serializer.validated_data["name"], cache=cache
        )
        mailing_list.settings["advertised"] = serializer.validated_data["advertised"]
        mailing_list.settings["description"] = serializer.validated_data["description"]
        mailing_list.settings.save()

        return Response(
            MailingListSerializer(
                MailingListSerializerDataBuilder.build_serializer_data(mailing_list)
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
        cache = {}

        domain = TapirMailmanClient.get_domain(cache=cache)
        advertised_lists = [
            mailing_list
            for mailing_list in domain.lists
            if mailing_list.settings["advertised"]
        ]
        available_lists = [
            mailing_list.fqdn_listname for mailing_list in advertised_lists
        ]

        subscribed_lists = [
            mailing_list.fqdn_listname
            for mailing_list in advertised_lists
            if self.is_member_subscribed_to_list(
                email=member.email, mailing_list=mailing_list
            )
        ]
        waiting_for_confirmation_lists = [
            mailing_list.fqdn_listname
            for mailing_list in advertised_lists
            if self.is_member_waiting_for_confirmation(
                email=member.email, mailing_list=mailing_list
            )
        ]

        return Response(
            MemberMailingListDataResponseSerializer(
                {
                    "available_lists": available_lists,
                    "subscribed_lists": subscribed_lists,
                    "waiting_for_confirmation_lists": waiting_for_confirmation_lists,
                }
            ).data
        )

    @classmethod
    def is_member_subscribed_to_list(cls, email: str, mailing_list: MailingList):
        return any(member.address == email for member in mailing_list.members)

    @classmethod
    def is_member_waiting_for_confirmation(cls, email: str, mailing_list: MailingList):
        return any(request["email"] == email for request in mailing_list.requests)
