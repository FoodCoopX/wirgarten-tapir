from django.core.exceptions import ValidationError

from tapir.deliveries.models import CustomCycleDeliveryWeeks
from tapir.deliveries.services.custom_cycle_delivery_date_calculator import (
    CustomCycleDeliveryDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.utils.shortcuts import get_first_of_next_month
from tapir.wirgarten.models import ProductType, GrowingPeriod
from tapir.wirgarten.utils import get_today, format_date


class ProductTypeChangeValidator:
    @classmethod
    def validate_custom_cycle_changes(
        cls, product_type: ProductType, extended_data: dict, cache: dict
    ):
        week_objects = cls.build_week_objects(
            extended_data=extended_data, product_type=product_type
        )
        cls.validate_weeks_are_contained_in_growing_periods(week_objects)

        cls.validate_no_changes_in_past_deliveries(week_objects, product_type, cache)

    @classmethod
    def validate_no_changes_in_past_deliveries(
        cls,
        week_objects: list[CustomCycleDeliveryWeeks],
        product_type: ProductType,
        cache: dict,
    ):
        all_weeks_before_changes = (
            TapirCache.get_all_delivered_week_objects_for_custom_cycle(
                product_type=product_type, cache=cache
            )
        )
        all_dates_before_changes = [
            CustomCycleDeliveryDateCalculator.get_date_from_week_object(
                week_object=week_object
            )
            for week_object in all_weeks_before_changes
        ]
        date_limit = get_first_of_next_month(get_today(cache=cache))
        past_dates_before_changes = {
            date for date in all_dates_before_changes if date < date_limit
        }

        dates_after_changes = {
            CustomCycleDeliveryDateCalculator.get_date_from_week_object(
                week_object=week_object
            )
            for week_object in week_objects
        }

        if not past_dates_before_changes.issubset(dates_after_changes):
            raise ValidationError(
                "Folgenden Wochen sind in entweder in der Vergangenheit oder im aktuellem Monat und können nicht mehr geändert werden"
            )

    @classmethod
    def validate_weeks_are_contained_in_growing_periods(
        cls, week_objects: list[CustomCycleDeliveryWeeks]
    ):
        for week_object in week_objects:
            date = CustomCycleDeliveryDateCalculator.get_date_from_week_object(
                week_object=week_object
            )
            growing_period = week_object.growing_period
            date_is_within_growing_period = (
                growing_period.start_date <= date <= growing_period.end_date
            )
            if not date_is_within_growing_period:
                raise ValidationError(
                    f"KW {week_object.calendar_week} ist nicht in der Vertragsperiode {format_date(growing_period.start_date)} - {format_date(growing_period.end_date)} enthalten"
                )

    @classmethod
    def build_week_objects(cls, extended_data: dict, product_type: ProductType):
        week_objects: list[CustomCycleDeliveryWeeks] = []
        growing_periods = {
            growing_period.id: growing_period
            for growing_period in GrowingPeriod.objects.filter(
                id__in=extended_data["custom_cycle_delivery_weeks"].keys()
            )
        }

        for growing_period_id, weeks in extended_data[
            "custom_cycle_delivery_weeks"
        ].items():
            for week in weeks:
                week_objects.append(
                    CustomCycleDeliveryWeeks(
                        product_type=product_type,
                        growing_period=growing_periods[growing_period_id],
                        calendar_week=week,
                    )
                )
        return week_objects
