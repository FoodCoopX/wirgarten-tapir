import uuid

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet, Subquery, OuterRef
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

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.membership_cancellation_manager import (
    MembershipCancellationManager,
)
from tapir.core.config import LEGAL_STATUS_COOPERATIVE
from tapir.generic_exports.permissions import HasCoopManagePermission
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.serializers import OrderConfirmationResponseSerializer
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.waiting_list.serializers import (
    WaitingListEntryDetailsSerializer,
    WaitingListEntrySerializer,
    WaitingListEntryUpdateSerializer,
    PublicWaitingListEntryNewMemberCreateSerializer,
    PublicWaitingListEntryExistingMemberCreateSerializer,
    PublicConfirmWaitingListEntryRequestSerializer,
    OptionalWaitingListEntryDetailsSerializer,
    PublicWaitingListEntryDetailsSerializer,
)
from tapir.waiting_list.services.waiting_list_categories_service import (
    WaitingListCategoriesService,
)
from tapir.waiting_list.services.waiting_list_entry_confirmation_applier import (
    WaitingListEntryConfirmationApplier,
)
from tapir.waiting_list.services.waiting_list_entry_confirmation_email_sender import (
    WaitingListEntryConfirmationEmailSender,
)
from tapir.waiting_list.services.waiting_list_entry_confirmation_validator import (
    WaitingListEntryConfirmationValidator,
)
from tapir.waiting_list.services.waiting_list_entry_creator import (
    WaitingListEntryCreator,
)
from tapir.waiting_list.services.waiting_list_entry_validator import (
    WaitingListEntryValidator,
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
                name="can_be_fulfilled",
                type=str,
                enum=["any", "fulfillable", "not_fulfillable"],
                required=True,
            ),
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
            "product_wishes__product",
            "pickup_location_wishes__pickup_location",
        ).select_related(
            "member",
        )

        filters = [
            "member_type",
            "entry_type",
            "category",
            "current_pickup_location_id",
            "pickup_location_wish",
            "product_wish",
            "can_be_fulfilled",
        ]
        for filter_name in filters:
            parameter = request.query_params.get(filter_name)
            filter_method = getattr(self, f"filter_by_{filter_name}")
            entries = filter_method(parameter, entries)

        order_by = request.query_params.get("order_by", "-created_at")
        if "created_at" in order_by:
            entries = entries.order_by(order_by)
        else:
            entries = self.order_by_coop_entry_date(entries, descending="-" in order_by)

        entries = entries.distinct()

        entries = pagination.paginate_queryset(entries, request)

        data = [self.build_entry_data(entry, cache=self.cache) for entry in entries]
        serializer = WaitingListEntryDetailsSerializer(data, many=True)

        return pagination.get_paginated_response(serializer.data)

    @classmethod
    def filter_by_member_type(
        cls, member_type: str, entries: QuerySet[WaitingListEntry]
    ):
        member_ids_with_at_least_one_transaction = (
            CoopShareTransaction.objects.values_list("member_id", flat=True).distinct()
        )
        if member_type == "new_members":
            return entries.exclude(
                member_id__in=member_ids_with_at_least_one_transaction
            )

        if member_type == "existing_members":
            return entries.filter(
                member_id__in=member_ids_with_at_least_one_transaction
            )

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
        member_ids = MemberPickupLocationGetter.get_members_ids_at_pickup_location(
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
    def filter_by_can_be_fulfilled(
        cls, value: str, entries: QuerySet[WaitingListEntry]
    ):
        if not value or value == "any":
            return entries

        cache = {}
        filtered_entries = []
        for entry in entries:
            can_be_fulfilled = cls.check_if_entry_can_be_fulfilled(
                entry=entry, cache=cache
            )
            if value == "fulfillable" and can_be_fulfilled:
                filtered_entries.append(entry.id)
            elif value == "not_fulfillable" and not can_be_fulfilled:
                filtered_entries.append(entry.id)

        return entries.filter(id__in=filtered_entries)

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
        birthdate = None
        account_owner = None
        iban = None
        payment_rhythm = None
        if entry.member is not None:
            member_no = entry.member.member_no
            cls.fill_entry_with_personal_data(entry)
            date_of_entry_in_cooperative = (
                MembershipCancellationManager.get_coop_entry_date(entry.member)
            )
            pickup_location_id = (
                MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    entry.member.id, reference_date=get_today(cache=cache), cache=cache
                )
            )
            current_pickup_location = TapirCache.get_pickup_location_by_id(
                cache=cache,
                pickup_location_id=pickup_location_id,
            )

            current_subscriptions = (
                TapirCache.get_active_and_future_subscriptions_by_member_id(
                    cache=cache, reference_date=get_today(cache=cache)
                ).get(entry.member.id, [])
            )

            current_products = {
                TapirCache.get_product_by_id(
                    cache=cache, product_id=subscription.product_id
                )
                for subscription in current_subscriptions
            }
            url_to_member_profile = reverse(
                "wirgarten:member_detail", args=[entry.member.id]
            )

            current_subscriptions = cls.remove_renewals(
                subscriptions=current_subscriptions, cache=cache
            )

            birthdate = entry.member.birthdate
            account_owner = entry.member.account_owner
            iban = entry.member.iban
            payment_rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                member=entry.member, reference_date=get_today(cache=cache), cache=cache
            )
        link = None
        if settings.DEBUG and entry.confirmation_link_key:
            link = SendWaitingListLinkApiView.build_waiting_list_link(
                entry.id, entry.confirmation_link_key
            )

        can_be_fulfilled = cls.check_if_entry_can_be_fulfilled(entry=entry, cache=cache)

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
            "birthdate": birthdate,
            "account_owner": account_owner,
            "iban": iban,
            "payment_rhythm": payment_rhythm,
            "can_be_fulfilled": can_be_fulfilled,
        }

    @classmethod
    def check_if_entry_can_be_fulfilled(cls, entry: WaitingListEntry, cache: dict):
        pickup_location_wishes = entry.pickup_location_wishes.all()

        if not pickup_location_wishes or not entry.product_wishes.all():
            return False

        order: TapirOrder = TapirOrderBuilder.build_tapir_order_from_waiting_list_entry(
            entry
        )

        reference_date = (
            entry.desired_start_date
            if entry.desired_start_date
            else get_today(cache=cache)
        )
        subscription_start = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=reference_date,
            apply_buffer_time=False,
            cache=cache,
        )

        product_type_ids_without_enough_capacity = GlobalCapacityChecker.get_product_type_ids_without_enough_capacity_for_order(
            order_with_all_product_types=order,
            member_id=entry.member_id if entry.member else None,
            subscription_start_date=subscription_start,
            cache=cache,
            check_waiting_list_entries=False,
        )

        if product_type_ids_without_enough_capacity:
            return False

        for pickup_location_wish in pickup_location_wishes:
            has_capacity = PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                pickup_location=pickup_location_wish.pickup_location,
                order=order,
                already_registered_member=entry.member,
                subscription_start=subscription_start,
                cache=cache,
                check_waiting_list_entries=False,
            )
            if has_capacity:
                return True

        return False

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
        WaitingListEntryCreator.set_personal_data_from_validated_data(
            waiting_list_entry, serializer.validated_data
        )

        waiting_list_entry.desired_start_date = serializer.validated_data.get(
            "desired_start_date", None
        )
        waiting_list_entry.comment = serializer.validated_data["comment"]
        waiting_list_entry.category = serializer.validated_data.get("category", None)
        waiting_list_entry.save()

        waiting_list_entry.product_wishes.all().delete()
        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            serializer.validated_data["shopping_cart"], cache=self.cache
        )
        WaitingListEntryCreator.create_product_wishes(
            order=order, entry=waiting_list_entry
        )

        waiting_list_entry.pickup_location_wishes.all().delete()
        WaitingListEntryCreator.create_pickup_location_wishes(
            pickup_location_ids_in_priority_order=serializer.validated_data[
                "pickup_location_ids"
            ],
            entry=waiting_list_entry,
        )

        return Response("OK", status=status.HTTP_200_OK)


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


class PublicWaitingListCreateEntryPotentialMemberView(APIView):
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

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=serializer.validated_data["shopping_cart"],
            cache=self.cache,
        )
        try:
            WaitingListEntryValidator.validate_creation_of_waiting_list_entry_for_a_potential_member(
                order=order,
                number_of_coop_shares=serializer.validated_data[
                    "number_of_coop_shares"
                ],
                email=serializer.validated_data["email"],
                cache=self.cache,
            )
        except ValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        with transaction.atomic():
            entry = WaitingListEntryCreator.create_entry_potential_member(
                order=order,
                pickup_location_ids_in_priority_order=serializer.validated_data[
                    "pickup_location_ids"
                ],
                number_of_coop_shares=serializer.validated_data[
                    "number_of_coop_shares"
                ],
                personal_data=serializer.validated_data,
                cache=self.cache,
            )
            WaitingListEntryConfirmationEmailSender.send_confirmation_mail(
                entry=entry,
                potential_member_info=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                    email=serializer.validated_data["email"],
                    first_name=serializer.validated_data["first_name"],
                    last_name=serializer.validated_data["last_name"],
                ),
            )

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": ""}
            ).data
        )


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

        member_id = serializer.validated_data["member_id"]
        check_permission_or_self(member_id, request)
        member = get_object_or_404(Member, id=member_id)

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=serializer.validated_data["shopping_cart"],
            cache=self.cache,
        )

        try:
            WaitingListEntryValidator.validate_creation_of_waiting_list_entry_for_an_existing_member(
                member_id=member_id,
                order=order,
                cache=self.cache,
            )
        except ValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        with transaction.atomic():
            entry = WaitingListEntryCreator.create_entry_existing_member(
                order=order,
                pickup_location_ids_in_priority_order=serializer.validated_data[
                    "pickup_location_ids"
                ],
                member=member,
                growing_period_id=TapirCache.get_growing_period_at_date(
                    reference_date=get_today(cache=self.cache), cache=self.cache
                ).id,
                cache=self.cache,
            )
            WaitingListEntryConfirmationEmailSender.send_confirmation_mail(
                existing_member_id=member_id,
                entry=entry,
            )

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": ""}
            ).data
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
        responses={200: PublicWaitingListEntryDetailsSerializer},
        parameters=[
            OpenApiParameter(name="entry_id", type=str, required=True),
            OpenApiParameter(name="link_key", type=str, required=True),
        ],
    )
    def get(self, request):
        entry_id = request.query_params.get("entry_id")
        link_key = request.query_params.get("link_key")

        waiting_list_entry = (
            WaitingListEntryConfirmationValidator.get_entry_by_id_and_validate_link_key(
                entry_id, link_key
            )
        )

        data = self.build_public_entry_data(waiting_list_entry, cache={})
        serializer = PublicWaitingListEntryDetailsSerializer(data)

        return Response(serializer.data)

    @classmethod
    def build_public_entry_data(cls, entry: WaitingListEntry, cache: dict):
        birthdate = None
        account_owner = None
        iban = None
        payment_rhythm = None
        if entry.member is not None:
            WaitingListApiView.fill_entry_with_personal_data(entry)

            birthdate = entry.member.birthdate
            account_owner = entry.member.account_owner
            iban = entry.member.iban
            payment_rhythm = MemberPaymentRhythmService.get_member_payment_rhythm(
                member=entry.member, reference_date=get_today(cache=cache), cache=cache
            )

        return {
            "entry_id": entry.id,
            "link_key": entry.confirmation_link_key,
            "first_name": entry.first_name,
            "last_name": entry.last_name,
            "email": entry.email,
            "phone_number": entry.phone_number,
            "street": entry.street,
            "street_2": entry.street_2,
            "postcode": entry.postcode,
            "city": entry.city,
            "country": entry.country,
            "pickup_location_wishes": PickupLocation.objects.filter(
                id__in=entry.pickup_location_wishes.values_list(
                    "pickup_location", flat=True
                )
            ),
            "product_wishes": entry.product_wishes.all(),
            "desired_start_date": entry.desired_start_date,
            "number_of_coop_shares": entry.number_of_coop_shares,
            "comment": entry.comment,
            "category": entry.category,
            "member_already_exists": entry.member is not None,
            "birthdate": birthdate,
            "account_owner": account_owner,
            "iban": iban,
            "payment_rhythm": payment_rhythm,
        }


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
            waiting_list_entry = WaitingListEntryConfirmationValidator.validate_request_and_get_waiting_list_entry(
                serializer.validated_data, cache=self.cache
            )
        except ValidationError as error:
            return Response(
                OrderConfirmationResponseSerializer(
                    {"order_confirmed": False, "error": error.message}
                ).data
            )

        WaitingListEntryConfirmationApplier.apply_changes(
            waiting_list_entry=waiting_list_entry,
            validated_data=serializer.validated_data,
            request=request,
            cache=self.cache,
        )

        return Response(
            OrderConfirmationResponseSerializer(
                {"order_confirmed": True, "error": None}
            ).data
        )


class GetMemberWaitingListEntryDetailsApiView(APIView):
    @extend_schema(
        responses={200: OptionalWaitingListEntryDetailsSerializer},
        parameters=[
            OpenApiParameter(name="member_id", type=str, required=True),
        ],
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        check_permission_or_self(member_id, request)

        waiting_list_entry = WaitingListEntry.objects.filter(
            member_id=member_id
        ).first()

        entry_data = None
        if waiting_list_entry is not None:
            entry_data = WaitingListApiView.build_entry_data(
                waiting_list_entry, cache={}
            )
        serializer = OptionalWaitingListEntryDetailsSerializer({"entry": entry_data})

        return Response(serializer.data)
