import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
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
from tapir.subscriptions.services.earliest_possible_contract_start_date_calculator import (
    EarliestPossibleContractStartDateCalculator,
)
from tapir.subscriptions.services.global_capacity_checker import (
    GlobalCapacityChecker,
)
from tapir.subscriptions.services.notice_period_manager import NoticePeriodManager
from tapir.subscriptions.services.order_validator import OrderValidator
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
    MemberPickupLocation,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.member import (
    get_next_contract_start_date,
    get_or_create_mandate_ref,
    send_order_confirmation,
    buy_cooperative_shares,
)
from tapir.wirgarten.service.products import (
    get_current_growing_period,
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

        contract_start_date = get_next_contract_start_date(cache=self.cache)

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
                contract_start_date=contract_start_date,
            )
            order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
                serializer.validated_data["shopping_cart"], cache=self.cache
            )
            if OrderValidator.does_order_need_a_pickup_location(
                order=order, cache=self.cache
            ):
                self.link_member_to_pickup_location(
                    serializer.validated_data["pickup_location_id"],
                    member=member,
                    contract_start_date=contract_start_date,
                )
            self.create_coop_shares(
                number_of_shares=serializer.validated_data["nb_shares"],
                member=member,
                subscriptions=subscriptions,
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

    @staticmethod
    def link_member_to_pickup_location(
        pickup_location_id, member: Member, contract_start_date: datetime.date
    ):
        MemberPickupLocation.objects.create(
            member_id=member.id,
            pickup_location_id=pickup_location_id,
            valid_from=contract_start_date,
        )

    def create_coop_shares(
        self, number_of_shares: int, member: Member, subscriptions: list[Subscription]
    ):
        min_trial_end_date = datetime.date(year=datetime.MAXYEAR, month=12, day=31)
        for subscription in subscriptions:
            min_trial_end_date = min(
                min_trial_end_date,
                TrialPeriodManager.get_end_of_trial_period(
                    subscription=subscription, cache=self.cache
                ),
            )

        buy_cooperative_shares(
            quantity=number_of_shares,
            member=member,
            start_date=min_trial_end_date,
            cache=self.cache,
        )

    def create_subscriptions(
        self, validated_data, member: Member, contract_start_date: datetime.date
    ):
        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=validated_data["shopping_cart"], cache=self.cache
        )
        growing_period = get_current_growing_period(
            reference_date=contract_start_date, cache=self.cache
        )
        mandate_ref = get_or_create_mandate_ref(member.id, cache=self.cache)
        now = get_now(cache=self.cache)

        subscriptions = []
        for product, quantity in order.items():
            if quantity == 0:
                continue
            product_type = TapirCache.get_product_type_by_id(
                cache=self.cache, product_type_id=product.type_id
            )
            notice_period_duration = None
            if get_parameter_value(
                ParameterKeys.SUBSCRIPTION_AUTOMATIC_RENEWAL, cache=self.cache
            ):
                notice_period_duration = NoticePeriodManager.get_notice_period_duration(
                    product_type=product_type,
                    growing_period=growing_period,
                    cache=self.cache,
                )

            end_date = None
            if product_type.subscriptions_have_end_dates:
                end_date = growing_period.end_date

            subscriptions.append(
                Subscription(
                    member_id=member.id,
                    product=product,
                    quantity=quantity,
                    period=growing_period,
                    start_date=contract_start_date,
                    end_date=end_date,
                    mandate_ref=mandate_ref,
                    consent_ts=now if product_type.contract_link else None,
                    withdrawal_consent_ts=now,
                    trial_disabled=not get_parameter_value(
                        ParameterKeys.TRIAL_PERIOD_ENABLED, cache=self.cache
                    ),
                    trial_end_date_override=None,
                    notice_period_duration=notice_period_duration,
                )
            )

        subscriptions = Subscription.objects.bulk_create(subscriptions)
        TapirCache.clear_category(cache=self.cache, category="subscriptions")

        return subscriptions

    def validate_everything(
        self, validated_data: dict, contract_start_date: datetime.date
    ):
        PersonalDataValidator.validate_personal_data_new_member(
            personal_data=validated_data["personal_data"], cache=self.cache
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

            minimum_number_of_shares = (
                MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_order(
                    order, cache=self.cache
                )
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

        subscription_start_date = get_next_contract_start_date(cache=self.cache)

        ids_of_product_types_over_capacity = GlobalCapacityChecker.get_product_type_ids_without_enough_capacity_for_order(
            order_with_all_product_types=order,
            member_id=None,
            subscription_start_date=subscription_start_date,
            cache=self.cache,
        )

        response_data = {
            "ids_of_product_types_over_capacity": ids_of_product_types_over_capacity,
            "ids_of_products_over_capacity": [],
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

        contract_start_date = EarliestPossibleContractStartDateCalculator.get_earliest_possible_contract_start_date(
            reference_date=get_today(cache=self.cache),
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
