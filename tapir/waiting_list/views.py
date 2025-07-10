from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import permissions, viewsets, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.triggers.transactional_trigger import (
    TransactionalTrigger,
    TransactionalTriggerData,
)

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.core.config import LEGAL_STATUS_COOPERATIVE
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.subscriptions.serializers import OrderConfirmationResponseSerializer
from tapir.subscriptions.services.required_product_types_validator import (
    RequiredProductTypesValidator,
)
from tapir.subscriptions.services.single_subscription_validator import (
    SingleSubscriptionValidator,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.waiting_list.serializers import (
    WaitingListEntryDetailsSerializer,
    WaitingListEntrySerializer,
    WaitingListEntryUpdateSerializer,
    PublicWaitingListEntryNewMemberCreateSerializer,
    PublicWaitingListEntryExistingMemberCreateSerializer,
)
from tapir.waiting_list.services.waiting_list_categories_service import (
    WaitingListCategoriesService,
)
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    WaitingListEntry,
    WaitingListProductWish,
    WaitingListPickupLocationWish,
    Member,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_active_and_future_subscriptions
from tapir.wirgarten.tapirmail import Events
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
        ],
    )
    def get(self, request):
        pagination = self.pagination_class()
        entries = (
            WaitingListEntry.objects.order_by("created_at")
            .prefetch_related(
                "product_wishes__product", "pickup_location_wishes__pickup_location"
            )
            .select_related("member")
        )
        entries = pagination.paginate_queryset(entries, request)

        data = [self.build_entry_data(entry) for entry in entries]
        serializer = WaitingListEntryDetailsSerializer(data, many=True)

        return pagination.get_paginated_response(serializer.data)

    def build_entry_data(self, entry: WaitingListEntry):
        date_of_entry_in_cooperative = None
        current_pickup_location = None
        member_no = None
        current_products = None
        url_to_member_profile = None
        current_subscriptions = None
        if entry.member is not None:
            member_no = entry.member.member_no
            self.fill_entry_with_personal_data(entry)
            date_of_entry_in_cooperative = (
                MembershipCancellationManager.get_coop_entry_date(entry.member)
            )
            pickup_location_id = (
                MemberPickupLocationService.get_member_pickup_location_id(
                    entry.member, reference_date=get_today(cache=self.cache)
                )
            )
            current_pickup_location = TapirCache.get_pickup_location_by_id(
                cache=self.cache,
                pickup_location_id=pickup_location_id,
            )
            current_products = {
                subscription.product
                for subscription in get_active_and_future_subscriptions(
                    cache=self.cache
                )
                .filter(member=entry.member)
                .select_related("product__type")
            }
            url_to_member_profile = reverse(
                "wirgarten:member_detail", args=[entry.member.id]
            )
            current_subscriptions = (
                TapirCache.get_active_and_future_subscriptions_by_member_id(
                    cache=self.cache, reference_date=get_today(cache=self.cache)
                ).get(entry.member.id, [])
            )

        return {
            "id": entry.id,
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
        }

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
            product_wishes.append(
                WaitingListProductWish(
                    waiting_list_entry=waiting_list_entry,
                    product_id=product_id,
                    quantity=validated_data["product_quantities"][index],
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
                PublicWaitingListCreateEntryExistingMemberView.send_confirmation_mail(
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
        ] < MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_order(
            ordered_products_id_to_quantity_map=order, cache=self.cache
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


class PublicWaitingListCreateEntryExistingMemberView(APIView):
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
