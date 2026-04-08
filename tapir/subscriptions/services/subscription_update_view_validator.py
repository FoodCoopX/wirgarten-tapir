import datetime

from django.core.exceptions import ValidationError
from localflavor.generic.validators import IBANValidator

from tapir.configuration.parameter import get_parameter_value
from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.base_product_type_service import (
    BaseProductTypeService,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, PickupLocation, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)
from tapir.wirgarten.utils import get_today


class SubscriptionUpdateViewValidator:
    @classmethod
    def validate_everything(
        cls,
        sepa_allowed: bool,
        order: TapirOrder,
        product_type: ProductType,
        contract_start_date: datetime.date,
        member: Member,
        logged_in_user_is_admin: bool,
        desired_pickup_location_id: str | None,
        account_owner: str,
        iban: str,
        payment_rhythm: str | None,
        cache: dict,
    ):
        if not sepa_allowed:
            raise ValidationError("Das SEPA-Mandat muss ermächtigt sein.")

        cls.validate_all_products_belong_to_product_type(
            order=order, product_type_id=product_type.id, cache=cache
        )

        pickup_location = cls.validate_pickup_location(
            order=order,
            desired_pickup_location_id=desired_pickup_location_id,
            contract_start_date=contract_start_date,
            member=member,
            cache=cache,
        )

        OrderValidator.validate_order_general(
            order=order,
            pickup_location=pickup_location,
            contract_start_date=contract_start_date,
            cache=cache,
            member=member,
        )

        OrderValidator.validate_cannot_reduce_size(
            logged_in_user_is_admin=logged_in_user_is_admin,
            contract_start_date=contract_start_date,
            member=member,
            order_for_a_single_product_type=order,
            product_type=product_type,
            cache=cache,
        )

        OrderValidator.validate_at_least_one_change(
            member=member,
            contract_start_date=contract_start_date,
            cache=cache,
            product_type=product_type,
            order=order,
        )

        cls.validate_additional_product_can_be_ordered_without_base_product_subscription(
            product_type=product_type,
            member=member,
            contract_start_date=contract_start_date,
            cache=cache,
        )

        cls.validate_banking_data(
            member=member,
            account_owner=account_owner,
            iban=iban,
            payment_rhythm=payment_rhythm,
            cache=cache,
        )

    @classmethod
    def validate_banking_data(
        cls,
        member: Member,
        account_owner: str,
        iban: str,
        payment_rhythm: str | None,
        cache: dict,
    ):
        if MemberNeedsBankingDataChecker.does_member_need_banking_data(member):
            IBANValidator()(iban)

            if account_owner == "":
                raise ValidationError("Das Feld 'Kontoinhaber*in' muss ausgefüllt sein")

        need_payment_rhythm = (
            TapirCache.get_member_payment_rhythm_object(
                member=member,
                reference_date=get_today(cache=cache),
                cache=cache,
            )
            is None
        )

        if need_payment_rhythm and payment_rhythm is None:
            raise ValidationError("Das Zahlungsintervall fehlt")

        if payment_rhythm is None:
            return

        if not MemberPaymentRhythmService.is_payment_rhythm_allowed(
            payment_rhythm, cache=cache
        ):
            raise ValidationError(
                f"Diese Zahlungsintervall {payment_rhythm} is nicht erlaubt, erlaubt sind: {MemberPaymentRhythmService.get_allowed_rhythms(cache=cache)}"
            )

    @classmethod
    def validate_pickup_location(
        cls,
        order: TapirOrder,
        member: Member,
        contract_start_date: datetime.date,
        desired_pickup_location_id: str | None,
        cache: dict,
    ):
        if not OrderValidator.does_order_need_a_pickup_location(
            order=order, cache=cache
        ):
            return None

        current_pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id(
                member=member, reference_date=contract_start_date
            )
        )
        if (
            current_pickup_location_id is not None
            and desired_pickup_location_id is not None
            and current_pickup_location_id != desired_pickup_location_id
        ):
            raise ValidationError("Du hast schon eine Verteilstation")

        pickup_location_id = current_pickup_location_id or desired_pickup_location_id
        if pickup_location_id is None:
            raise ValidationError("Bitte wähle einen Abholort aus!")

        return PickupLocation.objects.get(id=pickup_location_id)

    @classmethod
    def validate_all_products_belong_to_product_type(
        cls, order: TapirOrder, product_type_id, cache: dict
    ):
        for product in order.keys():
            product = TapirCache.get_product_by_id(cache=cache, product_id=product.id)
            if product.type_id != product_type_id:
                raise ValidationError(
                    f"Product '{product.name}' does not belong to product type with id: {product_type_id}"
                )

    @classmethod
    def validate_additional_product_can_be_ordered_without_base_product_subscription(
        cls,
        product_type: ProductType,
        member: Member,
        contract_start_date: datetime.date,
        cache: dict,
    ):
        if get_parameter_value(
            ParameterKeys.SUBSCRIPTION_ADDITIONAL_PRODUCT_ALLOWED_WITHOUT_BASE_PRODUCT,
            cache=cache,
        ):
            return

        base_product_type = BaseProductTypeService.get_base_product_type(cache=cache)
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
