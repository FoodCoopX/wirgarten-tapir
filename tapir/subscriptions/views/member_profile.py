from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.bestell_wizard.serializers import (
    BestellWizardCapacityCheckResponseSerializer,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.subscriptions.serializers import (
    UpdateSubscriptionsRequestSerializer,
    OrderConfirmationResponseSerializer,
    MemberProfileCapacityCheckRequestSerializer,
    MemberSubscriptionDataSerializer,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.subscriptions.services.subscription_update_view_change_applier import (
    SubscriptionUpdateViewChangeApplier,
)
from tapir.subscriptions.services.subscription_update_view_validator import (
    SubscriptionUpdateViewValidator,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member, ProductType, GrowingPeriod
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import check_permission_or_self, get_today


class GetMemberSubscriptionDataApiView(APIView):
    @extend_schema(
        parameters=[OpenApiParameter(name="member_id", type=str)],
        responses={200: MemberSubscriptionDataSerializer},
    )
    def get(self, request):
        member_id = request.query_params.get("member_id")
        get_object_or_404(Member, id=member_id)
        check_permission_or_self(member_id, request)

        subscriptions = (
            get_active_and_future_subscriptions()
            .filter(member_id=member_id)
            .select_related("product", "product__type")
        )
        bestell_wizard_url_template = reverse(
            "bestell_wizard:bestell_wizard_product_type",
            args=[member_id, "product_type_id"],
        )

        data = {
            "subscriptions": subscriptions,
            "product_types": ProductType.objects.all(),
            "bestell_wizard_url_template": bestell_wizard_url_template,
        }

        return Response(MemberSubscriptionDataSerializer(data).data)


class UpdateSubscriptionsApiView(APIView):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        request=UpdateSubscriptionsRequestSerializer,
        responses={200: OrderConfirmationResponseSerializer},
    )
    def post(self, request):
        serializer = UpdateSubscriptionsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member_id = serializer.validated_data["member_id"]
        check_permission_or_self(member_id, request)
        member = get_object_or_404(Member, id=member_id)

        growing_period = get_object_or_404(
            GrowingPeriod, id=serializer.validated_data["growing_period_id"]
        )

        contract_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period,
                apply_buffer_time=True,
                cache=self.cache,
            )
        )

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=serializer.validated_data["shopping_cart"], cache=self.cache
        )
        product_type_id = serializer.validated_data["product_type_id"]
        product_type = TapirCache.get_product_type_by_id(
            cache=self.cache, product_type_id=product_type_id
        )
        if product_type is None:
            raise Http404(f"Unknown product type id: {product_type_id}")

        desired_pickup_location_id = serializer.validated_data.get(
            "pickup_location_id", None
        )
        account_owner = serializer.validated_data.get("account_owner", "").strip()
        iban = serializer.validated_data.get("iban", "").strip()
        payment_rhythm = serializer.validated_data.get("payment_rhythm", None)
        sepa_allowed = serializer.validated_data["sepa_allowed"]
        cancellation_policy_read = serializer.validated_data["cancellation_policy_read"]

        try:
            logged_in_user_is_admin = request.user.has_perm(Permission.Accounts.MANAGE)
            SubscriptionUpdateViewValidator.validate_everything(
                sepa_allowed=sepa_allowed,
                cancellation_policy_read=cancellation_policy_read,
                order=order,
                product_type=product_type,
                contract_start_date=contract_start_date,
                member=member,
                logged_in_user_is_admin=logged_in_user_is_admin,
                desired_pickup_location_id=desired_pickup_location_id,
                account_owner=account_owner,
                iban=iban,
                payment_rhythm=payment_rhythm,
                cache=self.cache,
            )
        except ValidationError as error:
            data = {
                "order_confirmed": False,
                "error": error.message,
            }
            return Response(OrderConfirmationResponseSerializer(data).data)

        with transaction.atomic():
            SubscriptionUpdateViewChangeApplier.apply_changes(
                member=member,
                product_type=product_type,
                contract_start_date=contract_start_date,
                actor=request.user,
                desired_pickup_location_id=desired_pickup_location_id,
                order=order,
                payment_rhythm=payment_rhythm,
                account_owner=account_owner,
                iban=iban,
                sepa_allowed=sepa_allowed,
                cache=self.cache,
            )

        data = {
            "order_confirmed": True,
            "error": None,
            "redirect_url": member.get_absolute_url(),
        }
        return Response(OrderConfirmationResponseSerializer(data).data)


class MemberProfileCapacityCheckApiView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        responses={200: BestellWizardCapacityCheckResponseSerializer},
        request=MemberProfileCapacityCheckRequestSerializer,
    )
    def post(self, request):
        serializer = MemberProfileCapacityCheckRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member_id = serializer.validated_data["member_id"]
        check_permission_or_self(member_id, request)
        member = get_object_or_404(Member, id=member_id)

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=serializer.validated_data["shopping_cart"], cache=self.cache
        )

        subscription_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache=self.cache),
                apply_buffer_time=True,
                cache=self.cache,
            )
        )

        ids_of_product_types_over_capacity = GlobalCapacityChecker.get_product_type_ids_without_enough_capacity_for_order(
            order_with_all_product_types=order,
            member_id=member.id,
            subscription_start_date=subscription_start_date,
            cache=self.cache,
        )

        if len(ids_of_product_types_over_capacity) == 0:
            pickup_location = MemberPickupLocationGetter.get_member_pickup_location(
                member=member, reference_date=subscription_start_date, cache=self.cache
            )
            if (
                pickup_location is not None
                and not PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                    pickup_location=pickup_location,
                    order=order,
                    already_registered_member=member,
                    subscription_start=subscription_start_date,
                    cache=self.cache,
                )
            ):
                ids_of_product_types_over_capacity.append(list(order.keys())[0].type_id)

        ids_of_products_over_capacity = []
        for product, quantity in order.items():
            if not ProductCapacityChecker.does_product_have_enough_free_capacity_to_add_order(
                product=product,
                ordered_quantity=quantity,
                member_id=member.id,
                subscription_start_date=subscription_start_date,
                cache=self.cache,
            ):
                ids_of_products_over_capacity.append(product.id)

        response_data = {
            "ids_of_product_types_over_capacity": ids_of_product_types_over_capacity,
            "ids_of_products_over_capacity": ids_of_products_over_capacity,
        }
        return Response(
            BestellWizardCapacityCheckResponseSerializer(response_data).data
        )
