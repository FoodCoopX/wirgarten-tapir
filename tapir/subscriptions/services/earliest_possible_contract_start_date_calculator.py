import datetime

from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.deliveries.services.delivery_date_calculator import DeliveryDateCalculator


class EarliestPossibleContractStartDateCalculator:
    @classmethod
    def get_earliest_possible_contract_start_date(
        cls,
        reference_date: datetime.date,
        pickup_location_id,
        cache: dict,
    ) -> datetime.date:
        next_delivery_date = DeliveryDateCalculator.get_next_delivery_date_any_product(
            reference_date=reference_date, pickup_location_id=pickup_location_id
        )
        changes_possible_until_date = DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
            reference_date=next_delivery_date, cache=cache
        )

        if changes_possible_until_date > reference_date:
            return reference_date

        return changes_possible_until_date + datetime.timedelta(days=7)
