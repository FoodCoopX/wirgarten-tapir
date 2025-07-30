import datetime
import uuid

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet, Subquery, OuterRef
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from rest_framework import permissions, viewsets, status, serializers
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.core.config import LEGAL_STATUS_COOPERATIVE
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.serializers import OrderConfirmationResponseSerializer
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.required_product_types_validator import (
    RequiredProductTypesValidator,
)
from tapir.subscriptions.services.single_subscription_validator import (
    SingleSubscriptionValidator,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.views.bestell_wizard import BestellWizardConfirmOrderApiView
from tapir.utils.services.tapir_cache import TapirCache
from tapir.waiting_list.models import WaitingListChangeConfirmedLogEntry
from tapir.waiting_list.serializers import (
    WaitingListEntryDetailsSerializer,
    WaitingListEntrySerializer,
    WaitingListEntryUpdateSerializer,
    PublicWaitingListEntryNewMemberCreateSerializer,
    PublicWaitingListEntryExistingMemberCreateSerializer,
    PublicConfirmWaitingListEntryRequestSerializer,
)
from tapir.waiting_list.services.waiting_list_categories_service import (
    WaitingListCategoriesService,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    WaitingListEntry,
    WaitingListProductWish,
    WaitingListPickupLocationWish,
    Member,
    PickupLocation,
    CoopShareTransaction,
    Subscription,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import calculate_pickup_location_change_date
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.utils import get_today, get_now, check_permission_or_self


class WaitingListView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "waiting_list/list.html"
    permission_required = Permission.Coop.MANAGE


class WaitingListApiView(APIView):
    serializer_class = WaitingListEntryDetailsSerializer(many=True)
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]
    pagination_class = LimitOffsetPagination

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: WaitingListEntryDetailsSerializer(many=True)},
        parameters=[
            OpenApiParameter(name="limit", type=int, required=True),
            OpenApiParameter(name="offset", type=int, required=True),
            OpenApiParameter(
                name="member_type",
                type=str,
                enum=["all", "new_members", "existing_members"],
                required=True,
            ),
            OpenApiParameter(
                name="entry_type",
                type=str,
                enum=[
                    "any",
                    "must_have_pickup_location_wish",
                    "must_have_product_wish",
                ],
                required=True,
            ),
            OpenApiParameter(name="category", type=str, required=True),
            OpenApiParameter(
                name="current_pickup_location_id", type=str, required=True
            ),
            OpenApiParameter(name="pickup_location_wish", type=str, required=True),
            OpenApiParameter(name="product_wish", type=str, required=True),
            OpenApiParameter(
                name="order_by",
                type=str,
                required=True,
                enum=["created_at", "-created_at", "member_since", "-member_since"],
            ),
        ],
    )
    def get(self, request):
        pagination = self.pagination_class()

        entries = WaitingListEntry.objects.prefetch_related(
            "product_wishes__product", "pickup_location_wishes__pickup_location"
        ).select_related("member")

        filters = [
            "member_type",
            "entry_type",
            "category",
            "current_pickup_location_id",
            "pickup_location_wish",
            "product_wish",
        ]
        for filter in filters:
            parameter = request.query_params.get(filter)
            filter_method = getattr(self, f"filter_by_{filter}")
            entries = filter_method(parameter, entries)

        order_by = request.query_params.get("order_by", "-created_at")
        if "created_at" in order_by:
            entries = entries.order_by(order_by)
        else:
            entries = self.order_by_coop_entry_date(entries, descending="-" in order_by)

        entries = pagination.paginate_queryset(entries, request)

        data = [self.build_entry_data(entry, cache=self.cache) for entry in entries]
        serializer = WaitingListEntryDetailsSerializer(data, many=True)

        return pagination.get_paginated_response(serializer.data)

    @classmethod
    def filter_by_member_type(
        cls, member_type: str, entries: QuerySet[WaitingListEntry]
    ):
        if member_type == "new_members":
            return entries.filter(member__isnull=True)

        if member_type == "existing_members":
            return entries.filter(member__isnull=False)

        return entries

    @classmethod
    def filter_by_entry_type(cls, entry_type: str, entries: QuerySet[WaitingListEntry]):
        if entry_type == "must_have_pickup_location_wish":
            return entries.filter(pickup_location_wishes__isnull=False)

        if entry_type == "must_have_product_wish":
            return entries.filter(product_wishes__isnull=False)

        return entries

    @classmethod
    def filter_by_category(cls, category: str, entries: QuerySet[WaitingListEntry]):
        if category == "none":
            return entries.filter(category__isnull=True)
        if category == "any":
            return entries
        if category:
            return entries.filter(category=category)
        return entries

    def filter_by_current_pickup_location_id(
        self, pickup_location_id: str, entries: QuerySet[WaitingListEntry]
    ):
        if not pickup_location_id:
            return entries

        pickup_location = get_object_or_404(PickupLocation, id=pickup_location_id)
        member_ids = MemberPickupLocationService.get_members_ids_at_pickup_location(
            pickup_location=pickup_location,
            reference_date=get_today(cache=self.cache),
            cache=self.cache,
        )
        return entries.filter(member_id__in=member_ids)

    @classmethod
    def filter_by_pickup_location_wish(
        cls, pickup_location_id: str, entries: QuerySet[WaitingListEntry]
    ):
        if not pickup_location_id:
            return entries
        wishes = WaitingListPickupLocationWish.objects.filter(
            pickup_location_id=pickup_location_id
        )
        return entries.filter(pickup_location_wishes__in=wishes)

    @classmethod
    def filter_by_product_wish(
        cls, product_id: str, entries: QuerySet[WaitingListEntry]
    ):
        if not product_id:
            return entries
        wishes = WaitingListProductWish.objects.filter(product_id=product_id)
        return entries.filter(product_wishes__in=wishes)

    @classmethod
    def order_by_coop_entry_date(
        cls, entries: QuerySet[WaitingListEntry], descending: bool
    ):
        entries = entries.annotate(
            coop_entry_date=Subquery(
                CoopShareTransaction.objects.filter(
                    transaction_type__in=[
                        CoopShareTransaction.CoopShareTransactionType.PURCHASE,
                        CoopShareTransaction.CoopShareTransactionType.TRANSFER_IN,
                    ],
                    member_id=OuterRef("member_id"),
                )
                .order_by("valid_at")
                .values("valid_at")[:1]
            )
        )

        order_by = "coop_entry_date"
        if descending:
            order_by = "-" + order_by
        return entries.order_by(order_by)

    @classmethod
    def build_entry_data(cls, entry: WaitingListEntry, cache: dict):
        date_of_entry_in_cooperative = None
        current_pickup_location = None
        member_no = None
        current_products = None
        url_to_member_profile = None
        current_subscriptions = None
        if entry.member is not None:
            member_no = entry.member.member_no
            cls.fill_entry_with_personal_data(entry)
            date_of_entry_in_cooperative = (
                MembershipCancellationManager.get_coop_entry_date(entry.member)
            )
            pickup_location_id = (
                MemberPickupLocationService.get_member_pickup_location_id(
                    entry.member, reference_date=get_today(cache=cache)
                )
            )
            current_pickup_location = TapirCache.get_pickup_location_by_id(
                cache=cache,
                pickup_location_id=pickup_location_id,
            )
            current_products = {
                subscription.product
                for subscription in get_active_and_future_subscriptions(cache=cache)
                .filter(member=entry.member)
                .select_related("product__type")
            }
            url_to_member_profile = reverse(
                "wirgarten:member_detail", args=[entry.member.id]
            )
            current_subscriptions = (
                TapirCache.get_active_and_future_subscriptions_by_member_id(
                    cache=cache, reference_date=get_today(cache=cache)
                ).get(entry.member.id, [])
            )
            current_subscriptions = cls.remove_renewals(
                subscriptions=current_subscriptions, cache=cache
            )
        link = None
        if settings.DEBUG and entry.confirmation_link_key:
            link = SendWaitingListLinkApiView.build_waiting_list_link(
                entry.id, entry.confirmation_link_key
            )

        return {
            "id": entry.id,
            "link_key": entry.confirmation_link_key,
            "member_no": member_no,
            "url_to_member_profile": url_to_member_profile,
            "waiting_since": entry.created_at,
            "first_name": entry.first_name,
            "last_name": entry.last_name,
            "email": entry.email,
            "phone_number": entry.phone_number,
            "street": entry.street,
            "street_2": entry.street_2,
            "postcode": entry.postcode,
            "city": entry.city,
            "country": entry.country,
            "date_of_entry_in_cooperative": date_of_entry_in_cooperative,
            "current_pickup_location": current_pickup_location,
            "current_products": current_products,
            "pickup_location_wishes": entry.pickup_location_wishes.all(),
            "product_wishes": entry.product_wishes.all(),
            "desired_start_date": entry.desired_start_date,
            "number_of_coop_shares": entry.number_of_coop_shares,
            "comment": entry.comment,
            "category": entry.category,
            "member_already_exists": entry.member is not None,
            "current_subscriptions": current_subscriptions,
            "link_sent_date": (
                entry.link_sent_date
                if entry.confirmation_link_key is not None
                else None
            ),
            "link": link,
        }

    @staticmethod
    def remove_renewals(subscriptions: list[Subscription], cache: dict):
        current_subscriptions = list(
            filter(
                lambda subscription: subscription.start_date <= get_today(cache=cache),
                subscriptions,
            )
        )
        future_subscriptions = list(
            filter(
                lambda subscription: subscription.start_date > get_today(cache=cache),
                subscriptions,
            )
        )

        subscriptions_without_renewals = current_subscriptions.copy()
        for future_subscription in future_subscriptions:
            is_renewal = False
            for current_subscription in current_subscriptions:
                if (
                    current_subscription.product_id == future_subscription.product_id
                    and current_subscription.quantity == future_subscription.quantity
                ):
                    is_renewal = True
                    break
            if not is_renewal:
                subscriptions_without_renewals.append(future_subscription)

        return subscriptions_without_renewals

    @staticmethod
    def fill_entry_with_personal_data(entry: WaitingListEntry):
        personal_data_fields = [
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "street",
            "street_2",
            "postcode",
            "city",
            "country",
        ]
        for field in personal_data_fields:
            setattr(entry, field, getattr(entry.member, field))


class WaitingListGetCountsApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={
            200: inline_serializer(
                name="counts",
                fields={
                    "all": serializers.IntegerField(),
                    "new_members": serializers.IntegerField(),
                    "existing_members": serializers.IntegerField(),
                },
            )
        },
    )
    def get(self, request):
        entries = WaitingListEntry.objects.all()

        return Response(
            {
                "all": entries.count(),
                "new_members": entries.filter(member__isnull=True).count(),
                "existing_members": entries.filter(member__isnull=False).count(),
            }
        )


class WaitingListEntryViewSet(viewsets.ModelViewSet):
    queryset = WaitingListEntry.objects.all()
    serializer_class = WaitingListEntrySerializer
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]


class WaitingListEntryUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: str},
        request=WaitingListEntryUpdateSerializer,
    )
    @transaction.atomic
    def post(self, request):
        serializer = WaitingListEntryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        waiting_list_entry = get_object_or_404(
            WaitingListEntry, pk=serializer.validated_data["id"]
        )
        self.set_personal_data_from_validated_data(
            waiting_list_entry, serializer.validated_data
        )

        waiting_list_entry.desired_start_date = serializer.validated_data.get(
            "desired_start_date", None
        )
        waiting_list_entry.comment = serializer.validated_data["comment"]
        waiting_list_entry.category = serializer.validated_data.get("category", None)
        waiting_list_entry.save()

        waiting_list_entry.product_wishes.all().delete()
        self.create_product_wishes_from_validated_data(
            waiting_list_entry, serializer.validated_data
        )

        waiting_list_entry.pickup_location_wishes.all().delete()
        self.create_pickup_location_wishes_from_validated_data(
            waiting_list_entry, serializer.validated_data
        )

        return Response("OK", status=status.HTTP_200_OK)

    @classmethod
    def set_personal_data_from_validated_data(
        cls, waiting_list_entry: WaitingListEntry, validated_data: dict
    ):
        waiting_list_entry.first_name = validated_data["first_name"]
        waiting_list_entry.last_name = validated_data["last_name"]
        waiting_list_entry.email = validated_data["email"]
        waiting_list_entry.phone_number = validated_data["phone_number"]
        waiting_list_entry.street = validated_data["street"]
        waiting_list_entry.street_2 = validated_data["street_2"]
        waiting_list_entry.postcode = validated_data["postcode"]
        waiting_list_entry.city = validated_data["city"]

    @classmethod
    def create_product_wishes_from_validated_data(
        cls, waiting_list_entry: WaitingListEntry, validated_data: dict
    ):
        product_wishes = []
        for index, product_id in enumerate(validated_data["product_ids"]):
            quantity = validated_data["product_quantities"][index]
            if quantity == 0:
                continue
            product_wishes.append(
                WaitingListProductWish(
                    waiting_list_entry=waiting_list_entry,
                    product_id=product_id,
                    quantity=quantity,
                )
            )
        WaitingListProductWish.objects.bulk_create(product_wishes)

    @classmethod
    def create_pickup_location_wishes_from_validated_data(
        cls, waiting_list_entry: WaitingListEntry, validated_data: dict
    ):
        pickup_location_wishes = []
        for index, pickup_location_id in enumerate(
            validated_data["pickup_location_ids"]
        ):
            pickup_location_wishes.append(
                WaitingListPickupLocationWish(
                    waiting_list_entry=waiting_list_entry,
                    pickup_location_id=pickup_location_id,
                    priority=index + 1,
                )
            )
        WaitingListPickupLocationWish.objects.bulk_create(pickup_location_wishes)


class WaitingListCategoriesView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: list[str]},
    )
    def get(self, request):
        return Response(
            WaitingListCategoriesService.get_categories(cache={}),
            status=status.HTTP_200_OK,
        )


class WaitingListShowsCoopContentView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: bool},
    )
    def get(self, request):
        return Response(
            (
                get_parameter_value(ParameterKeys.ORGANISATION_LEGAL_STATUS)
                == LEGAL_STATUS_COOPERATIVE
            ),
            status=status.HTTP_200_OK,
        )


class PublicWaitingListCreateEntryNewMemberView(APIView):
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        request=PublicWaitingListEntryNewMemberCreateSerializer,
        responses={200: OrderConfirmationResponseSerializer},
    )
    def post(self, request):
        serializer = PublicWaitingListEntryNewMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = {"order_confirmed": True, "error": ""}
        try:
            self.validate(serializer.validated_data)
            with transaction.atomic():
                entry = self.create_entry(serializer.validated_data)
                WaitingListCreateEntryExistingMemberView.send_confirmation_mail(
                    entry=entry,
                    future_member_info=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                        email=serializer.validated_data["email"],
                        first_name=serializer.validated_data["first_name"],
                        last_name=serializer.validated_data["last_name"],
                    ),
                )
        except ValidationError as error:
            data["order_confirmed"] = False
            data["error"] = error.message

        return Response(OrderConfirmationResponseSerializer(data).data)

    def validate(self, validated_data: dict):
        shopping_cart = {}
        for index, product_id in enumerate(validated_data["product_ids"]):
            shopping_cart[product_id] = validated_data["product_quantities"][index]
        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=shopping_cart, cache=self.cache
        )
        if not RequiredProductTypesValidator.does_order_contain_all_required_product_types(
            order=order
        ):
            raise ValidationError("Some required products have not been selected")

        if not SingleSubscriptionValidator.are_single_subscription_products_are_ordered_at_most_once(
            order=order, cache=self.cache
        ):
            raise ValidationError("Single subscription product ordered more than once")

        if validated_data[
            "number_of_coop_shares"
        ] < MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_tapir_order(
            order=order, cache=self.cache
        ):
            raise ValidationError(
                "The given number of coop shares is less than the required minimum."
            )

        if WaitingListEntry.objects.filter(email=validated_data["email"]).exists():
            raise ValidationError(
                "Es gibt schon einen Warteliste-Eintrag mit dieser E-Mail-Adresse"
            )
        if Member.objects.filter(email=validated_data["email"]).exists():
            raise ValidationError(
                "Es gibt schon einen Konto mit dieser E-Mail-Adresse. Wenn du deine Verträge anpassen möchtest, nutzt die Funktionen im Mitgliederbereich."
            )

    def create_entry(self, validated_data: dict):
        waiting_list_entry = WaitingListEntry(
            privacy_consent=get_now(cache=self.cache),
            number_of_coop_shares=validated_data["number_of_coop_shares"],
        )
        WaitingListEntryUpdateView.set_personal_data_from_validated_data(
            waiting_list_entry, validated_data
        )
        waiting_list_entry.save()

        WaitingListEntryUpdateView.create_product_wishes_from_validated_data(
            waiting_list_entry, validated_data
        )
        WaitingListEntryUpdateView.create_pickup_location_wishes_from_validated_data(
            waiting_list_entry, validated_data
        )

        return waiting_list_entry


class WaitingListCreateEntryExistingMemberView(APIView):
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        request=PublicWaitingListEntryExistingMemberCreateSerializer,
        responses={200: OrderConfirmationResponseSerializer},
    )
    def post(self, request):
        serializer = PublicWaitingListEntryExistingMemberCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        check_permission_or_self(serializer.validated_data["member_id"], request)

        data = {"order_confirmed": True, "error": ""}
        try:
            self.validate(serializer.validated_data)
            with transaction.atomic():
                entry = self.create_entry(serializer.validated_data)
                self.send_confirmation_mail(
                    existing_member_id=serializer.validated_data["member_id"],
                    entry=entry,
                )
        except ValidationError as error:
            data["order_confirmed"] = False
            data["error"] = error.message

        return Response(OrderConfirmationResponseSerializer(data).data)

    def validate(self, validated_data: dict):
        shopping_cart = {}
        for index, product_id in enumerate(validated_data["product_ids"]):
            shopping_cart[product_id] = validated_data["product_quantities"][index]
        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=shopping_cart, cache=self.cache
        )
        if not SingleSubscriptionValidator.are_single_subscription_products_are_ordered_at_most_once(
            order=order, cache=self.cache
        ):
            raise ValidationError("Single subscription product ordered more than once")

        if WaitingListEntry.objects.filter(
            member_id=validated_data["member_id"]
        ).exists():
            raise ValidationError(
                "Es gibt schon einen Warteliste-Eintrag für dieses Mitglied."
            )

    def create_entry(self, validated_data: dict):
        waiting_list_entry = WaitingListEntry(
            privacy_consent=get_now(cache=self.cache),
            number_of_coop_shares=0,
        )
        waiting_list_entry.member_id = validated_data["member_id"]
        waiting_list_entry.save()

        WaitingListEntryUpdateView.create_product_wishes_from_validated_data(
            waiting_list_entry, validated_data
        )
        WaitingListEntryUpdateView.create_pickup_location_wishes_from_validated_data(
            waiting_list_entry, validated_data
        )

        return waiting_list_entry

    @staticmethod
    def send_confirmation_mail(
        entry: WaitingListEntry,
        existing_member_id: str | None = None,
        future_member_info: (
            TransactionalTriggerData.RecipientOutsideOfBaseQueryset | None
        ) = None,
    ):
        if (
            existing_member_id is None
            and future_member_info is None
            or existing_member_id is not None
            and future_member_info is not None
        ):
            raise ValueError(
                f"Exactly one of `existing_member_id` or `future_member_info` must be provided. "
                f"existing_member_id:{existing_member_id}, future_member_info:{future_member_info}"
            )

        contract_list = "</li><li>".join(
            [
                f"{product_wish.product.name} x {product_wish.quantity}"
                for product_wish in entry.product_wishes.all().select_related("product")
            ]
        )
        contract_list = f"<ul><li>{contract_list}</li></ul>"

        pickup_location_list = "</li><li>".join(
            [
                f"{pickup_location_wish.pickup_location.name}"
                for pickup_location_wish in entry.pickup_location_wishes.all()
                .select_related("pickup_location")
                .order_by("priority")
            ]
        )
        pickup_location_list = f"<ol><li>{pickup_location_list}</li></ol>"

        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=Events.CONFIRMATION_REGISTRATION_IN_WAITING_LIST,
                recipient_id_in_base_queryset=existing_member_id,
                recipient_outside_of_base_queryset=future_member_info,
                token_data={
                    "contract_list": contract_list,
                    "pickup_location_list": pickup_location_list,
                    "desired_start_date": (
                        entry.desired_start_date.strftime("%d.%m.%Y")
                        if entry.desired_start_date is not None
                        else "so früh wie möglich"
                    ),
                },
            ),
        )


class SendWaitingListLinkApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: str},
        request=inline_serializer(
            name="send_link_serializer",
            fields={
                "entry_id": serializers.CharField(),
            },
        ),
    )
    @transaction.atomic
    def post(self, request):
        entry_id = request.data["entry_id"]
        waiting_list_entry = get_object_or_404(WaitingListEntry, id=entry_id)

        with transaction.atomic():
            if waiting_list_entry.confirmation_link_key is None:
                waiting_list_entry.confirmation_link_key = uuid.uuid4()
            waiting_list_entry.link_sent_date = get_now(cache=self.cache)
            waiting_list_entry.save()

            self.send_mail(waiting_list_entry)

        return Response("OK")

    @staticmethod
    def build_waiting_list_link(entry_id: str, link_key: uuid.UUID) -> str:
        url = reverse("waiting_list:waiting_list_confirm")
        return f"{url}?entry_id={entry_id}&link_key={link_key}"

    @classmethod
    def send_mail(cls, waiting_list_entry: WaitingListEntry):
        recipient_id_in_base_queryset = None
        recipient_outside_of_base_queryset = None
        if waiting_list_entry.member_id is None:
            recipient_outside_of_base_queryset = (
                TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=waiting_list_entry.email,
                    first_name=waiting_list_entry.first_name,
                    last_name=waiting_list_entry.last_name,
                )
            )
        else:
            recipient_id_in_base_queryset = waiting_list_entry.member_id

        TransactionalTrigger.fire_action(
            TransactionalTriggerData(
                key=Events.WAITING_LIST_WISH_CAN_BE_ORDERED,
                token_data={
                    "link": cls.build_waiting_list_link(
                        waiting_list_entry.id,
                        waiting_list_entry.confirmation_link_key,
                    ),
                },
                recipient_id_in_base_queryset=recipient_id_in_base_queryset,
                recipient_outside_of_base_queryset=recipient_outside_of_base_queryset,
            ),
        )


class DisableWaitingListLinkApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, HasCoopManagePermission]

    @extend_schema(
        responses={200: str},
        request=inline_serializer(
            name="disable_link_serializer",
            fields={
                "entry_id": serializers.CharField(),
            },
        ),
    )
    @transaction.atomic
    def post(self, request):
        entry_id = request.data["entry_id"]
        waiting_list_entry = get_object_or_404(WaitingListEntry, id=entry_id)

        waiting_list_entry.confirmation_link_key = None
        waiting_list_entry.link_sent_date = None
        waiting_list_entry.save()

        return Response("OK")


class WaitingListConfirmOrderView(TemplateView):
    template_name = "waiting_list/waiting_list_confirm.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        context_data["entry_id"] = self.request.GET.get("entry_id", None)
        context_data["link_key"] = self.request.GET.get("link_key", None)
        return context_data


class PublicGetWaitingListEntryDetailsApiView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: WaitingListEntryDetailsSerializer},
        parameters=[
            OpenApiParameter(name="entry_id", type=str, required=True),
            OpenApiParameter(name="link_key", type=str, required=True),
        ],
    )
    def get(self, request):
        entry_id = request.query_params.get("entry_id")
        link_key = request.query_params.get("link_key")

        waiting_list_entry = self.get_entry_by_id_and_validate_link_key(
            entry_id, link_key
        )

        data = WaitingListApiView.build_entry_data(waiting_list_entry, cache={})
        serializer = WaitingListEntryDetailsSerializer(data)

        return Response(serializer.data)

    @classmethod
    def get_entry_by_id_and_validate_link_key(
        cls, entry_id: str, link_key: str
    ) -> WaitingListEntry:
        waiting_list_entry = get_object_or_404(WaitingListEntry, id=entry_id)
        try:
            link_key = uuid.UUID(link_key)
        except ValueError:
            raise Http404(f"Unknown entry (id:{entry_id}, key:{link_key})")

        if waiting_list_entry.confirmation_link_key != link_key:
            raise Http404(f"Unknown entry (id:{entry_id}, key:{link_key})")

        return waiting_list_entry


class PublicConfirmWaitingListEntryView(APIView):
    permission_classes = []

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=PublicConfirmWaitingListEntryRequestSerializer,
    )
    def post(self, request):
        serializer = PublicConfirmWaitingListEntryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            waiting_list_entry = self.validate_request_and_get_waiting_list_entry(
                serializer.validated_data
            )
        except ValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        is_new_member = waiting_list_entry.member is None

        with transaction.atomic():
            member = waiting_list_entry.member
            if is_new_member:
                member = self.create_member(
                    waiting_list_entry, serializer.validated_data
                )

            actor = request.user if request.user.is_authenticated else member
            WaitingListChangeConfirmedLogEntry().populate(
                actor=actor, user=member
            ).save()

            subscriptions_existed_before_changes, new_subscriptions = (
                self.apply_changes(
                    waiting_list_entry=waiting_list_entry,
                    actor=actor,
                    member=member,
                )
            )
            waiting_list_entry.delete()

            if len(new_subscriptions) > 0:
                ApplyTapirOrderManager.send_order_confirmation_mail(
                    member=member,
                    subscriptions_existed_before_changes=subscriptions_existed_before_changes,
                    new_subscriptions=new_subscriptions,
                    cache=self.cache,
                )

            if is_new_member:
                BestellWizardConfirmOrderApiView.create_coop_shares(
                    member=member,
                    number_of_shares=serializer.validated_data["number_of_coop_shares"],
                    subscriptions=new_subscriptions,
                    cache=self.cache,
                )

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )

    def validate_request_and_get_waiting_list_entry(self, validated_data: dict):
        waiting_list_entry = PublicGetWaitingListEntryDetailsApiView.get_entry_by_id_and_validate_link_key(
            validated_data["entry_id"], validated_data["link_key"]
        )

        if waiting_list_entry.member is None:
            PersonalDataValidator.validate_personal_data_new_member(
                email=waiting_list_entry.email,
                phone_number=str(waiting_list_entry.phone_number),
                birthdate=validated_data["birthdate"],
                iban=validated_data["iban"],
                cache=self.cache,
            )
            order = TapirOrderBuilder.build_tapir_order_from_waiting_list_entry(
                waiting_list_entry
            )

            min_number_of_shares = MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_tapir_order(
                order, cache=self.cache
            )
            if validated_data["number_of_coop_shares"] < min_number_of_shares:
                raise ValidationError(
                    f"Diese Bestellung erfordert mindestens {min_number_of_shares} Genossenschaftsanteile"
                )

        if waiting_list_entry.product_wishes.exists():
            if not validated_data["sepa_allowed"]:
                raise ValidationError("SEPA-Mandat muss erlaubt sein")

            if not validated_data["contract_accepted"]:
                raise ValidationError("Vertragsgrundsätze müssen akzeptiert sein")

        return waiting_list_entry

    def create_member(self, waiting_list_entry: WaitingListEntry, validated_data: dict):
        now = get_now(cache=self.cache)
        contracts_signed = {
            contract: now
            for contract in ["sepa_consent", "withdrawal_consent", "privacy_consent"]
        }

        return Member.objects.create(
            first_name=waiting_list_entry.first_name,
            last_name=waiting_list_entry.last_name,
            email=waiting_list_entry.email,
            phone_number=waiting_list_entry.phone_number,
            street=waiting_list_entry.street,
            street_2=waiting_list_entry.street_2,
            postcode=waiting_list_entry.postcode,
            city=waiting_list_entry.city,
            country=waiting_list_entry.country,
            birthdate=validated_data["birthdate"],
            account_owner=validated_data["account_owner"],
            iban=validated_data["iban"],
            **contracts_signed,
        )

    def apply_changes(
        self, waiting_list_entry: WaitingListEntry, actor: TapirUser, member: Member
    ):
        contract_start_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=self.cache),
            apply_buffer_time=False,
            cache=self.cache,
        )

        pickup_location_change_valid_from = contract_start_date
        if not waiting_list_entry.product_wishes.exists():
            pickup_location_change_valid_from = calculate_pickup_location_change_date(
                reference_date=get_today(cache=self.cache), cache=self.cache
            )
        self.apply_pickup_location_changes(
            waiting_list_entry=waiting_list_entry,
            valid_from=pickup_location_change_valid_from,
            actor=actor,
            member=member,
        )
        return self.apply_subscription_changes(
            waiting_list_entry=waiting_list_entry,
            contract_start_date=contract_start_date,
            actor=actor,
            member=member,
        )

    def apply_subscription_changes(
        self,
        waiting_list_entry: WaitingListEntry,
        contract_start_date: datetime.date,
        actor: TapirUser,
        member: Member,
    ):
        order = TapirOrderBuilder.build_tapir_order_from_waiting_list_entry(
            waiting_list_entry
        )
        if len(order) == 0:
            return False, []

        return ApplyTapirOrderManager.apply_order_with_several_product_types(
            member=member,
            order=order,
            contract_start_date=contract_start_date,
            actor=actor,
            needs_admin_confirmation=False,
            cache=self.cache,
        )

    def apply_pickup_location_changes(
        self,
        waiting_list_entry: WaitingListEntry,
        valid_from: datetime.date,
        actor: TapirUser,
        member: Member,
    ):
        pickup_location_wish = waiting_list_entry.pickup_location_wishes.order_by(
            "priority"
        ).first()
        if pickup_location_wish is None:
            return

        MemberPickupLocationService.link_member_to_pickup_location(
            pickup_location_wish.pickup_location_id,
            member=member,
            valid_from=valid_from,
            actor=actor,
            cache=self.cache,
        )
