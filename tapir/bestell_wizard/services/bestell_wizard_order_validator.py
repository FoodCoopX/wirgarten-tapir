import datetime

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.minimum_number_of_shares_validator import (
    MinimumNumberOfSharesValidator,
)
from tapir.coop.services.personal_data_validator import PersonalDataValidator
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.services.required_product_types_validator import (
    RequiredProductTypesValidator,
)
from tapir.subscriptions.services.solidarity_validator_new import SolidarityValidatorNew
from tapir.subscriptions.services.tapir_order_builder import TapirOrderBuilder
from tapir.subscriptions.types import TapirOrder
from tapir.wirgarten.models import PickupLocation
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.utils import legal_status_is_cooperative


class BestellWizardOrderValidator:
    @classmethod
    def validate_complete_order(
        cls,
        validated_serializer_data: dict,
        contract_start_date: datetime.date,
        cache: dict,
    ):
        PersonalDataValidator.validate_personal_data_new_member(
            email=validated_serializer_data["personal_data"]["email"],
            phone_number=validated_serializer_data["personal_data"]["phone_number"],
            birthdate=validated_serializer_data["personal_data"]["birthdate"],
            iban=validated_serializer_data["personal_data"]["iban"],
            cache=cache,
            check_waiting_list=True,
            payment_rhythm=validated_serializer_data["payment_rhythm"],
        )

        if not validated_serializer_data["sepa_allowed"]:
            raise ValidationError("SEPA-Mandat muss erlaubt sein")

        if not validated_serializer_data["contract_accepted"]:
            raise ValidationError("Vertragsgrundsätze müssen akzeptiert sein")

        order = TapirOrderBuilder.build_tapir_order_from_shopping_cart_serializer(
            shopping_cart=validated_serializer_data["shopping_cart"], cache=cache
        )

        cls.validate_order(
            pickup_location_ids=validated_serializer_data["pickup_location_ids"],
            contract_start_date=contract_start_date,
            order=order,
            cache=cache,
        )

        if not SolidarityValidatorNew.is_the_ordered_solidarity_allowed(
            ordered_solidarity_factor=0,  # TODO
            order=order,
            start_date=contract_start_date,
            cache=cache,
        ):
            raise ValidationError("Solidarbeitrag ungültig oder zu niedrig")

        if legal_status_is_cooperative(cache=cache):
            cls.validate_coop_content(
                validated_data=validated_serializer_data, order=order, cache=cache
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
            pickup_location = get_object_or_404(
                PickupLocation, id=pickup_location_ids[0]
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
