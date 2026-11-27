from abc import ABC, abstractmethod

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from mailmanclient import MailingList
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.core.serializers import (
    SubscriptionManagementCategoriesRequest,
    SubscriptionManagementDataSerializer,
    SubscriptionManagementExternalRequest,
    SubscriptionManagementMailingListRequest,
)
from tapir.core.services.internal_recipient_manager import InternalRecipientManager
from tapir.core.services.mail_category_selection_validator import (
    MailCategorySelectionValidator,
)
from tapir.core.services.mailman.mailing_list_join_validator import (
    MailingListJoinValidator,
)
from tapir.core.services.mailman.mailing_list_provider import MailingListProvider
from tapir.core.services.mailman.mailing_list_self_service import (
    MailingListSelfService,
)
from tapir.core.services.mailman.mailing_list_unsubscriber import (
    MailingListUnsubscriber,
)
from tapir.core.services.mailman.mailing_lists_enabled_checker import (
    MailingListsEnabledChecker,
)
from tapir.core.services.subscription_management_request_resolver import (
    SubscriptionManagementRequestResolver,
)
from tapir.mail.models import ExternalRecipient, StaticSegmentRecipient
from tapir.mail.services.external_recipient_manager import ExternalRecipientManager
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.models import (
    MemberExtraEmail,
    MemberExtraEmailDeletedLogEntry,
    MemberExtraEmailSubscriptionsChangedLogEntry,
)


class SubscriptionManagementDataApiView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: SubscriptionManagementDataSerializer},
        parameters=[OpenApiParameter(name="token", type=str, required=True)],
    )
    def get(self, request: Request) -> Response:
        cache = {}
        address = SubscriptionManagementRequestResolver.get_address(
            token=request.query_params.get("token"), cache=cache
        )

        return Response(
            SubscriptionManagementDataSerializer(
                {
                    "address": address,
                    "extra": self._build_extra_part(address=address, cache=cache),
                    "external": self._build_external_part(address=address),
                    "mailing_lists": (
                        MailingListSelfService.build_list_data(
                            email=address,
                            include_advertised_lists=SubscriptionManagementRequestResolver.can_subscribe_to_lists(
                                address=address, cache=cache
                            ),
                            cache=cache,
                        )
                        if settings.MAILING_LISTS_ENABLED
                        else None
                    ),
                }
            ).data
        )

    @staticmethod
    def _build_extra_part(address: str, cache: dict) -> dict | None:
        if not get_parameter_value(
            key=ParameterKeys.ENABLE_EXTRA_MAIL_ADDRESSES, cache=cache
        ):
            return None

        extra_email = (
            MemberExtraEmail.objects.filter(email=address, confirmed_on__isnull=False)
            .select_related("member")
            .first()
        )
        if extra_email is None:
            return None

        categories = InternalRecipientManager.get_categories_for_member(
            member=extra_email.member
        )
        return {
            "member_first_name": extra_email.member.first_name,
            "receives_direct_mails": extra_email.receives_direct_mails,
            "categories": categories,
            "categories_registered_to": {
                category.id: InternalRecipientManager.is_extra_email_registered_to_mail_category(
                    extra_email=extra_email, mail_category=category
                )
                for category in categories
            },
        }

    @classmethod
    def _build_external_part(cls, address: str) -> dict | None:
        external_recipient = ExternalRecipient.objects.filter(email=address).first()
        if external_recipient is None:
            return None

        categories = SubscriptionManagementRequestResolver.get_external_categories()
        return {
            "first_name": external_recipient.first_name,
            "categories": categories,
            "categories_registered_to": {
                category.id: ExternalRecipientManager.is_email_address_registered_to_category(
                    mail_category=category, email=address
                )
                for category in categories
            },
        }


class SubscriptionManagementExtraCategoriesApiView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: bool}, request=SubscriptionManagementCategoriesRequest
    )
    @transaction.atomic
    def post(self, request: Request) -> Response:
        serializer = SubscriptionManagementCategoriesRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        cache = {}
        address = SubscriptionManagementRequestResolver.get_address(
            token=serializer.validated_data["token"], cache=cache
        )
        extra_email = SubscriptionManagementRequestResolver.get_extra_email(
            address=address, cache=cache
        )

        registrations = MailCategorySelectionValidator.resolve_submitted_registrations(
            available_categories=InternalRecipientManager.get_categories_for_member(
                member=extra_email.member
            ),
            categories_registered_to=serializer.validated_data[
                "categories_registered_to"
            ],
        )
        changes = [
            f"Kategorie {category.name}: {'angemeldet' if is_registered else 'abgemeldet'}"
            for category, is_registered in registrations.items()
            if is_registered
            != InternalRecipientManager.is_extra_email_registered_to_mail_category(
                extra_email=extra_email, mail_category=category
            )
        ]
        InternalRecipientManager.update_extra_email_registrations(
            extra_email=extra_email, is_registered_by_category=registrations
        )
        if changes:
            MemberExtraEmailSubscriptionsChangedLogEntry().populate_changes(
                email=address, changes=changes, user=extra_email.member
            ).save()

        return Response(True)


class SubscriptionManagementExtraApiView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: bool},
        parameters=[OpenApiParameter(name="token", type=str, required=True)],
    )
    @transaction.atomic
    def delete(self, request: Request) -> Response:
        cache = {}
        address = SubscriptionManagementRequestResolver.get_address(
            token=request.query_params.get("token"), cache=cache
        )
        extra_email = SubscriptionManagementRequestResolver.get_extra_email(
            address=address, cache=cache
        )

        MemberExtraEmailDeletedLogEntry().populate_email(
            email=address, user=extra_email.member, actor=None
        ).save()
        extra_email.delete()
        transaction.on_commit(
            lambda: MailingListUnsubscriber.unsubscribe_if_address_unused(
                email=address, cache=cache
            ),
            robust=True,
        )

        return Response(True)


class SubscriptionManagementExternalApiView(APIView):
    permission_classes = []

    @extend_schema(responses={200: bool}, request=SubscriptionManagementExternalRequest)
    @transaction.atomic
    def post(self, request: Request) -> Response:
        serializer = SubscriptionManagementExternalRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        cache = {}
        address = SubscriptionManagementRequestResolver.get_address(
            token=serializer.validated_data["token"], cache=cache
        )
        external_recipient = get_object_or_404(ExternalRecipient, email=address)

        first_name = serializer.validated_data["first_name"]

        external_categories = (
            SubscriptionManagementRequestResolver.get_external_categories()
        )
        registrations = MailCategorySelectionValidator.resolve_submitted_registrations(
            available_categories=external_categories,
            categories_registered_to=serializer.validated_data[
                "categories_registered_to"
            ],
        )

        external_recipient.first_name = first_name
        external_recipient.save()
        StaticSegmentRecipient.objects.filter(
            email=address,
            segment_id__in=[
                category.static_segment_id for category in external_categories
            ],
        ).update(first_name=first_name)

        for category, is_registered in registrations.items():
            if is_registered:
                ExternalRecipientManager.register_external_recipient_to_category(
                    mail_category=category, external_recipient=external_recipient
                )
            else:
                ExternalRecipientManager.remove_external_recipient_from_category(
                    mail_category=category, external_recipient=external_recipient
                )

        return Response(True)

    @extend_schema(
        responses={200: bool},
        parameters=[OpenApiParameter(name="token", type=str, required=True)],
    )
    @transaction.atomic
    def delete(self, request: Request) -> Response:
        cache = {}
        address = SubscriptionManagementRequestResolver.get_address(
            token=request.query_params.get("token"), cache=cache
        )
        external_recipient = get_object_or_404(ExternalRecipient, email=address)

        StaticSegmentRecipient.objects.filter(
            email=address,
            segment_id__in=[
                category.static_segment_id
                for category in SubscriptionManagementRequestResolver.get_external_categories()
            ],
        ).delete()
        external_recipient.delete()
        transaction.on_commit(
            lambda: MailingListUnsubscriber.unsubscribe_if_address_unused(
                email=address, cache=cache
            ),
            robust=True,
        )

        return Response(True)


class SubscriptionManagementMailingListApiView(APIView, ABC):
    permission_classes = []

    ACTION_LABEL: str

    @extend_schema(
        responses={200: bool}, request=SubscriptionManagementMailingListRequest
    )
    def post(self, request: Request) -> Response:
        MailingListsEnabledChecker.check_mailing_lists_enabled()
        serializer = SubscriptionManagementMailingListRequest(data=request.data)
        serializer.is_valid(raise_exception=True)
        cache = {}
        address = SubscriptionManagementRequestResolver.get_address(
            token=serializer.validated_data["token"], cache=cache
        )
        mailing_list = MailingListProvider.get_list_by_name_or_404(
            list_name=serializer.validated_data["list_name"], cache=cache
        )

        self._apply(email=address, mailing_list=mailing_list, cache=cache)
        self._log_if_extra(address=address, mailing_list=mailing_list)

        return Response(True)

    @abstractmethod
    def _apply(self, email: str, mailing_list: MailingList, cache: dict): ...

    def _log_if_extra(self, address: str, mailing_list: MailingList):
        extra_email = (
            MemberExtraEmail.objects.filter(email=address, confirmed_on__isnull=False)
            .select_related("member")
            .first()
        )
        if extra_email is None:
            return

        MemberExtraEmailSubscriptionsChangedLogEntry().populate_changes(
            email=address,
            changes=[f"Liste {mailing_list.fqdn_listname}: {self.ACTION_LABEL}"],
            user=extra_email.member,
        ).save()


class SubscriptionManagementMailingListSubscribeApiView(
    SubscriptionManagementMailingListApiView
):
    ACTION_LABEL = "angemeldet"

    def _apply(self, email: str, mailing_list: MailingList, cache: dict):
        if not SubscriptionManagementRequestResolver.can_subscribe_to_lists(
            address=email, cache=cache
        ):
            raise ValidationError(
                "Diese Adresse kann sich nicht selbst bei einer Liste anmelden"
            )
        MailingListJoinValidator.validate_address_can_join(address=email, cache=cache)
        MailingListSelfService.subscribe(email=email, mailing_list=mailing_list)


class SubscriptionManagementMailingListUnsubscribeApiView(
    SubscriptionManagementMailingListApiView
):
    ACTION_LABEL = "abgemeldet"

    def _apply(self, email: str, mailing_list: MailingList, cache: dict):
        MailingListSelfService.unsubscribe(email=email, mailing_list=mailing_list)


class SubscriptionManagementMailingListAcceptInvitationApiView(
    SubscriptionManagementMailingListApiView
):
    ACTION_LABEL = "Einladung angenommen"

    def _apply(self, email: str, mailing_list: MailingList, cache: dict):
        MailingListJoinValidator.validate_address_can_join(address=email, cache=cache)
        MailingListSelfService.accept_invitation(email=email, mailing_list=mailing_list)


class SubscriptionManagementMailingListRejectInvitationApiView(
    SubscriptionManagementMailingListApiView
):
    ACTION_LABEL = "Einladung abgelehnt"

    def _apply(self, email: str, mailing_list: MailingList, cache: dict):
        MailingListSelfService.reject_invitation(email=email, mailing_list=mailing_list)
