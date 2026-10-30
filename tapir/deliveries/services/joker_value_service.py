import datetime
from dataclasses import dataclass
from decimal import Decimal

from tapir.configuration.parameter import get_parameter_value
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.solidarity_contribution.services.member_solidarity_contribution_service import (
    MemberSolidarityContributionService,
)
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.constants import CUSTOM_CYCLE
from tapir.wirgarten.models import Member, Subscription
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.utils import format_currency


@dataclass
class JokerCreditValuePart:
    explanation: str
    value: Decimal


class JokerValueService:
    @classmethod
    def get_joker_credit_value_for_single_joker(
        cls, member: Member, joker_date: datetime.date, cache: dict
    ) -> Decimal:
        return cls.get_total_value(
            cls.get_joker_credit_value_parts(
                member=member, joker_date=joker_date, cache=cache
            )
        )

    @classmethod
    def get_total_value(cls, parts: list[JokerCreditValuePart]) -> Decimal:
        # A negative solidarity contribution may lower the credit, but never below 0.
        return max(sum((part.value for part in parts), start=Decimal(0)), Decimal(0))

    @classmethod
    def build_explanation(cls, parts: list[JokerCreditValuePart]) -> str:
        lines = ["Berechnung der Gutschrift:"]
        lines.extend(f"- {part.explanation}" for part in parts)
        lines.append(f"Summe: {format_currency(cls.get_total_value(parts))} €")
        return "\n".join(lines)

    @classmethod
    def get_joker_credit_value_parts(
        cls, member: Member, joker_date: datetime.date, cache: dict
    ) -> list[JokerCreditValuePart]:
        subscriptions = list(
            DeliveryPriceCalculator.get_subscriptions_that_get_delivered_in_week(
                member=member, reference_date=joker_date, cache=cache
            )
            .filter(product__type__is_affected_by_jokers=True)
            .order_by("product__type__name", "product__name")
        )
        parts = [
            cls._get_subscription_part(
                subscription=subscription, joker_date=joker_date, cache=cache
            )
            for subscription in subscriptions
        ]
        solidarity_part = cls._get_solidarity_contribution_part(
            member=member,
            joker_date=joker_date,
            subscriptions=subscriptions,
            cache=cache,
        )
        if solidarity_part is not None:
            parts.append(solidarity_part)

        delivery_charge_part = cls._get_delivery_charge_part(
            member=member, joker_date=joker_date, cache=cache
        )
        if delivery_charge_part is not None:
            parts.append(delivery_charge_part)

        return parts

    @classmethod
    def _get_subscription_part(
        cls, subscription: Subscription, joker_date: datetime.date, cache: dict
    ) -> JokerCreditValuePart:
        value = DeliveryPriceCalculator.get_price_of_single_delivery_for_subscription(
            subscription=subscription, at_date=joker_date, cache=cache
        )
        product_price = get_product_price(
            product=subscription.product, reference_date=joker_date, cache=cache
        ).price
        name = f"{subscription.product.type.name} {subscription.product.name}"

        if subscription.product.type.delivery_cycle == CUSTOM_CYCLE[0]:
            return JokerCreditValuePart(
                explanation=f"{name}: Preis pro Lieferung {format_currency(product_price)} €",
                value=value,
            )

        calculation = cls._build_monthly_to_delivery_calculation(
            monthly_amount=product_price,
            delivery_cycle=subscription.product.type.delivery_cycle,
            joker_date=joker_date,
        )
        if subscription.quantity != 1:
            calculation += f" × {subscription.quantity} Anteile"

        return JokerCreditValuePart(
            explanation=f"{name}: {calculation} = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def _get_solidarity_contribution_part(
        cls,
        member: Member,
        joker_date: datetime.date,
        subscriptions: list[Subscription],
        cache: dict,
    ) -> JokerCreditValuePart | None:
        product_type_id = get_parameter_value(
            key=ParameterKeys.JOKERS_SOLIDARITY_CONTRIBUTION_PRODUCT_TYPE, cache=cache
        )
        subscription_of_selected_type = next(
            (
                subscription
                for subscription in subscriptions
                if subscription.product.type_id == product_type_id
            ),
            None,
        )
        if subscription_of_selected_type is None:
            return None
        delivery_cycle = subscription_of_selected_type.product.type.delivery_cycle

        monthly_contribution = (
            MemberSolidarityContributionService.get_member_contribution(
                member_id=member.id, reference_date=joker_date, cache=cache
            )
        )
        if monthly_contribution == 0:
            return None

        value = DeliveryPriceCalculator.get_price_of_single_delivery_from_monthly_price(
            monthly_price=monthly_contribution,
            delivery_cycle=delivery_cycle,
            at_date=joker_date,
        )
        calculation = cls._build_monthly_to_delivery_calculation(
            monthly_amount=monthly_contribution,
            delivery_cycle=delivery_cycle,
            joker_date=joker_date,
        )

        return JokerCreditValuePart(
            explanation=f"Solidarbeitrag: {calculation} = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def _get_delivery_charge_part(
        cls, member: Member, joker_date: datetime.date, cache: dict
    ) -> JokerCreditValuePart | None:
        pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=member.id, reference_date=joker_date, cache=cache
            )
        )
        if pickup_location_id is None:
            return None

        delivery_charge = (
            PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
                pickup_location_id=pickup_location_id,
                reference_date=joker_date,
                cache=cache,
            )
        )
        if delivery_charge == 0:
            return None

        return JokerCreditValuePart(
            explanation=f"Liefergebühr Abholort: {format_currency(delivery_charge)} €",
            value=delivery_charge,
        )

    @classmethod
    def _build_monthly_to_delivery_calculation(
        cls, monthly_amount: Decimal, delivery_cycle: str, joker_date: datetime.date
    ) -> str:
        nb_weeks = DeliveryPriceCalculator.get_number_of_weeks_in_year(joker_date.year)
        calculation = (
            f"{format_currency(monthly_amount)} € monatlich × 12 ÷ {nb_weeks} Wochen"
        )
        weeks_per_delivery = (
            DeliveryPriceCalculator.get_number_of_weeks_covered_by_single_delivery(
                delivery_cycle
            )
        )
        if weeks_per_delivery != 1:
            calculation += (
                f" × {weeks_per_delivery} (Lieferung alle {weeks_per_delivery} Wochen)"
            )
        return calculation
