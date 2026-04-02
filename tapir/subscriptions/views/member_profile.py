import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from localflavor.generic.validators import IBANValidator
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.accounts.models import TapirUser
from tapir.bestell_wizard.serializers import (
    BestellWizardCapacityCheckResponseSerializer,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.payments.services.member_credit_creator import MemberCreditCreator
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
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
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.global_capacity_checker import GlobalCapacityChecker
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import Member, PickupLocation, ProductType, GrowingPeriod
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import check_permission_or_self, get_today, get_now


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
        try:
            logged_in_user_is_admin = request.user.has_perm(Permission.Accounts.MANAGE)
            self.validate_everything(
                validated_data=serializer.validated_data,
                contract_start_date=contract_start_date,
                member=member,
                logged_in_user_is_admin=logged_in_user_is_admin,
            )
        except ValidationError as error:
            data = {
                "order_confirmed": False,
                "error": error.message,
            }
            return Response(OrderConfirmationResponseSerializer(data).data)

        with transaction.atomic():
            self.apply_changes(
                member=member,
                product_type=TapirCache.get_product_type_by_id(
                    cache=self.cache,
                    product_type_id=serializer.validated_data["product_type_id"],
                ),
                contract_start_date=contract_start_date,
                validated_data=serializer.validated_data,
                actor=request.user,
            )

        data = {
            "order_confirmed": True,
            "error": None,
            "redirect_url": member.get_absolute_url(),
        }
        return Response(OrderConfirmationResponseSerializer(data).data)

    def validate_everything(
        self,
        validated_data: dict,
        contract_start_date: datetime.date,
        member: Member,
        logged_in_user_is_admin: bool,
    ):
        if not validated_data["sepa_allowed"]:
            raise ValidationError("Das SEPA-Mandat muss ermächtigt sein.")

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=validated_data["shopping_cart"], cache=self.cache
        )
        product_type_id = validated_data["product_type_id"]
        product_type = TapirCache.get_product_type_by_id(
            cache=self.cache, product_type_id=product_type_id
        )
        if product_type is None:
            raise Http404(f"Unknown product type id: {product_type_id}")

        self.validate_all_products_belong_to_product_type(
            order=order, product_type_id=product_type_id
        )

        pickup_location = self.validate_pickup_location(
            order=order,
            validated_data=validated_data,
            contract_start_date=contract_start_date,
            member=member,
        )

        OrderValidator.validate_order_general(
            order=order,
            pickup_location=pickup_location,
            contract_start_date=contract_start_date,
            cache=self.cache,
            member=member,
        )

        OrderValidator.validate_cannot_reduce_size(
            logged_in_user_is_admin=logged_in_user_is_admin,
            contract_start_date=contract_start_date,
            member=member,
            order_for_a_single_product_type=order,
            product_type=product_type,
            cache=self.cache,
        )

        OrderValidator.validate_at_least_one_change(
            member=member,
            contract_start_date=contract_start_date,
            cache=self.cache,
            product_type=product_type,
            order=order,
        )

        self.validate_additional_product_can_be_ordered_without_base_product_subscription(
            product_type=product_type,
            member=member,
            contract_start_date=contract_start_date,
        )

        self.validate_banking_data(member=member, validated_data=validated_data)

    def validate_banking_data(
        self,
        member: Member,
        validated_data: dict,
    ):
        if MemberNeedsBankingDataChecker.does_member_need_banking_data(member):
            IBANValidator()(validated_data.get("iban", "").strip())

            if validated_data.get("account_owner", "").strip() == "":
                raise ValidationError("Das Feld 'Kontoinhaber*in' muss ausgefüllt sein")

        need_payment_rhythm = (
            TapirCache.get_member_payment_rhythm_object(
                member=member,
                reference_date=get_today(cache=self.cache),
                cache=self.cache,
            )
            is None
        )

        payment_rhythm = validated_data.get("payment_rhythm", None)
        if need_payment_rhythm and payment_rhythm is None:
            raise ValidationError("Das Zahlungsintervall fehlt")

        if payment_rhythm is None:
            return

        if not MemberPaymentRhythmService.is_payment_rhythm_allowed(
            validated_data["payment_rhythm"], cache=self.cache
        ):
            raise ValidationError(
                f"Diese Zahlungsintervall {validated_data["payment_rhythm"]} is nicht erlaubt, erlaubt sind: {MemberPaymentRhythmService.get_allowed_rhythms(cache=self.cache)}"
            )

    def validate_pickup_location(
        self,
        order: TapirOrder,
        member: Member,
        contract_start_date: datetime.date,
        validated_data: dict,
    ):
        if not OrderValidator.does_order_need_a_pickup_location(
            order=order, cache=self.cache
        ):
            return None

        current_pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=contract_start_date
            )
        )
        desired_pickup_location_id = validated_data.get("pickup_location_id", None)
        if (
            current_pickup_location_id is not None
            and desired_pickup_location_id is not None
            and current_pickup_location_id != desired_pickup_location_id
        ):
            raise ValidationError("Du hast schon eine Verteilstation")

        pickup_location_id = None
        if current_pickup_location_id is not None:
            pickup_location_id = current_pickup_location_id
        if desired_pickup_location_id is not None:
            pickup_location_id = desired_pickup_location_id
        if pickup_location_id is None:
            raise ValidationError("Bitte wähle einen Abholort aus!")

        return PickupLocation.objects.get(id=pickup_location_id)

    def validate_all_products_belong_to_product_type(
        self, order: TapirOrder, product_type_id
    ):
        for product in order.keys():
            product = TapirCache.get_product_by_id(
                cache=self.cache, product_id=product.id
            )
            if product.type_id != product_type_id:
                raise ValidationError(
                    f"Product '{product.name}' does not belong to product type with id{product_type_id}"
                )

    def validate_additional_product_can_be_ordered_without_base_product_subscription(
        self,
        product_type: ProductType,
        member: Member,
        contract_start_date: datetime.date,
    ):
        if get_parameter_value(
            ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            cache=self.cache,
        ):
            return

        base_product_type = BaseProductTypeService.get_base_product_type(
            cache=self.cache
        )
        if product_type == base_product_type:
            return

        has_subscription_to_base_product_type = (
            get_active_and_future_subscriptions(reference_date=contract_start_date)
            .filter(
                member__id=member.id,
                product__type__id=base_product_type.id,
            )
            .exists()
        )
        if has_subscription_to_base_product_type:
            return

        raise ValidationError(
            "Um Anteile von diese zusätzliche Produkte zu bestellen, "
            "musst du Anteile von der Basis-Produkt an der gleiche Vertragsperiode haben."
        )

    def apply_changes(
        self,
        member: Member,
        product_type: ProductType,
        contract_start_date: datetime.date,
        validated_data: dict,
        actor: TapirUser,
    ):
        if validated_data.get(
            "pickup_location_id", None
        ) != MemberPickupLocationGetter.get_member_pickup_location_id(
            member=member, reference_date=contract_start_date
        ):
            MemberPickupLocationSetter.link_member_to_pickup_location(
                member=member,
                valid_from=contract_start_date,
                pickup_location_id=validated_data["pickup_location_id"],
                actor=actor,
                cache=self.cache,
            )

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=validated_data["shopping_cart"], cache=self.cache
        )
        subscriptions_existed_before_changes, new_subscriptions = (
            ApplyTapirOrderManager.apply_order_single_product_type(
                member=member,
                order=order,
                contract_start_date=contract_start_date,
                product_type=product_type,
                actor=actor,
                needs_admin_confirmation=True,
                cache=self.cache,
            )
        )

        ApplyTapirOrderManager.send_order_confirmation_mail(
            subscriptions_existed_before_changes=subscriptions_existed_before_changes,
            member=member,
            new_subscriptions=new_subscriptions,
            cache=self.cache,
            from_waiting_list=False,
            solidarity_contribution=None,
        )

        self.change_payment_rhythm_if_necessary(
            validated_data=validated_data, member=member, actor=actor
        )

        MemberCreditCreator.create_member_credit_if_necessary(
            member=member,
            actor=actor,
            product_type_id_or_soli=product_type.id,
            reference_date=contract_start_date,
            comment="Produkt-Anteil vom Admin durch dem Mitgliederbereich reduziert",
            cache=self.cache,
        )

        iban = validated_data.get("iban", "")
        if iban.strip() != "":
            member.iban = iban

        account_owner = validated_data.get("account_owner", "")
        if account_owner.strip() != "":
            member.account_owner = account_owner

        if validated_data["sepa_allowed"]:
            member.sepa_consent = get_now(cache=self.cache)

        member.save()

    def change_payment_rhythm_if_necessary(
        self, validated_data: dict, member: Member, actor: TapirUser
    ):
        payment_rhythm = validated_data.get("payment_rhythm", None)
        if payment_rhythm is None:
            return

        rhythm_valid_from = (
            MemberPaymentRhythmService.get_date_of_next_payment_rhythm_change(
                member=member,
                reference_date=get_today(cache=self.cache),
                cache=self.cache,
            )
        )
        if (
            MemberPaymentRhythmService.get_member_payment_rhythm(
                member=member, reference_date=rhythm_valid_from, cache=self.cache
            )
            == payment_rhythm
        ):
            return

        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=member,
            actor=actor,
            rhythm=validated_data["payment_rhythm"],
            valid_from=MemberPaymentRhythmService.get_date_of_next_payment_rhythm_change(
                member=member,
                reference_date=get_today(cache=self.cache),
                cache=self.cache,
            ),
            cache=self.cache,
        )


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
