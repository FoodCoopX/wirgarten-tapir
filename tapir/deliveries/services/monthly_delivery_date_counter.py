import datetime

from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.utils.shortcuts import get_from_cache_or_compute, get_last_day_of_month
from tapir.wirgarten.models import ProductType


class MonthlyDeliveryDateCounter:
    @classmethod
    def count_delivery_dates_in_month(
        cls,
        member_id: str,
        product_type: ProductType,
        first_of_month: datetime.date,
        contract_start: datetime.date | None,
        contract_end: datetime.date | None,
        cache: dict,
    ) -> int:
        counts = get_from_cache_or_compute(
            cache, "monthly_delivery_date_counts", lambda: {}
        )
        return get_from_cache_or_compute(
            counts,
            (member_id, product_type.id, first_of_month, contract_start, contract_end),
            lambda: cls._compute_delivery_dates_in_month(
                member_id=member_id,
                product_type=product_type,
                first_of_month=first_of_month,
                contract_start=contract_start,
                contract_end=contract_end,
                cache=cache,
            ),
        )

    @classmethod
    def _compute_delivery_dates_in_month(
        cls,
        member_id: str,
        product_type: ProductType,
        first_of_month: datetime.date,
        contract_start: datetime.date | None,
        contract_end: datetime.date | None,
        cache: dict,
    ) -> int:
        last_of_month = get_last_day_of_month(first_of_month)
        number_of_deliveries = 0

        # start one day back so that deliveries on the first day of the month are counted
        current_date = first_of_month - datetime.timedelta(days=1)

        while current_date <= last_of_month:
            current_date = DeliveryDateCalculator.get_next_delivery_date_for_product_type(
                reference_date=current_date,
                pickup_location_id=MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                    member_id=member_id,
                    reference_date=current_date,
                    cache=cache,
                ),
                product_type=product_type,
                check_for_weeks_without_delivery=False,
                cache=cache,
            )
            if current_date is None:
                break
            if current_date > last_of_month:
                break
            if contract_start is not None and current_date < contract_start:
                continue
            if contract_end is not None and current_date > contract_end:
                continue
            number_of_deliveries += 1

        return number_of_deliveries
