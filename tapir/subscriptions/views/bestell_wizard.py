import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.accounts.models import TapirUser
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.coop_share_purchase_handler import CoopSharePurchaseHandler
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.pickup_locations.services.member_pickup_location_service import (
    MemberPickupLocationService,
)
from tapir.settings import COOP_SHARE_PRICE
from tapir.subscriptions.serializers import (
    BestellWizardConfirmOrderRequestSerializer,
    OrderConfirmationResponseSerializer,
    BestellWizardCapacityCheckRequestSerializer,
    BestellWizardCapacityCheckResponseSerializer,
    BestellWizardBaseDataResponseSerializer,
    BestellWizardDeliveryDatesForOrderRequestSerializer,
    BestellWizardDeliveryDatesForOrderResponseSerializer,
)
from tapir.subscriptions.services.apply_tapir_order_manager import (
    ApplyTapirOrderManager,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.earliest_possible_contract_start_date_calculator import (
    EarliestPossibleContractStartDateCalculator,
)
from tapir.subscriptions.services.global_capacity_checker import (
    GlobalCapacityChecker,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.subscriptions.services.required_product_types_validator import (
    RequiredProductTypesValidator,
)
from tapir.subscriptions.services.solidarity_validator_new import SolidarityValidatorNew
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.services.trial_period_manager import TrialPeriodManager
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    Member,
    Subscription,
    ProductType,
    PickupLocation,
    WaitingListEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import (
    send_order_confirmation,
)
from tapir.wirgarten.utils import (
    get_today,
    get_now,
)


class BestellWizardView(TemplateView):
    template_name = "subscriptions/bestell_wizard.html"


class BestellWizardConfirmOrderApiView(APIView):
    permission_classes = []

    def __init__(self):
        super().__init__()
        self.cache = {}

    @extend_schema(
        responses={200: OrderConfirmationResponseSerializer},
        request=BestellWizardConfirmOrderRequestSerializer,
    )
    def post(self, request):
        serializer = BestellWizardConfirmOrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        contract_start_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=self.cache),
            apply_buffer_time=True,
            cache=self.cache,
        )

        try:
            self.validate_everything(
                validated_data=serializer.validated_data,
                contract_start_date=contract_start_date,
            )
        except ValidationError as error:
            data = {
                "order_confirmed": False,
                "error": error.message,
            }
            return Response(OrderConfirmationResponseSerializer(data).data)

        with transaction.atomic():
            member = self.create_member(
                personal_data=serializer.validated_data["personal_data"]
            )
            subscriptions = self.create_subscriptions(
                validated_data=serializer.validated_data,
                member=member,
                actor=request.user,
                contract_start_date=contract_start_date,
            )
            order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
                serializer.validated_data["shopping_cart"], cache=self.cache
            )
            if OrderValidator.does_order_need_a_pickup_location(
                order=order, cache=self.cache
            ):
                MemberPickupLocationService.link_member_to_pickup_location(
                    serializer.validated_data["pickup_location_id"],
                    member=member,
                    valid_from=contract_start_date,
                    actor=request.user if request.user.is_authenticated else member,
                    cache=self.cache,
                )
            self.create_coop_shares(
                number_of_shares=serializer.validated_data["nb_shares"],
                member=member,
                subscriptions=subscriptions,
                cache=self.cache,
            )
            send_order_confirmation(member, subscriptions, cache=self.cache)

        data = {
            "order_confirmed": True,
            "error": None,
        }
        return Response(OrderConfirmationResponseSerializer(data).data)

    def create_member(self, personal_data):
        now = get_now(cache=self.cache)
        contracts_signed = {
            contract: now
            for contract in ["sepa_consent", "withdrawal_consent", "privacy_consent"]
        }

        return Member.objects.create(**personal_data, **contracts_signed)

    @classmethod
    def create_coop_shares(
        cls,
        number_of_shares: int,
        member: Member,
        subscriptions: list[Subscription],
        cache: dict,
    ):
        min_trial_end_date = datetime.date(year=datetime.MAXYEAR, month=12, day=31)
        for subscription in subscriptions:
            min_trial_end_date = min(
                min_trial_end_date,
                TrialPeriodManager.get_end_of_trial_period(
                    subscription=subscription, cache=cache
                ),
            )

        CoopSharePurchaseHandler.buy_cooperative_shares(
            quantity=number_of_shares,
            member=member,
            shares_valid_at=min_trial_end_date,
            cache=cache,
        )

    def create_subscriptions(
        self,
        validated_data,
        member: Member,
        contract_start_date: datetime.date,
        actor: TapirUser,
    ):
        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=validated_data["shopping_cart"], cache=self.cache
        )
        _, subscriptions = (
            ApplyTapirOrderManager.apply_order_with_several_product_types(
                member=member,
                order=order,
                contract_start_date=contract_start_date,
                actor=actor,
                needs_admin_confirmation=True,
                cache=self.cache,
            )
        )

        return subscriptions

    def validate_everything(
        self, validated_data: dict, contract_start_date: datetime.date
    ):
        PersonalDataValidator.validate_personal_data_new_member(
            email=validated_data["personal_data"]["email"],
            phone_number=validated_data["personal_data"]["phone_number"],
            birthdate=validated_data["personal_data"]["birthdate"],
            iban=validated_data["personal_data"]["iban"],
            cache=self.cache,
        )

        if get_parameter_value(
            ParameterKeys.BESTELLWIZARD_FORCE_WAITING_LIST, cache=self.cache
        ):
            raise ValidationError("Nur Warteliste-Einträge sind erlaubt.")

        if not validated_data["sepa_allowed"]:
            raise ValidationError("SEPA-Mandat muss erlaubt sein")

        if not validated_data["contract_accepted"]:
            raise ValidationError("Vertragsgrundsätze müssen akzeptiert sein")

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=validated_data["shopping_cart"], cache=self.cache
        )

        pickup_location = None
        if OrderValidator.does_order_need_a_pickup_location(
            order=order, cache=self.cache
        ):
            if "pickup_location_id" not in validated_data:
                raise ValidationError(
                    "Diese Bestellung braucht eine Verteilstation, bitte wählt eine aus."
                )
            pickup_location = get_object_or_404(
                PickupLocation, id=validated_data["pickup_location_id"]
            )

        OrderValidator.validate_order_general(
            order=order,
            contract_start_date=contract_start_date,
            cache=self.cache,
            member=None,
            pickup_location=pickup_location,
        )

        if not RequiredProductTypesValidator.does_order_contain_all_required_product_types(
            order=order
        ):
            raise ValidationError("Manche Pflichtprodukte fehlen in der Bestellung")

        if not SolidarityValidatorNew.is_the_ordered_solidarity_allowed(
            ordered_solidarity_factor=0,  # TODO
            order=order,
            start_date=contract_start_date,
            cache=self.cache,
        ):
            raise ValidationError("Solidarbeitrag ungültig oder zu niedrig")

        student_status_enabled = validated_data["student_status_enabled"]
        if student_status_enabled and not get_parameter_value(
            ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES, cache=self.cache
        ):
            raise ValidationError("Studenten-Status ist nicht erlaubt")

        nb_ordered_coop_shares = validated_data["nb_shares"]
        if student_status_enabled:
            if nb_ordered_coop_shares > 0:
                raise ValidationError(
                    "Studenten-Status aktiviert, es sollen keine Genossenschaftsanteilen bestellt werden."
                )
        else:
            if not validated_data["statute_accepted"]:
                raise ValidationError("Die Satzung muss akzeptiert werden.")

            minimum_number_of_shares = MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_tapir_order(
                order, cache=self.cache
            )
            if nb_ordered_coop_shares < minimum_number_of_shares:
                raise ValidationError(
                    f"Genossenschaftsanteile bestellt: {nb_ordered_coop_shares}, minimum: {minimum_number_of_shares}."
                )


class BestellWizardCapacityCheckApiView(APIView):
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        responses={200: BestellWizardCapacityCheckResponseSerializer},
        request=BestellWizardCapacityCheckRequestSerializer,
    )
    def post(self, request):
        serializer = BestellWizardCapacityCheckRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

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
            member_id=None,
            subscription_start_date=subscription_start_date,
            cache=self.cache,
        )

        ids_of_products_over_capacity = []
        for product, quantity in order.items():
            if not ProductCapacityChecker.does_product_have_enough_free_capacity_to_add_order(
                product=product,
                ordered_quantity=quantity,
                member_id=None,
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


class BestellWizardBaseDataApiView(APIView):
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        responses={200: BestellWizardBaseDataResponseSerializer},
    )
    def get(self, request):
        response_data = {
            "price_of_a_share": COOP_SHARE_PRICE,
            "theme": get_parameter_value(
                ParameterKeys.ORGANISATION_THEME, cache=self.cache
            ),
            "allow_investing_membership": get_parameter_value(
                ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES,
                cache=self.cache,
            ),
            "product_types": ProductType.objects.all(),
            "force_waiting_list": get_parameter_value(
                ParameterKeys.BESTELLWIZARD_FORCE_WAITING_LIST, cache=self.cache
            ),
            "intro_enabled": get_parameter_value(
                ParameterKeys.BESTELLWIZARD_SHOW_INTRO, cache=self.cache
            ),
            "student_status_allowed": get_parameter_value(
                ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
                cache=self.cache,
            ),
        }

        return Response(BestellWizardBaseDataResponseSerializer(response_data).data)


class BestellWizardDeliveryDatesForOrderApiView(APIView):
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        responses={200: BestellWizardDeliveryDatesForOrderResponseSerializer},
        request=BestellWizardDeliveryDatesForOrderRequestSerializer,
    )
    def post(self, request):
        serializer = BestellWizardDeliveryDatesForOrderRequestSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=serializer.validated_data["shopping_cart"], cache=self.cache
        )
        product_type_ids = {product.type_id for product in order.keys()}
        pickup_location_id = serializer.validated_data["pickup_location_id"]
        pickup_location = TapirCache.get_pickup_location_by_id(
            cache=self.cache,
            pickup_location_id=pickup_location_id,
        )
        if pickup_location is None:
            raise Http404(f"Unknown pickup location")

        reference_date = get_today(cache=self.cache)
        waiting_list_entry_id = serializer.validated_data.get(
            "waiting_list_entry_id", None
        )
        if waiting_list_entry_id is not None:
            reference_date = get_object_or_404(
                WaitingListEntry, id=waiting_list_entry_id
            ).desired_start_date

        contract_start_date = EarliestPossibleContractStartDateCalculator.get_earliest_possible_contract_start_date(
            reference_date=reference_date,
            pickup_location_id=pickup_location_id,
            cache=self.cache,
        )
        response_data = {
            "product_type_id_to_next_delivery_date_map": {
                product_type_id: DeliveryDateCalculator.get_next_delivery_date_for_delivery_cycle(
                    reference_date=contract_start_date,
                    pickup_location_id=pickup_location_id,
                    delivery_cycle=TapirCache.get_product_type_by_id(
                        cache=self.cache, product_type_id=product_type_id
                    ).delivery_cycle,
                    cache=self.cache,
                )
                for product_type_id in product_type_ids
            },
        }

        return Response(
            BestellWizardDeliveryDatesForOrderResponseSerializer(response_data).data
        )


class PublicBestellWizardIsEmailAddressValidApiView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: bool},
        parameters=[OpenApiParameter(name="email", type=str)],
    )
    def get(self, request):
        email = request.query_params.get("email")

        try:
            PersonalDataValidator.validate_email_address_not_in_use(
                email=email, cache={}
            )
        except ValidationError:
            return Response(False)

        return Response(True)
