import datetime
from decimal import Decimal

from django.utils.formats import date_format

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.services.member_specific_delivery_day_calculator import (
    MemberSpecificDeliveryDayCalculator,
)
from tapir.deliveries.services.monthly_delivery_date_counter import (
    MonthlyDeliveryDateCounter,
)
from tapir.deliveries.services.partial_month_calculation_mode_decider import (
    PartialMonthCalculationModeDecider,
)
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
from tapir.subscriptions.services.subscription_calculation_name_builder import (
    SubscriptionCalculationNameBuilder,
)
from tapir.subscriptions.services.subscription_price_calculator import (
    SubscriptionPriceCalculator,
)
from tapir.utils.dataclasses import CalculationPart
from tapir.utils.services.calculation_explanation_builder import (
    CalculationExplanationBuilder,
)
from tapir.utils.shortcuts import get_monday
from tapir.wirgarten.constants import CUSTOM_CYCLE
from tapir.wirgarten.models import Member, Subscription, ProductType
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.service.get_next_delivery_date import get_next_delivery_date
from tapir.wirgarten.service.products import get_product_price
from tapir.wirgarten.utils import format_currency


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
    def get_total_value(cls, parts: list[CalculationPart]) -> Decimal:
        # A negative solidarity contribution may lower the credit, but never below 0.
        return max(sum((part.value for part in parts), start=Decimal(0)), Decimal(0))

    @classmethod
    def build_explanation(cls, parts: list[CalculationPart]) -> str:
        return "\n".join(
            CalculationExplanationBuilder.build_credit_lines(
                calculation_parts=parts, total=cls.get_total_value(parts)
            )
        )

    @classmethod
    def get_actual_delivery_date(
        cls, member_id: str, joker_date: datetime.date, cache: dict
    ) -> datetime.date:
        return MemberSpecificDeliveryDayCalculator.get_specific_delivery_date(
            member_id=member_id,
            delivery_date=get_next_delivery_date(get_monday(joker_date), cache=cache),
            cache=cache,
        )

    @classmethod
    def get_joker_credit_value_parts(
        cls, member: Member, joker_date: datetime.date, cache: dict
    ) -> list[CalculationPart]:
        delivery_date = cls.get_actual_delivery_date(
            member_id=member.id, joker_date=joker_date, cache=cache
        )
        subscriptions = list(
            DeliveryPriceCalculator.get_subscriptions_that_get_delivered_in_week(
                member=member, reference_date=delivery_date, cache=cache
            )
            .filter(product__type__is_affected_by_jokers=True)
            .order_by("product__type__name", "product__name")
        )
        parts = [
            cls._get_subscription_part(
                subscription=subscription, delivery_date=delivery_date, cache=cache
            )
            for subscription in subscriptions
        ]
        solidarity_part = cls._get_solidarity_contribution_part(
            member=member,
            delivery_date=delivery_date,
            subscriptions=subscriptions,
            cache=cache,
        )
        if solidarity_part is not None:
            parts.append(solidarity_part)

        delivery_charge_part = cls._get_delivery_charge_part(
            member=member, delivery_date=delivery_date, cache=cache
        )
        if delivery_charge_part is not None:
            parts.append(delivery_charge_part)

        return parts

    @classmethod
    def _get_subscription_part(
        cls, subscription: Subscription, delivery_date: datetime.date, cache: dict
    ) -> CalculationPart:
        name = f"{subscription.product.type.name} {subscription.product.name}"
        delivery_cycle = subscription.product.type.delivery_cycle

        if delivery_cycle != CUSTOM_CYCLE[0] and (
            PartialMonthCalculationModeDecider.is_proportional_mode_active(
                first_of_month=delivery_date.replace(day=1), cache=cache
            )
        ):
            return cls._build_proportional_part(
                name=SubscriptionCalculationNameBuilder.build_name(
                    subscription=subscription
                ),
                monthly_amount=SubscriptionPriceCalculator.get_monthly_price(
                    subscription=subscription,
                    reference_date=delivery_date,
                    cache=cache,
                ),
                member_id=subscription.member_id,
                product_type=subscription.product.type,
                delivery_date=delivery_date,
                cache=cache,
            )

        value = DeliveryPriceCalculator.get_price_of_single_delivery_for_subscription(
            subscription=subscription, at_date=delivery_date, cache=cache
        )
        quantity_factor = ""
        if subscription.price_override is not None:
            name += " (Sonderpreis)"
            price = subscription.price_override
        else:
            price = get_product_price(
                product=subscription.product, reference_date=delivery_date, cache=cache
            ).price
            if subscription.quantity != 1:
                quantity_factor = f" × {subscription.quantity} Anteile"

        if delivery_cycle == CUSTOM_CYCLE[0]:
            explanation = f"{name}: Preis pro Lieferung {format_currency(price)} €"
            if quantity_factor:
                explanation += f"{quantity_factor} = {format_currency(value)} €"
            return CalculationPart(explanation=explanation, value=value)

        calculation = cls._build_monthly_to_delivery_calculation(
            monthly_amount=price,
            delivery_cycle=delivery_cycle,
            delivery_date=delivery_date,
        )
        calculation += quantity_factor

        return CalculationPart(
            explanation=f"{name}: {calculation} = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def _get_solidarity_contribution_part(
        cls,
        member: Member,
        delivery_date: datetime.date,
        subscriptions: list[Subscription],
        cache: dict,
    ) -> CalculationPart | None:
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
                member_id=member.id, reference_date=delivery_date, cache=cache
            )
        )
        if monthly_contribution == 0:
            return None

        if PartialMonthCalculationModeDecider.is_proportional_mode_active(
            first_of_month=delivery_date.replace(day=1), cache=cache
        ):
            return cls._build_proportional_part(
                name="Solidarbeitrag",
                monthly_amount=monthly_contribution,
                member_id=member.id,
                product_type=subscription_of_selected_type.product.type,
                delivery_date=delivery_date,
                cache=cache,
            )

        value = DeliveryPriceCalculator.get_price_of_single_delivery_from_monthly_price(
            monthly_price=monthly_contribution,
            delivery_cycle=delivery_cycle,
            at_date=delivery_date,
        )
        calculation = cls._build_monthly_to_delivery_calculation(
            monthly_amount=monthly_contribution,
            delivery_cycle=delivery_cycle,
            delivery_date=delivery_date,
        )

        return CalculationPart(
            explanation=f"Solidarbeitrag: {calculation} = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def _get_delivery_charge_part(
        cls, member: Member, delivery_date: datetime.date, cache: dict
    ) -> CalculationPart | None:
        pickup_location_id = (
            MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=member.id, reference_date=delivery_date, cache=cache
            )
        )
        if pickup_location_id is None:
            return None

        delivery_charge = (
            PickupLocationDeliveryChargeService.get_delivery_charge_at_date(
                pickup_location_id=pickup_location_id,
                reference_date=delivery_date,
                cache=cache,
            )
        )
        if delivery_charge == 0:
            return None

        return CalculationPart(
            explanation=f"Liefergebühr Abholort: {format_currency(delivery_charge)} €",
            value=delivery_charge,
        )

    @classmethod
    def _build_monthly_to_delivery_calculation(
        cls, monthly_amount: Decimal, delivery_cycle: str, delivery_date: datetime.date
    ) -> str:
        nb_weeks = DeliveryPriceCalculator.get_number_of_weeks_in_year(
            delivery_date.year
        )
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

    @classmethod
    def _build_proportional_part(
        cls,
        name: str,
        monthly_amount: Decimal,
        member_id: str,
        product_type: ProductType,
        delivery_date: datetime.date,
        cache: dict,
    ) -> CalculationPart:
        number_of_dates = MonthlyDeliveryDateCounter.count_delivery_dates_in_month(
            member_id=member_id,
            product_type=product_type,
            first_of_month=delivery_date.replace(day=1),
            contract_start=None,
            contract_end=None,
            cache=cache,
        )
        value = Decimal(0) if number_of_dates == 0 else monthly_amount / number_of_dates
        calculation = cls._build_proportional_calculation(
            monthly_amount=monthly_amount,
            number_of_dates=number_of_dates,
            month=delivery_date,
        )
        return CalculationPart(
            explanation=f"{name}: {calculation} = {format_currency(value)} €",
            value=value,
        )

    @classmethod
    def _build_proportional_calculation(
        cls, monthly_amount: Decimal, number_of_dates: int, month: datetime.date
    ) -> str:
        dates_label = "Liefertermin" if number_of_dates == 1 else "Liefertermine"
        return f"{format_currency(monthly_amount)} € monatlich ÷ {number_of_dates} {dates_label} im {date_format(month, "F")}"
