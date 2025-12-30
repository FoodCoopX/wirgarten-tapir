import datetime

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from tapir.bestell_wizard.services.questionnaire_source_service import (
    QuestionnaireSourceService,
)
from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.pickup_locations.services.pickup_location_capacity_general_checker import (
    PickupLocationCapacityGeneralChecker,
)
from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.subscriptions.services.growing_period_choice_provider import (
    GrowingPeriodChoiceProvider,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.required_product_types_validator import (
    RequiredProductTypesValidator,
)
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import (
    Member,
    GrowingPeriod,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_cooperative, get_today


class BestellWizardOrderValidator:
    @classmethod
    def validate_order_and_user_data_and_distribution_channels(
        cls,
        validated_serializer_data: dict,
        contract_start_date: datetime.date,
        cache: dict,
    ):
        PersonalDataValidator.validate_personal_data_new_member(
            email=validated_serializer_data["personal_data"]["email"],
            phone_number=validated_serializer_data["personal_data"]["phone_number"],
            iban=validated_serializer_data["personal_data"]["iban"],
            account_owner=validated_serializer_data["personal_data"]["account_owner"],
            cache=cache,
            check_waiting_list=True,
            payment_rhythm=validated_serializer_data["payment_rhythm"],
        )

        if not validated_serializer_data["sepa_allowed"]:
            raise ValidationError("SEPA-Mandat muss erlaubt sein")

        if (
            cls.is_contract_required(cache=cache)
            and not validated_serializer_data["contract_accepted"]
        ):
            raise ValidationError("Vertragsgrundsätze müssen akzeptiert sein")

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=validated_serializer_data["shopping_cart_order"], cache=cache
        )

        if (
            cls.is_cancellation_policy_required(
                order=order,
                solidarity_contribution=validated_serializer_data[
                    "solidarity_contribution"
                ],
            )
            and not validated_serializer_data["cancellation_policy_read"]
        ):
            raise ValidationError("Die Widerrufsbelehrung muss akzeptiert sein")

        cls.validate_order(
            pickup_location_ids=validated_serializer_data["pickup_location_ids"],
            contract_start_date=contract_start_date,
            order=order,
            cache=cache,
        )

        if not SolidarityValidator.is_the_ordered_solidarity_allowed(
            amount=validated_serializer_data["solidarity_contribution"],
            start_date=contract_start_date,
            cache=cache,
        ):
            raise ValidationError("Solidarbeitrag ungültig oder zu niedrig")

        if legal_status_is_cooperative(cache=cache):
            cls.validate_coop_content(
                validated_data=validated_serializer_data, order=order, cache=cache
            )

        cls.validate_distribution_channels(
            validated_serializer_data["distribution_channels"], cache=cache
        )

    @classmethod
    def validate_distribution_channels(cls, given_channel_ids: list[str], cache: dict):
        valid_ids = set(
            QuestionnaireSourceService.get_questionnaire_source_choices(
                cache=cache
            ).keys()
        )

        if not set(given_channel_ids).issubset(valid_ids):
            raise ValidationError("Ungültige Vertriebskanäle")

    @classmethod
    def is_cancellation_policy_required(
        cls, order: TapirOrder, solidarity_contribution: float
    ):
        return sum(order.values(), start=0) > 0 or solidarity_contribution > 0

    @classmethod
    def is_contract_required(cls, cache: dict):
        return (
            get_parameter_value(
                key=ParameterKeys.BESTELLWIZARD_CONTRACT_POLICY_CHECKBOX_TEXT,
                cache=cache,
            ).strip()
            != ""
        )

    @classmethod
    def validate_order(
        cls,
        pickup_location_ids: list[str],
        contract_start_date: datetime.date,
        order: TapirOrder,
        cache: dict,
    ):
        if len(order.keys()) > 0 and get_parameter_value(
            ParameterKeys.BESTELLWIZARD_FORCE_WAITING_LIST, cache=cache
        ):
            raise ValidationError("Nur Warteliste-Einträge sind erlaubt.")

        pickup_location = None
        if OrderValidator.does_order_need_a_pickup_location(order=order, cache=cache):
            if len(pickup_location_ids) == 0:
                raise ValidationError(
                    "Diese Bestellung braucht eine Verteilstation, bitte wählt eine aus."
                )

            pickup_location = cls.get_first_pickup_location_with_enough_capacity(
                pickup_location_ids=pickup_location_ids,
                order=order,
                member=None,
                contract_start_date=contract_start_date,
                cache=cache,
            )
            if pickup_location is None:
                raise ValidationError(
                    "Keine der ausgewählte Verteilstationen hat genug Kapazität"
                )

        OrderValidator.validate_order_general(
            order=order,
            contract_start_date=contract_start_date,
            cache=cache,
            member=None,
            pickup_location=pickup_location,
        )

        if not RequiredProductTypesValidator.does_order_contain_all_required_product_types(
            order=order
        ):
            raise ValidationError("Manche Pflichtprodukte fehlen in der Bestellung")

    @classmethod
    def validate_coop_content(
        cls, validated_data: dict, order: TapirOrder, cache: dict
    ):
        student_status_enabled = validated_data["student_status_enabled"]
        if student_status_enabled and not get_parameter_value(
            ParameterKeys.ALLOW_STUDENT_TO_ORDER_WITHOUT_COOP_SHARES, cache=cache
        ):
            raise ValidationError("Studenten-Status ist nicht erlaubt")

        nb_ordered_coop_shares = validated_data["number_of_coop_shares"]
        if student_status_enabled:
            if nb_ordered_coop_shares > 0:
                raise ValidationError(
                    "Studenten-Status aktiviert, es sollen keine Genossenschaftsanteilen bestellt werden."
                )
        else:
            if not validated_data["statute_accepted"]:
                raise ValidationError("Die Satzung muss akzeptiert werden.")

            minimum_number_of_shares = MinimumNumberOfSharesValidator.get_minimum_number_of_shares_for_tapir_order(
                order, cache=cache
            )
            if nb_ordered_coop_shares < minimum_number_of_shares:
                raise ValidationError(
                    f"Genossenschaftsanteile bestellt: {nb_ordered_coop_shares}, minimum: {minimum_number_of_shares}."
                )

    @classmethod
    def get_first_pickup_location_with_enough_capacity(
        cls,
        pickup_location_ids: list[str],
        order: TapirOrder,
        member: Member | None,
        contract_start_date: datetime.date,
        cache: dict,
    ):
        pickup_locations = [
            TapirCache.get_pickup_location_by_id(
                cache=cache, pickup_location_id=pickup_location_id
            )
            for pickup_location_id in pickup_location_ids
        ]

        for pickup_location in pickup_locations:
            if PickupLocationCapacityGeneralChecker.does_pickup_location_have_enough_capacity_to_add_subscriptions(
                pickup_location=pickup_location,
                order=order,
                already_registered_member=member,
                subscription_start=contract_start_date,
                cache=cache,
            ):
                return pickup_location

        return None

    @classmethod
    def validated_growing_period_and_get_contract_start_date(
        cls, growing_period_id: str, cache: dict
    ):
        growing_period = cls.get_and_validate_growing_period(growing_period_id, cache)

        return (
            ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period,
                apply_buffer_time=True,
                cache=cache,
            )
        )

    @classmethod
    def get_and_validate_growing_period(cls, growing_period_id: str, cache: dict):
        growing_period = get_object_or_404(GrowingPeriod, id=growing_period_id)
        if (
            growing_period
            not in GrowingPeriodChoiceProvider.get_available_growing_periods(
                reference_date=get_today(cache=cache), cache=cache
            )
        ):
            raise ValidationError("Ungültige Vertragsperiode " + growing_period_id)
        return growing_period
