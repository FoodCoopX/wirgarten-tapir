import datetime
from dataclasses import dataclass

from tapir.bestell_wizard.services.products_without_free_capacity_provider import (
    ProductsWithoutFreeCapacityProvider,
)
from tapir.pickup_locations.services.public_pickup_locations_provider import (
    PublicPickupLocationProvider,
)
from tapir.solidarity_contribution.services.solidarity_validator import (
    SolidarityValidator,
)
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import GrowingPeriod, PickupLocation, ProductType


@dataclass
class GrowingPeriodChoice:
    growing_period: GrowingPeriod
    contract_start_date: datetime.date
    product_types: list[ProductType]
    product_type_ids_that_are_already_at_capacity: list[str]
    product_ids_that_are_already_at_capacity: list[str]
    pickup_locations: list[PickupLocation]
    solidarity_contribution_minimum: float


class GrowingPeriodChoiceBuilder:
    @classmethod
    def build(cls, growing_period: GrowingPeriod, cache: dict) -> GrowingPeriodChoice:
        contract_start_date = (
            ContractStartDateCalculator.get_next_contract_start_date_in_growing_period(
                growing_period=growing_period, apply_buffer_time=True, cache=cache
            )
        )
        product_ids_without_free_capacity = (
            ProductsWithoutFreeCapacityProvider.get_product_ids(
                cache=cache, contract_start_date=contract_start_date
            )
        )

        return GrowingPeriodChoice(
            growing_period=growing_period,
            contract_start_date=contract_start_date,
            product_types=cls._get_product_types(
                growing_period=growing_period, cache=cache
            ),
            product_type_ids_that_are_already_at_capacity=ProductsWithoutFreeCapacityProvider.get_product_type_ids(
                cache=cache,
                product_ids_without_free_capacity=product_ids_without_free_capacity,
                contract_start_date=contract_start_date,
            ),
            product_ids_that_are_already_at_capacity=product_ids_without_free_capacity,
            pickup_locations=list(
                PublicPickupLocationProvider.get_pickup_locations_available_for_members(
                    cache=cache, reference_date=contract_start_date
                )
            ),
            solidarity_contribution_minimum=SolidarityValidator.get_solidarity_contribution_minimum(
                reference_date=contract_start_date, cache=cache
            ),
        )

    @classmethod
    def _get_product_types(
        cls, growing_period: GrowingPeriod, cache: dict
    ) -> list[ProductType]:
        product_types = [
            product_type
            for product_type in TapirCache.get_all_product_types(cache)
            if TapirCache.get_product_type_capacity_at_date(
                cache=cache,
                reference_date=growing_period.start_date,
                product_type=product_type,
            )
            is not None
        ]
        product_types.sort(key=lambda product_type: product_type.order_in_bestellwizard)
        return product_types
