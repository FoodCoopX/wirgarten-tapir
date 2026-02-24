import datetime

from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
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
    PublicProductPricesResponseSerializer,
)
from tapir.bestell_wizard.services.bestell_wizard_order_fulfiller import (
    BestellWizardOrderFulfiller,
)
from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.bestell_wizard.services.questionnaire_source_service import (
    QuestionnaireSourceService,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.deliveries.serializers import PublicGrowingPeriodSerializer
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.public_pickup_locations_provider import (
    PublicPickupLocationProvider,
)
from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
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
from tapir.subscriptions.services.growing_period_choice_provider import (
    GrowingPeriodChoiceProvider,
)
from tapir.subscriptions.services.product_capacity_checker import ProductCapacityChecker
from tapir.subscriptions.services.product_type_lowest_free_capacity_after_date_generic import (
    ProductTypeLowestFreeCapacityAfterDateCalculator,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.types import TapirOrder
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
from tapir.wirgarten.constants import Permission
from tapir.wirgarten.models import (
    ProductType,
    WaitingListEntry,
    Member,
    PickupLocation,
    GrowingPeriod,
    Product,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.delivery import calculate_pickup_location_change_date
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
    get_product_price,
)
from tapir.wirgarten.utils import (
    get_today,
    legal_status_is_cooperative,
    check_permission_or_self,
)


class BestellWizardView(TemplateView):
    template_name = "bestell_wizard/bestell_wizard.html"


class BestellWizardMobileView(TemplateView):
    template_name = "bestell_wizard/bestell_wizard_mobile.html"

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        cache = {}
        self.add_body_style_context(context_data, cache)
        return context_data

    @classmethod
    def add_body_style_context(cls, context_data: dict, cache: dict):
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


class BestellWizardCoopSharesView(TemplateView):
    template_name = "bestell_wizard/bestell_wizard_coop_shares.html"

    def get(self, request, *args, **kwargs):
        check_permission_or_self(pk=kwargs["member_id"], request=request)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        cache = {}
        BestellWizardMobileView.add_body_style_context(context_data, cache)
        context_data["member_id"] = kwargs["member_id"]
        member = get_object_or_404(Member, id=kwargs["member_id"])
        context_data["first_name"] = member.first_name
        context_data["last_name"] = member.last_name
        context_data["needs_banking_data"] = (
            MemberNeedsBankingDataChecker.does_member_need_banking_data(member)
        )
        context_data["member_url"] = member.get_absolute_url()
        return context_data


class BestellWizardProductTypeView(TemplateView):
    template_name = "bestell_wizard/bestell_wizard_product_type.html"

    def get(self, request, *args, **kwargs):
        check_permission_or_self(pk=kwargs["member_id"], request=request)
        if not request.user.has_perm(
            Permission.Coop.MANAGE
        ) and not get_parameter_value(
            ParameterKeys.MEMBERS_CAN_UPDATE_THEIR_CONTRACTS, cache={}
        ):
            raise PermissionDenied()
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context_data = super().get_context_data(**kwargs)
        cache = {}
        BestellWizardMobileView.add_body_style_context(context_data, cache)
        context_data["member_id"] = kwargs["member_id"]
        context_data["product_type_id"] = kwargs["product_type_id"]

        member = get_object_or_404(Member, id=kwargs["member_id"])
        context_data["first_name"] = member.first_name
        context_data["last_name"] = member.last_name
        context_data["needs_banking_data"] = (
            MemberNeedsBankingDataChecker.does_member_need_banking_data(member)
        )
        context_data["member_url"] = member.get_absolute_url()
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
            member = None
            with transaction.atomic():
                member = self.validate_everything_and_apply_all_changes(
                    validated_serializer_data=serializer.validated_data,
                    request=request,
                    cache=self.cache,
                )
            if member is not None:
                # The member creation does calls to KeycloakUserManager that are only applied after the transaction ends.
                # In order to persist the changes that the KeycloakUserManager applies, we need to save manually one more time.
                member.save()
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
            or len(validated_serializer_data["pickup_location_ids"]) > 1
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

        return member

    @classmethod
    def validate_and_fulfill_order(
        cls,
        request,
        validated_serializer_data: dict,
        cache: dict,
    ) -> Member:
        contract_start_date = BestellWizardOrderValidator.validated_growing_period_and_get_contract_start_date(
            validated_serializer_data["growing_period_id"], cache=cache
        )

        BestellWizardOrderValidator.validate_order_and_user_data_and_distribution_channels(
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
        cls,
        member: Member,
        validated_serializer_data: dict,
        cache: dict,
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

        entry = WaitingListEntryCreator.create_entry_existing_member(
            order=waiting_list_order,
            pickup_location_ids_in_priority_order=validated_serializer_data[
                "pickup_location_ids"
            ],
            member=member,
            growing_period_id=validated_serializer_data["growing_period_id"],
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
        growing_period = get_object_or_404(
            GrowingPeriod, id=serializer.validated_data["growing_period_id"]
        )

        subscription_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period,
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
        available_growing_periods = (
            GrowingPeriodChoiceProvider.get_available_growing_periods(
                reference_date=get_today(cache=self.cache), cache=self.cache
            )
        )
        earliest_contract_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=available_growing_periods[0],
                apply_buffer_time=True,
                cache=self.cache,
            )
        )
        product_ids_that_are_already_at_capacity = (
            self.build_product_ids_that_are_already_at_capacity(
                self.cache, contract_start_date=earliest_contract_start_date
            )
        )

        response_data = self.build_simple_response_fields(self.cache)

        trial_period_length_in_weeks = 0
        if get_parameter_value(
            key=ParameterKeys.TRIAL_PERIOD_ENABLED, cache=self.cache
        ):
            trial_period_length_in_weeks = get_parameter_value(
                key=ParameterKeys.TRIAL_PERIOD_DURATION, cache=self.cache
            )

        response_data.update(
            {
                "product_types": ProductType.objects.all(),
                "pickup_locations": PublicPickupLocationProvider.get_pickup_locations_available_for_members(
                    cache=self.cache
                ),
                "show_coop_content": legal_status_is_cooperative(cache=self.cache),
                "trial_period_length_in_weeks": trial_period_length_in_weeks,
                "payment_rhythm_choices": {
                    rhythm: MemberPaymentRhythmService.get_rhythm_display_name(
                        rhythm=rhythm
                    )
                    for rhythm in MemberPaymentRhythmService.get_allowed_rhythms(
                        cache=self.cache
                    )
                },
                "product_type_ids_that_are_already_at_capacity": self.build_product_type_ids_that_are_already_at_capacity(
                    cache=self.cache,
                    product_ids_that_are_already_at_capacity=product_ids_that_are_already_at_capacity,
                    contract_start_date=earliest_contract_start_date,
                ),
                "product_ids_that_are_already_at_capacity": product_ids_that_are_already_at_capacity,
                "logo_url": static(
                    f"core/themes/{get_parameter_value(key=ParameterKeys.ORGANISATION_THEME, cache=self.cache)}/images/Logo_white.webp"
                ),
                "distribution_channels": QuestionnaireSourceService.get_questionnaire_source_choices(
                    cache=self.cache
                ),
                "solidarity_contribution_choices": SolidarityValidator.get_solidarity_dropdown_values(
                    cache=self.cache
                ),
                "solidarity_contribution_minimum": SolidarityValidator.get_solidarity_contribution_minimum(
                    reference_date=earliest_contract_start_date,
                    cache=self.cache,
                ),
                "growing_period_choices": available_growing_periods,
                "strings": self.build_strings_object(cache=self.cache),
                "images": self.build_images_object(cache=self.cache),
                "debug": settings.DEBUG,
            }
        )

        return Response(BestellWizardBaseDataResponseSerializer(response_data).data)

    @classmethod
    def build_simple_response_fields(cls, cache: dict):
        serializer_key_to_parameter_key_map = {
            "price_of_a_share": ParameterKeys.COOP_SHARE_PRICE,
            "theme": ParameterKeys.ORGANISATION_THEME,
            "allow_investing_membership": ParameterKeys.COOP_SHARES_INDEPENDENT_FROM_HARVEST_SHARES,
            "force_waiting_list": ParameterKeys.BESTELLWIZARD_FORCE_WAITING_LIST,
            "intro_enabled": ParameterKeys.BESTELLWIZARD_SHOW_INTRO,
            "student_status_allowed": ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES,
            "intro_step_text": ParameterKeys.BESTELLWIZARD_INTRO_TEXT,
            "label_checkbox_sepa_mandat": ParameterKeys.BESTELLWIZARD_SEPA_MANDAT_CHECKBOX_TEXT,
            "label_checkbox_contract_policy": ParameterKeys.BESTELLWIZARD_CONTRACT_POLICY_CHECKBOX_TEXT,
            "default_payment_rhythm": ParameterKeys.PAYMENT_DEFAULT_RHYTHM,
            "coop_statute_link": ParameterKeys.COOP_STATUTE_LINK,
            "organization_name": ParameterKeys.SITE_NAME,
            "contact_mail_address": ParameterKeys.SITE_EMAIL,
            "solidarity_contribution_default": ParameterKeys.SOLIDARITY_DEFAULT,
            "feedback_step_enabled": ParameterKeys.BESTELLWIZARD_STEP13_ENABLED,
        }
        return cls.build_dictionary_from_config_parameters(
            serializer_key_to_parameter_key_map, cache
        )

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
            "step3b_title": ParameterKeys.BESTELLWIZARD_STEP3B_TITLE,
            "step3b_text": ParameterKeys.BESTELLWIZARD_STEP3B_TEXT,
            "step4b_waiting_list_modal_title": ParameterKeys.BESTELL_WIZARD_STEP4B_WAITING_LIST_MODAL_HEADER,
            "step4b_waiting_list_modal_text": ParameterKeys.BESTELL_WIZARD_STEP4B_WAITING_LIST_MODAL_TEXT,
            "step4d_title": ParameterKeys.BESTELLWIZARD_STEP4D_TITLE,
            "step4d_text": ParameterKeys.BESTELLWIZARD_STEP4D_TEXT,
            "step5a_title": ParameterKeys.BESTELLWIZARD_STEP5A_TITLE,
            "step5a_text": ParameterKeys.BESTELLWIZARD_STEP5A_TEXT,
            "step5b_title": ParameterKeys.BESTELLWIZARD_STEP5B_TITLE,
            "step5c_title": ParameterKeys.BESTELLWIZARD_STEP5C_TITLE,
            "step5c_text": ParameterKeys.BESTELLWIZARD_STEP5C_TEXT,
            "step6a_title": ParameterKeys.BESTELLWIZARD_STEP6A_TITLE,
            "step6a_text": ParameterKeys.BESTELLWIZARD_STEP6A_TEXT,
            "step6b_title": ParameterKeys.BESTELLWIZARD_STEP6B_TITLE,
            "step6b_text": ParameterKeys.BESTELLWIZARD_STEP6B_TEXT,
            "step6c_title": ParameterKeys.BESTELLWIZARD_STEP6C_TITLE,
            "step6c_text": ParameterKeys.BESTELLWIZARD_STEP6C_TEXT,
            "step6c_checkbox_statute": ParameterKeys.BESTELLWIZARD_STEP6C_CHECKBOX_STATUTE,
            "step6c_text_statute": ParameterKeys.BESTELLWIZARD_STEP6C_TEXT_STATUTE,
            "step6c_checkbox_commitment": ParameterKeys.BESTELLWIZARD_STEP6C_CHECKBOX_COMMITMENT,
            "step8_title": ParameterKeys.BESTELLWIZARD_STEP8_TITLE,
            "step8_text": ParameterKeys.BESTELLWIZARD_STEP8_TEXT,
            "step9_title": ParameterKeys.BESTELLWIZARD_STEP9_TITLE,
            "step9_payment_rhythm_modal_text": ParameterKeys.BESTELLWIZARD_STEP9_PAYMENT_RHYTHM_MODAL_TEXT,
            "step10_title": ParameterKeys.BESTELLWIZARD_STEP10_TITLE,
            "step11_title": ParameterKeys.BESTELLWIZARD_STEP11_TITLE,
            "step11_privacy_policy_label": ParameterKeys.BESTELLWIZARD_PRIVACY_POLICY_LABEL,
            "step11_privacy_policy_text": ParameterKeys.BESTELLWIZARD_PRIVACY_POLICY_EXPLANATION,
            "step11_revocation_label": ParameterKeys.BESTELLWIZARD_REVOCATION_RIGHTS_LABEL,
            "step11_revocation_text": ParameterKeys.BESTELLWIZARD_REVOCATION_RIGHTS_EXPLANATION,
            "step12_title": ParameterKeys.BESTELLWIZARD_STEP12_TITLE,
            "step13_title": ParameterKeys.BESTELLWIZARD_STEP13_TITLE,
            "step13_text": ParameterKeys.BESTELLWIZARD_STEP13_TEXT,
            "step14_title": ParameterKeys.BESTELLWIZARD_STEP14_TITLE,
            "step14_text": ParameterKeys.BESTELLWIZARD_STEP14_TEXT,
            "step14b_title": ParameterKeys.BESTELLWIZARD_STEP14B_TITLE,
            "step14b_text": ParameterKeys.BESTELLWIZARD_STEP14B_TEXT,
            "privacy_policy_url": ParameterKeys.SITE_PRIVACY_LINK,
            "label_student_checkbox": ParameterKeys.LABEL_STUDENT_CHECKBOX,
        }
        return cls.build_dictionary_from_config_parameters(
            string_id_to_parameter_key_map, cache
        )

    @classmethod
    def build_images_object(cls, cache: dict):
        image_id_to_parameter_key_map = {
            "step1_background_image": ParameterKeys.BESTELLWIZARD_STEP1_BACKGROUND_IMAGE,
            "step2_background_image": ParameterKeys.BESTELLWIZARD_STEP2_BACKGROUND_IMAGE,
            "step3_background_image": ParameterKeys.BESTELLWIZARD_STEP3_BACKGROUND_IMAGE,
            "step4d_background_image": ParameterKeys.BESTELLWIZARD_STEP4D_BACKGROUND_IMAGE,
            "step5_background_image": ParameterKeys.BESTELLWIZARD_STEP5_BACKGROUND_IMAGE,
            "step6_background_image": ParameterKeys.BESTELLWIZARD_STEP6_BACKGROUND_IMAGE,
            "step8_background_image": ParameterKeys.BESTELLWIZARD_STEP8_BACKGROUND_IMAGE,
            "step9_background_image": ParameterKeys.BESTELLWIZARD_STEP9_BACKGROUND_IMAGE,
            "step10_background_image": ParameterKeys.BESTELLWIZARD_STEP10_BACKGROUND_IMAGE,
            "step11_background_image": ParameterKeys.BESTELLWIZARD_STEP11_BACKGROUND_IMAGE,
            "step12_background_image": ParameterKeys.BESTELLWIZARD_STEP12_BACKGROUND_IMAGE,
            "step13_background_image": ParameterKeys.BESTELLWIZARD_STEP13_BACKGROUND_IMAGE,
            "step14_background_image": ParameterKeys.BESTELLWIZARD_STEP14_BACKGROUND_IMAGE,
        }
        return cls.build_dictionary_from_config_parameters(
            image_id_to_parameter_key_map, cache
        )

    @classmethod
    def build_dictionary_from_config_parameters(
        cls, serializer_key_to_parameter_key_map: dict, cache: dict
    ):
        return {
            serializer_key: get_parameter_value(key=parameter_key, cache=cache)
            for serializer_key, parameter_key in serializer_key_to_parameter_key_map.items()
        }

    @classmethod
    def build_product_type_ids_that_are_already_at_capacity(
        cls,
        cache: dict,
        product_ids_that_are_already_at_capacity: list[str],
        contract_start_date: datetime.date,
    ):
        ids = []

        for product_type in TapirCache.get_product_types_in_standard_order(cache=cache):
            products = TapirCache.get_products_with_product_type(
                cache=cache, product_type_id=product_type.id
            )
            if len(products) == 0:
                continue

            lowest_free_capacity = ProductTypeLowestFreeCapacityAfterDateCalculator.get_lowest_free_capacity_after_date(
                product_type=product_type,
                reference_date=contract_start_date,
                cache=cache,
            )

            smallest_size = min(
                [
                    get_product_price(
                        product=product,
                        reference_date=contract_start_date,
                        cache=cache,
                    ).size
                    for product in products
                ],
            )
            if lowest_free_capacity < smallest_size:
                ids.append(product_type.id)
                continue

            no_product_with_free_capacity = all(
                product.id in product_ids_that_are_already_at_capacity
                for product in products
            )

            if no_product_with_free_capacity:
                ids.append(product_type.id)

        return ids

    @classmethod
    def build_product_ids_that_are_already_at_capacity(
        cls, cache: dict, contract_start_date: datetime.date
    ) -> list[str]:
        ids = []

        for product in TapirCache.get_all_products(cache=cache):
            if not ProductCapacityChecker.does_product_have_enough_free_capacity_to_add_order(
                product=product,
                ordered_quantity=1,
                member_id=None,
                subscription_start_date=contract_start_date,
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

        waiting_list_entry_id = serializer.validated_data.get(
            "waiting_list_entry_id", None
        )
        waiting_list_entry = None
        if waiting_list_entry_id is not None:
            waiting_list_entry = get_object_or_404(
                WaitingListEntry, id=waiting_list_entry_id
            )

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=serializer.validated_data["shopping_cart"], cache=self.cache
        )
        product_type_ids = self.get_relevant_product_type_ids(
            order=order, waiting_list_entry=waiting_list_entry, cache=self.cache
        )

        growing_period_id = serializer.validated_data.get("growing_period_id", None)
        growing_period = None
        if growing_period_id is not None:
            growing_period = get_object_or_404(GrowingPeriod, id=growing_period_id)

        reference_date = self.get_reference_date(
            waiting_list_entry=waiting_list_entry,
            growing_period=growing_period,
            cache=self.cache,
        )

        response_data = {}
        for pickup_location_id in PickupLocation.objects.values_list("id", flat=True):
            response_data[pickup_location_id] = {
                product_type_id: DeliveryDateCalculator.get_next_delivery_date_for_delivery_cycle(
                    reference_date=reference_date,
                    pickup_location_id=pickup_location_id,
                    delivery_cycle=TapirCache.get_product_type_by_id(
                        cache=self.cache, product_type_id=product_type_id
                    ).delivery_cycle,
                    check_for_weeks_without_delivery=True,
                    cache=self.cache,
                )
                for product_type_id in product_type_ids
            }

        return Response(
            BestellWizardDeliveryDatesForOrderResponseSerializer(
                {
                    "delivery_date_by_pickup_location_id_and_product_type_id": response_data
                }
            ).data
        )

    @classmethod
    def get_reference_date(
        cls,
        waiting_list_entry: WaitingListEntry | None,
        growing_period: GrowingPeriod | None,
        cache: dict,
    ):
        if waiting_list_entry is not None:
            if waiting_list_entry.desired_start_date:
                return waiting_list_entry.desired_start_date

            if waiting_list_entry.product_wishes.count() == 0:
                return calculate_pickup_location_change_date(cache=cache)

            else:
                return ContractStartDateCalculator.get_next_contract_start_date(
                    reference_date=get_today(cache=cache),
                    apply_buffer_time=False,
                    cache=cache,
                )

        if growing_period is None:
            return ContractStartDateCalculator.get_next_contract_start_date(
                reference_date=get_today(cache=cache),
                apply_buffer_time=True,
                cache=cache,
            )
        else:
            return ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period,
                apply_buffer_time=True,
                cache=cache,
            )

    @classmethod
    def get_relevant_product_type_ids(
        cls, order: TapirOrder, waiting_list_entry: WaitingListEntry | None, cache: dict
    ):
        product_type_ids = {product.type_id for product in order.keys()}
        if (
            waiting_list_entry is None
            or len(product_type_ids) > 0
            or waiting_list_entry.member is None
        ):
            return product_type_ids

        return (
            get_active_and_future_subscriptions(
                reference_date=waiting_list_entry.desired_start_date
                or get_today(cache=cache),
                cache=cache,
            )
            .filter(member=waiting_list_entry.member)
            .values_list("product__type_id", flat=True)
            .distinct()
        )


class GetContractStartDateForWaitingListEntryApiView(APIView):
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        responses={200: OpenApiTypes.DATE},
        parameters=[
            OpenApiParameter("waiting_list_entry_id", type=str),
        ],
    )
    def get(self, request):
        waiting_list_entry_id = request.query_params.get("waiting_list_entry_id")
        waiting_list_entry = get_object_or_404(
            WaitingListEntry, id=waiting_list_entry_id
        )
        contract_start_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=waiting_list_entry.desired_start_date
            or get_today(cache=self.cache),
            apply_buffer_time=False,
            cache=self.cache,
        )

        return Response(contract_start_date)


class GetEarliestContractStartDateApiView(APIView):
    permission_classes = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = {}

    @extend_schema(
        responses={200: OpenApiTypes.DATE},
    )
    def get(self, request):
        contract_start_date = ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=self.cache),
            apply_buffer_time=True,
            cache=self.cache,
        )

        return Response(contract_start_date)


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


class PublicProductPricesApiView(APIView):
    permission_classes = []

    @extend_schema(
        responses={200: PublicProductPricesResponseSerializer},
        parameters=[OpenApiParameter("growing_period_id", type=str)],
    )
    def get(self, request):
        growing_period = get_object_or_404(
            GrowingPeriod, id=request.query_params.get("growing_period_id")
        )
        contract_start_date = PublicGrowingPeriodSerializer.get_contract_start_date(
            growing_period
        )

        cache = {}
        prices_by_product_id = {
            product.id: get_product_price(
                product=product, reference_date=contract_start_date, cache=cache
            ).price
            for product in Product.objects.all()
        }

        return Response(
            PublicProductPricesResponseSerializer(
                {"prices_by_product_id": prices_by_product_id}
            ).data
        )
