from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.views.generic import TemplateView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.response import Response
from rest_framework.views import APIView
from tapir_mail.triggers.transactional_trigger import TransactionalTriggerData

from tapir.bestell_wizard.serializers import (
    BestellWizardConfirmOrderRequestSerializer,
    BestellWizardCapacityCheckResponseSerializer,
    BestellWizardCapacityCheckRequestSerializer,
    BestellWizardBaseDataResponseSerializer,
    BestellWizardDeliveryDatesForOrderResponseSerializer,
    BestellWizardDeliveryDatesForOrderRequestSerializer,
)
from tapir.bestell_wizard.services.bestell_wizard_order_fulfiller import (
    BestellWizardOrderFulfiller,
)
from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.subscriptions.serializers import (
    OrderConfirmationResponseSerializer,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.global_capacity_checker import (
    GlobalCapacityChecker,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.subscriptions.services.product_type_lowest_free_capacity_after_date_generic import (
    ProductTypeLowestFreeCapacityAfterDateCalculator,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.waiting_list.services.waiting_list_entry_confirmation_email_sender import (
    WaitingListEntryConfirmationEmailSender,
)
from tapir.waiting_list.services.waiting_list_entry_creator import (
    WaitingListEntryCreator,
)
from tapir.waiting_list.services.waiting_list_entry_validator import (
    WaitingListEntryValidator,
)
from tapir.wirgarten.models import (
    ProductType,
    WaitingListEntry,
    Member,
    PickupLocation,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
    get_product_price,
)
from tapir.wirgarten.utils import (
    get_today,
    legal_status_is_cooperative,
)


class BestellWizardView(TemplateView):
    template_name = "bestell_wizard/bestell_wizard.html"


class BestellWizardMobileView(TemplateView):
    template_name = "bestell_wizard/bestell_wizard_mobile.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        cache = {}
        context_data["body_style"] = (
            f"background-color: {get_parameter_value(key=ParameterKeys.BESTELLWIZARD_BACKGROUND_COLOR, cache=cache)}"
        )
        background_image_url = get_parameter_value(
            key=ParameterKeys.BESTELLWIZARD_BACKGROUND_IMAGE, cache=cache
        )
        if background_image_url:
            context_data["body_style"] = (
                f"background-image: url({background_image_url}); background-repeat: repeat"
            )
        context_data["cache"] = cache
        return context_data


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

        data = {
            "order_confirmed": True,
            "error": None,
        }
        try:
            with transaction.atomic():
                self.validate_everything_and_apply_all_changes(
                    validated_serializer_data=serializer.validated_data,
                    request=request,
                    cache=self.cache,
                )
        except ValidationError as error:
            data = {
                "order_confirmed": False,
                "error": ",".join(error.messages),
            }

        return Response(OrderConfirmationResponseSerializer(data).data)

    @classmethod
    def validate_everything_and_apply_all_changes(
        cls, validated_serializer_data: dict, request, cache: dict
    ):
        if not validated_serializer_data["privacy_policy_read"]:
            raise ValidationError("Die Datenschutzklärung muss akzeptiert werden.")

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            validated_serializer_data["shopping_cart_order"], cache=cache
        )
        member = None

        if len(order) > 0 or validated_serializer_data["become_member_now"]:
            member = cls.validate_and_fulfill_order(
                request=request,
                validated_serializer_data=validated_serializer_data,
                cache=cache,
            )

        order_waiting_list = (
            TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
                validated_serializer_data["shopping_cart_waiting_list"],
                cache=cache,
            )
        )
        if (
            len(order_waiting_list) > 0
            or validated_serializer_data["become_member_now"] is False
        ):
            if member is None:
                cls.validate_and_create_waiting_list_entry_potential_member(
                    validated_serializer_data=validated_serializer_data, cache=cache
                )
            else:
                cls.validate_and_create_waiting_list_entry_existing_member(
                    member=member,
                    validated_serializer_data=validated_serializer_data,
                    cache=cache,
                )

    @classmethod
    def validate_and_fulfill_order(
        cls, request, validated_serializer_data: dict, cache: dict
    ) -> Member:
        contract_start_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=cache),
            apply_buffer_time=True,
            cache=cache,
        )

        BestellWizardOrderValidator.validate_order_and_user_data(
            validated_serializer_data=validated_serializer_data,
            contract_start_date=contract_start_date,
            cache=cache,
        )

        return BestellWizardOrderFulfiller.create_member_and_fulfill_order(
            validated_serializer_data=validated_serializer_data,
            contract_start_date=contract_start_date,
            request=request,
            cache=cache,
        )

    @classmethod
    def validate_and_create_waiting_list_entry_potential_member(
        cls, validated_serializer_data: dict, cache: dict
    ):
        waiting_list_order = (
            TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
                shopping_cart=validated_serializer_data["shopping_cart_waiting_list"],
                cache=cache,
            )
        )
        WaitingListEntryValidator.validate_creation_of_waiting_list_entry_for_a_potential_member(
            order=waiting_list_order,
            email=validated_serializer_data["personal_data"]["email"],
            number_of_coop_shares=validated_serializer_data["number_of_coop_shares"],
            cache=cache,
        )
        entry = WaitingListEntryCreator.create_entry_potential_member(
            order=waiting_list_order,
            pickup_location_ids_in_priority_order=validated_serializer_data[
                "pickup_location_ids"
            ],
            number_of_coop_shares=validated_serializer_data["number_of_coop_shares"],
            personal_data=validated_serializer_data["personal_data"],
            cache=cache,
        )
        WaitingListEntryConfirmationEmailSender.send_confirmation_mail(
            entry=entry,
            potential_member_info=TransactionalTriggerData.RecipientOutsideOfBaseQueryset(
                email=validated_serializer_data["personal_data"]["email"],
                first_name=validated_serializer_data["personal_data"]["first_name"],
                last_name=validated_serializer_data["personal_data"]["last_name"],
            ),
        )

    @classmethod
    def validate_and_create_waiting_list_entry_existing_member(
        cls, member: Member, validated_serializer_data: dict, cache: dict
    ):
        waiting_list_order = (
            TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
                shopping_cart=validated_serializer_data["shopping_cart_waiting_list"],
                cache=cache,
            )
        )
        WaitingListEntryValidator.validate_creation_of_waiting_list_entry_for_an_existing_member(
            member_id=member.id, order=waiting_list_order, cache=cache
        )
        fulfilled_order = (
            TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
                validated_serializer_data["shopping_cart_order"], cache=cache
            )
        )
        pickup_location_ids = []
        if not OrderValidator.does_order_need_a_pickup_location(
            fulfilled_order, cache=cache
        ) and OrderValidator.does_order_need_a_pickup_location(
            waiting_list_order, cache=cache
        ):
            pickup_location_ids = validated_serializer_data["pickup_location_ids"]
        entry = WaitingListEntryCreator.create_entry_existing_member(
            order=waiting_list_order,
            pickup_location_ids_in_priority_order=pickup_location_ids,
            member_id=member.id,
            cache=cache,
        )
        WaitingListEntryConfirmationEmailSender.send_confirmation_mail(
            entry=entry,
            existing_member_id=member.id,
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
        product_ids_that_are_already_at_capacity = (
            self.build_product_ids_that_are_already_at_capacity(self.cache)
        )

        response_data = {
            "price_of_a_share": get_parameter_value(
                ParameterKeys.COOP_SHARE_PRICE, cache=self.cache
            ),
            "theme": get_parameter_value(
                ParameterKeys.ORGANISATION_THEME, cache=self.cache
            ),
            "allow_investing_membership": get_parameter_value(
                ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES,
                cache=self.cache,
            ),
            "product_types": ProductType.objects.all(),
            "pickup_locations": PickupLocation.objects.order_by("name"),
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
            "show_coop_content": legal_status_is_cooperative(cache=self.cache),
            "intro_step_text": get_parameter_value(
                ParameterKeys.BESTELLWIZARD_INTRO_TEXT, cache=self.cache
            ),
            "label_checkbox_sepa_mandat": get_parameter_value(
                ParameterKeys.BESTELLWIZARD_SEPA_MANDAT_CHECKBOX_TEXT, cache=self.cache
            ),
            "label_checkbox_contract_policy": get_parameter_value(
                ParameterKeys.BESTELLWIZARD_CONTRACT_POLICY_CHECKBOX_TEXT,
                cache=self.cache,
            ),
            "revocation_rights_explanation": get_parameter_value(
                ParameterKeys.BESTELLWIZARD_REVOCATION_RIGHTS_EXPLANATION,
                cache=self.cache,
            ),
            "trial_period_length_in_weeks": get_parameter_value(
                ParameterKeys.TRIAL_PERIOD_DURATION, cache=self.cache
            ),
            "payment_rhythm_choices": {
                rhythm: MemberPaymentRhythmService.get_rhythm_display_name(
                    rhythm=rhythm
                )
                for rhythm in MemberPaymentRhythmService.get_allowed_rhythms(
                    cache=self.cache
                )
            },
            "default_payment_rhythm": get_parameter_value(
                ParameterKeys.PAYMENT_DEFAULT_RHYTHM, cache=self.cache
            ),
            "product_type_ids_that_are_already_at_capacity": self.build_product_type_ids_that_are_already_at_capacity(
                cache=self.cache,
                product_ids_that_are_already_at_capacity=product_ids_that_are_already_at_capacity,
            ),
            "product_ids_that_are_already_at_capacity": product_ids_that_are_already_at_capacity,
            "coop_statute_link": get_parameter_value(
                key=ParameterKeys.COOP_STATUTE_LINK, cache=self.cache
            ),
            "organization_name": get_parameter_value(
                key=ParameterKeys.SITE_NAME, cache=self.cache
            ),
            "logo_url": static(
                f"core/themes/{get_parameter_value(key=ParameterKeys.ORGANISATION_THEME, cache=self.cache)}/images/Logo_white.webp"
            ),
            "contact_mail_address": get_parameter_value(
                key=ParameterKeys.SITE_EMAIL, cache=self.cache
            ),
            "strings": self.build_strings_object(cache=self.cache),
        }

        return Response(BestellWizardBaseDataResponseSerializer(response_data).data)

    @classmethod
    def build_strings_object(cls, cache: dict):
        string_id_to_parameter_key_map = {
            "step1a_title": ParameterKeys.BESTELLWIZARD_STEP1A_TITLE,
            "step1a_text": ParameterKeys.BESTELLWIZARD_STEP1A_TEXT,
            "step1b_title": ParameterKeys.BESTELLWIZARD_STEP1B_TITLE,
            "step1b_text": ParameterKeys.BESTELLWIZARD_STEP1B_TEXT,
            "step2_title": ParameterKeys.BESTELLWIZARD_STEP2_TITLE,
            "step2_text": ParameterKeys.BESTELLWIZARD_STEP2_TEXT,
            "step3_title": ParameterKeys.BESTELLWIZARD_STEP3_TITLE,
            "step3_text": ParameterKeys.BESTELLWIZARD_STEP3_TEXT,
            "step5a_title": ParameterKeys.BESTELLWIZARD_STEP5A_TITLE,
            "step5a_text": ParameterKeys.BESTELLWIZARD_STEP5A_TEXT,
            "step6a_title": ParameterKeys.BESTELLWIZARD_STEP6A_TITLE,
            "step6a_text": ParameterKeys.BESTELLWIZARD_STEP6A_TEXT,
            "step6b_title": ParameterKeys.BESTELLWIZARD_STEP6B_TITLE,
            "step6b_text": ParameterKeys.BESTELLWIZARD_STEP6B_TEXT,
            "step6c_checkbox_statute": ParameterKeys.BESTELLWIZARD_STEP6C_CHECKBOX_STATUTE,
            "step6c_text_statute": ParameterKeys.BESTELLWIZARD_STEP6C_TEXT_STATUTE,
            "step6c_checkbox_commitment": ParameterKeys.BESTELLWIZARD_STEP6C_CHECKBOX_COMMITMENT,
            "step8_title": ParameterKeys.BESTELLWIZARD_STEP8_TITLE,
        }
        return {
            string_id: get_parameter_value(key=parameter_key, cache=cache)
            for string_id, parameter_key in string_id_to_parameter_key_map.items()
        }

    @classmethod
    def build_product_type_ids_that_are_already_at_capacity(
        cls, cache: dict, product_ids_that_are_already_at_capacity: list[str]
    ):
        ids = []

        subscription_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache=cache),
                apply_buffer_time=True,
                cache=cache,
            )
        )

        for product_type in TapirCache.get_product_types_in_standard_order(cache=cache):
            lowest_free_capacity = ProductTypeLowestFreeCapacityAfterDateCalculator.get_lowest_free_capacity_after_date(
                product_type=product_type,
                reference_date=subscription_start_date,
                cache=cache,
            )
            products = TapirCache.get_products_with_product_type(
                cache=cache, product_type_id=product_type.id
            )
            smallest_size = min(
                [
                    get_product_price(
                        product=product,
                        reference_date=subscription_start_date,
                        cache=cache,
                    ).size
                    for product in products
                ]
            )
            if lowest_free_capacity < smallest_size:
                ids.append(product_type.id)
                continue

            no_product_with_free_capacity = all(
                [
                    product.id in product_ids_that_are_already_at_capacity
                    for product in products
                ]
            )

            if no_product_with_free_capacity:
                ids.append(product_type.id)

        return ids

    @classmethod
    def build_product_ids_that_are_already_at_capacity(cls, cache: dict) -> list[str]:
        ids = []

        subscription_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache=cache),
                apply_buffer_time=True,
                cache=cache,
            )
        )

        for product in TapirCache.get_all_products(cache=cache):
            if not ProductCapacityChecker.does_product_have_enough_free_capacity_to_add_order(
                product=product,
                ordered_quantity=1,
                member_id=None,
                subscription_start_date=subscription_start_date,
                cache=cache,
            ):
                ids.append(product.id)

        return ids


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
            raise Http404(f"Unknown pickup location: {pickup_location_id}")

        reference_date = get_today(cache=self.cache)
        waiting_list_entry_id = serializer.validated_data.get(
            "waiting_list_entry_id", None
        )
        if waiting_list_entry_id is not None:
            waiting_list_entry = get_object_or_404(
                WaitingListEntry, id=waiting_list_entry_id
            )
            desired_start_date = waiting_list_entry.desired_start_date
            if desired_start_date is not None:
                reference_date = desired_start_date

            if len(product_type_ids) == 0 and waiting_list_entry.member is not None:
                product_type_ids = (
                    get_active_and_future_subscriptions(
                        reference_date=reference_date, cache=self.cache
                    )
                    .filter(member=waiting_list_entry.member)
                    .values_list("product__type_id", flat=True)
                    .distinct()
                )

        contract_start_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=reference_date,
            apply_buffer_time=waiting_list_entry_id is None,
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


class GetNextContractStartDateApiView(APIView):
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        responses={200: OpenApiTypes.DATE},
        parameters=[
            OpenApiParameter("waiting_list_entry_id", type=str, required=False)
        ],
    )
    def get(self, request):
        reference_date = get_today(cache=self.cache)
        waiting_list_entry_id = request.query_params.get("waiting_list_entry_id", None)
        if waiting_list_entry_id is not None:
            waiting_list_entry = get_object_or_404(
                WaitingListEntry, id=waiting_list_entry_id
            )
            desired_start_date = waiting_list_entry.desired_start_date
            if desired_start_date is not None:
                reference_date = desired_start_date

        return Response(
            ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=reference_date,
                apply_buffer_time=waiting_list_entry_id is None,
                cache=self.cache,
            )
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
                email=email, cache={}, check_waiting_list=True
            )
        except ValidationError:
            return Response(False)

        return Response(True)
