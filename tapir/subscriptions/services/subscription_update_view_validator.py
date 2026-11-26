import datetime

from django.conf import settings
from django.core.exceptions import ValidationError

from tapir.configuration.parameter import get_parameter_value
from tapir.subscriptions.services.subscription_prerequisites_validator import (
    SubscriptionPrerequisitesValidator,
)
from tapir.subscriptions.services.order_validator import OrderValidator
from tapir.subscriptions.types import TapirOrder
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import Member, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import (
    get_active_and_future_subscriptions,
)


class SubscriptionUpdateViewValidator:
    @classmethod
    def may_member_reduce_size(cls, logged_in_user_is_admin: bool, cache: dict) -> bool:
        if logged_in_user_is_admin:
            return True

        return settings.BAKERY_ENABLED and get_parameter_value(
            ParameterKeys.BAKERY_MEMBERS_CAN_REDUCE_BREAD_SHARES, cache=cache
        )

    @classmethod
    def validate_everything(
        cls,
        sepa_allowed: bool,
        cancellation_policy_read: bool,
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

        if not cancellation_policy_read:
            raise ValidationError("Die Widerrufsbelehrung muss akzeptiert sein")

        cls.validate_all_products_belong_to_product_type(
            order=order, product_type_id=product_type.id, cache=cache
        )

        pickup_location = SubscriptionPrerequisitesValidator.validate_pickup_location(
            order=order,
            desired_pickup_location_id=desired_pickup_location_id,
            subscription_start_date=contract_start_date,
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
            member_may_reduce_size=cls.may_member_reduce_size(
                logged_in_user_is_admin=logged_in_user_is_admin, cache=cache
            ),
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

        cls.validate_optional_product_can_be_ordered_without_required_product_subscription(
            product_type=product_type,
            member=member,
            contract_start_date=contract_start_date,
            cache=cache,
        )

        SubscriptionPrerequisitesValidator.validate_banking_data(
            member=member, account_owner=account_owner, iban=iban
        )
        SubscriptionPrerequisitesValidator.validate_payment_rhythm(
            member=member, payment_rhythm=payment_rhythm, cache=cache
        )

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
    def validate_optional_product_can_be_ordered_without_required_product_subscription(
        cls,
        product_type: ProductType,
        member: Member,
        contract_start_date: datetime.date,
        cache: dict,
    ):
        if product_type.must_be_subscribed_to:
            return

        for other_product_type in ProductType.objects.filter(
            must_be_subscribed_to=True
        ):
            has_subscription_to_required_product_type = (
                get_active_and_future_subscriptions(
                    reference_date=contract_start_date, cache=cache
                )
                .filter(
                    member_id=member.id,
                    product__type_id=other_product_type.id,
                )
                .exists()
            )
            if not has_subscription_to_required_product_type:
                raise ValidationError(
                    f"Um Anteile dieses zusätzlichen Produktanteils ({product_type.name}) zu bestellen, "
                    f"musst du in derselben Vertragsperiode auch Anteile des Pflicht-Produktanteils ({other_product_type.name}) haben."
                )
