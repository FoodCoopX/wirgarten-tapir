import datetime

from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.utils.shortcuts import (
    get_from_cache_or_compute,
    get_last_day_of_month,
    get_monday,
)
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

        # One delivery per week at most, at the pickup location valid on that week's Monday.
        # The search starts on the Sunday before, so that a delivery on Monday is found;
        # a result on or after next Monday means the week isn't delivered (e.g. biweekly).
        for monday, pickup_location_id in cls._get_weeks_of_month_with_pickup_location(
            member_id=member_id, first_of_month=first_of_month, cache=cache
        ):
            next_monday = monday + datetime.timedelta(days=7)
            delivery_date = (
                DeliveryDateCalculator.get_next_delivery_date_for_product_type(
                    reference_date=monday - datetime.timedelta(days=1),
                    pickup_location_id=pickup_location_id,
                    product_type=product_type,
                    check_for_weeks_without_delivery=False,
                    cache=cache,
                )
            )
            if delivery_date is None:
                break
            if delivery_date >= next_monday:
                continue
            if not first_of_month <= delivery_date <= last_of_month:
                continue
            if contract_start is not None and delivery_date < contract_start:
                continue
            if contract_end is not None and delivery_date > contract_end:
                continue
            number_of_deliveries += 1

        return number_of_deliveries

    @classmethod
    def _get_weeks_of_month_with_pickup_location(
        cls, member_id: str, first_of_month: datetime.date, cache: dict
    ) -> list[tuple[datetime.date, str | None]]:
        last_of_month = get_last_day_of_month(first_of_month)
        mondays = []
        monday = get_monday(first_of_month)
        while monday <= last_of_month:
            mondays.append(monday)
            monday += datetime.timedelta(days=7)

        # Weeks outside the contract may have no location (e.g. before the first one):
        # they take the nearest known location of the month, so that they still count
        # on the right weekday.
        pickup_location_ids = [
            MemberPickupLocationGetter.get_member_pickup_location_id_from_cache(
                member_id=member_id, reference_date=monday, cache=cache
            )
            for monday in mondays
        ]
        known_ids = [
            pickup_location_id
            for pickup_location_id in pickup_location_ids
            if pickup_location_id is not None
        ]
        if len(known_ids) == 0:
            return list(zip(mondays, pickup_location_ids))

        previous_id = known_ids[0]
        weeks = []
        for monday, pickup_location_id in zip(mondays, pickup_location_ids):
            if pickup_location_id is not None:
                previous_id = pickup_location_id
            weeks.append((monday, previous_id))
        return weeks
