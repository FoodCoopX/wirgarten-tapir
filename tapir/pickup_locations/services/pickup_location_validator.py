from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import PickupLocation, PickupLocationOpeningTime
from tapir.wirgarten.service.pickup_location_date_validation import (
    PickupLocationDateValidator,
)


class PickupLocationValidator:
    NO_OPENING_TIMES_MESSAGE = "Mindestens ein Abholtag muss eingetragen werden."
    CLOSE_BEFORE_OPEN_MESSAGE = "Das Ende muss nach dem Beginn liegen."
    END_BEFORE_START_MESSAGE = "Ende darf nicht vor Beginn liegen."
    UNKNOWN_LOCATION_ROUTE_MESSAGE = "Unbekannte Ausfahrrunde."
    DUPLICATE_NAME_MESSAGE = "Es gibt bereits einen Abholort mit diesem Namen."
    COORDINATES_REQUIRED_MESSAGE = "Koordinaten sind für Abholorte erforderlich."

    @classmethod
    def validate(
        cls,
        pickup_location: PickupLocation,
        opening_times: list[PickupLocationOpeningTime],
        cache: dict,
    ) -> dict[str, str]:
        errors = {}

        if len(opening_times) == 0:
            errors["opening_times"] = cls.NO_OPENING_TIMES_MESSAGE
        elif any(
            opening_time.open_time >= opening_time.close_time
            for opening_time in opening_times
        ):
            errors["opening_times"] = cls.CLOSE_BEFORE_OPEN_MESSAGE

        start_date = pickup_location.start_date
        end_date = pickup_location.end_date
        if start_date and end_date and end_date < start_date:
            errors["end_date"] = cls.END_BEFORE_START_MESSAGE

        for field_name, message in PickupLocationDateValidator.validate(
            start_date=start_date, end_date=end_date
        ).items():
            errors.setdefault(field_name, message)

        if (
            pickup_location.location_route_id is not None
            and TapirCache.get_location_route_by_id(
                cache=cache, location_route_id=pickup_location.location_route_id
            )
            is None
        ):
            errors["location_route_id"] = cls.UNKNOWN_LOCATION_ROUTE_MESSAGE

        if any(
            other.name == pickup_location.name and other.id != pickup_location.id
            for other in TapirCache.get_all_pickup_locations(cache=cache)
        ):
            errors["name"] = cls.DUPLICATE_NAME_MESSAGE

        if not pickup_location.is_home_delivery:
            for field_name in ["latitude", "longitude"]:
                if getattr(pickup_location, field_name) is None:
                    errors[field_name] = cls.COORDINATES_REQUIRED_MESSAGE

        return errors
