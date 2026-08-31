import datetime

from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.utils import get_today


class PickupLocationReferenceDateService:
    @staticmethod
    def get_reference_date(cache: dict) -> datetime.date:
        return ContractStartDateCalculator.get_next_contract_start_date(
            reference_date=get_today(cache=cache),
            apply_buffer_time=False,
            cache=cache,
        )
