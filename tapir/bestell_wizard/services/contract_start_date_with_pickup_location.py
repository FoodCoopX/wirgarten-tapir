import datetime

from django.core.exceptions import ValidationError

from tapir.wirgarten.models import GrowingPeriod, PickupLocation


class ContractStartDateWithPickupLocation:
    @classmethod
    def get_contract_start_date_considering_pickup_location(
        cls,
        contract_start_date: datetime.date,
        pickup_location: PickupLocation,
        growing_period: GrowingPeriod,
    ):
        earliest_start_date = (
            pickup_location.start_date
            if pickup_location.start_date is not None
            else contract_start_date
        )
        effective_contract_start_date = max(contract_start_date, earliest_start_date)

        if effective_contract_start_date > growing_period.end_date:
            raise ValidationError(
                "Die ausgewählte Verteilstation ist erst nach dem Ende der "
                "Vertragsperiode verfügbar. Bitte wähle eine passende Vertragsperiode."
            )

        return effective_contract_start_date

    @classmethod
    def resolve_contract_start_date_for_pickup_location(
        cls,
        pickup_location_ids: list[str],
        order,
        contract_start_date: datetime.date,
        growing_period: GrowingPeriod,
        cache: dict,
    ) -> tuple[PickupLocation | None, datetime.date]:
        from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
            BestellWizardOrderValidator,
        )

        def get_first_pickup_location_with_enough_capacity(
            reference_contract_start_date: datetime.date,
        ) -> PickupLocation | None:
            return BestellWizardOrderValidator.get_first_pickup_location_with_enough_capacity(
                pickup_location_ids=pickup_location_ids,
                order=order,
                member=None,
                contract_start_date=reference_contract_start_date,
                cache=cache,
            )

        pickup_location = get_first_pickup_location_with_enough_capacity(
            contract_start_date
        )
        while pickup_location is not None:
            adjusted_contract_start_date = (
                cls.get_contract_start_date_considering_pickup_location(
                    contract_start_date=contract_start_date,
                    pickup_location=pickup_location,
                    growing_period=growing_period,
                )
            )
            if adjusted_contract_start_date == contract_start_date:
                return pickup_location, contract_start_date
            contract_start_date = adjusted_contract_start_date
            pickup_location = get_first_pickup_location_with_enough_capacity(
                contract_start_date
            )

        # No pickup location has enough capacity at contract_start_date (the last
        # date checked). The caller must not use this date to fulfill the order;
        # it passes it to the validator, which re-checks and rejects the order.
        return None, contract_start_date
