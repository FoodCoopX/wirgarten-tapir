import datetime
from unittest.mock import MagicMock, patch

from tapir.pickup_locations.services.pickup_location_validator import (
    PickupLocationValidator,
)
from tapir.utils.services.tapir_cache import TapirCache
from tapir.wirgarten.models import PickupLocation, PickupLocationOpeningTime
from tapir.wirgarten.service.pickup_location_date_validation import (
    PICKUP_LOCATION_END_DATE_VALIDATION_MESSAGE,
    PICKUP_LOCATION_START_DATE_VALIDATION_MESSAGE,
)
from tapir.wirgarten.tests.factories import LocationRouteFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(TapirCache, "get_location_route_by_id", return_value=None, autospec=True)
@patch.object(TapirCache, "get_all_pickup_locations", return_value=[], autospec=True)
class TestPickupLocationValidator(TapirUnitTest):
    @staticmethod
    def _build_pickup_location(**overrides) -> PickupLocation:
        fields = {
            "name": "Test Abholort",
            "start_date": datetime.date(2026, 1, 5),
            "end_date": datetime.date(2026, 12, 27),
        }
        fields.update(overrides)
        return PickupLocationFactory.build(**fields)

    @staticmethod
    def _build_opening_time(
        open_time: datetime.time = datetime.time(14, 0),
        close_time: datetime.time = datetime.time(18, 0),
    ) -> PickupLocationOpeningTime:
        return PickupLocationOpeningTime(
            day_of_week=1, open_time=open_time, close_time=close_time
        )

    @classmethod
    def _validate(
        cls,
        pickup_location: PickupLocation,
        opening_times: list[PickupLocationOpeningTime] | None = None,
    ) -> dict[str, str]:
        return PickupLocationValidator.validate(
            pickup_location=pickup_location,
            opening_times=(
                [cls._build_opening_time()] if opening_times is None else opening_times
            ),
            cache={},
        )

    def test_validate_validData_returnsNoErrors(self, _, __):
        self.assertEqual({}, self._validate(self._build_pickup_location()))

    def test_validate_noOpeningTimes_returnsError(self, _, __):
        errors = self._validate(self._build_pickup_location(), opening_times=[])

        self.assertEqual(
            {"opening_times": PickupLocationValidator.NO_OPENING_TIMES_MESSAGE}, errors
        )

    def test_validate_closeTimeNotAfterOpenTime_returnsError(self, _, __):
        errors = self._validate(
            self._build_pickup_location(),
            opening_times=[
                self._build_opening_time(
                    open_time=datetime.time(14, 0), close_time=datetime.time(14, 0)
                )
            ],
        )

        self.assertEqual(
            {"opening_times": PickupLocationValidator.CLOSE_BEFORE_OPEN_MESSAGE}, errors
        )

    def test_validate_endDateBeforeStartDate_returnsError(self, _, __):
        errors = self._validate(
            self._build_pickup_location(
                start_date=datetime.date(2026, 12, 7),
                end_date=datetime.date(2026, 12, 6),
            )
        )

        self.assertEqual(
            PickupLocationValidator.END_BEFORE_START_MESSAGE, errors["end_date"]
        )

    def test_validate_startDateNotOnMonday_returnsError(self, _, __):
        errors = self._validate(
            self._build_pickup_location(start_date=datetime.date(2026, 1, 6))
        )

        self.assertEqual(
            {"start_date": PICKUP_LOCATION_START_DATE_VALIDATION_MESSAGE}, errors
        )

    def test_validate_endDateNotOnSunday_returnsError(self, _, __):
        errors = self._validate(
            self._build_pickup_location(end_date=datetime.date(2026, 12, 26))
        )

        self.assertEqual(
            {"end_date": PICKUP_LOCATION_END_DATE_VALIDATION_MESSAGE}, errors
        )

    def test_validate_noDates_returnsNoErrors(self, _, __):
        errors = self._validate(
            self._build_pickup_location(start_date=None, end_date=None)
        )

        self.assertEqual({}, errors)

    def test_validate_existingLocationRoute_returnsNoErrors(
        self, _, mock_get_location_route_by_id: MagicMock
    ):
        location_route = LocationRouteFactory.build()
        mock_get_location_route_by_id.return_value = location_route

        errors = self._validate(
            self._build_pickup_location(location_route_id=location_route.id)
        )

        self.assertEqual({}, errors)
        mock_get_location_route_by_id.assert_called_once_with(
            cache={}, location_route_id=location_route.id
        )

    def test_validate_unknownLocationRoute_returnsError(self, _, __):
        errors = self._validate(
            self._build_pickup_location(location_route_id="unknown")
        )

        self.assertEqual(
            {
                "location_route_id": PickupLocationValidator.UNKNOWN_LOCATION_ROUTE_MESSAGE
            },
            errors,
        )

    def test_validate_otherLocationWithSameName_returnsError(
        self, mock_get_all_pickup_locations: MagicMock, _
    ):
        mock_get_all_pickup_locations.return_value = [
            PickupLocationFactory.build(name="Test Abholort")
        ]

        errors = self._validate(self._build_pickup_location())

        self.assertEqual(
            {"name": PickupLocationValidator.DUPLICATE_NAME_MESSAGE}, errors
        )

    def test_validate_otherLocationWithSameCoordinates_returnsNoErrors(
        self, mock_get_all_pickup_locations: MagicMock, _
    ):
        pickup_location = self._build_pickup_location()
        mock_get_all_pickup_locations.return_value = [
            PickupLocationFactory.build(
                name="Anderer Abholort",
                latitude=pickup_location.latitude,
                longitude=pickup_location.longitude,
            )
        ]

        errors = self._validate(pickup_location)

        self.assertEqual({}, errors)

    def test_validate_sameLocationWithSameName_returnsNoErrors(
        self, mock_get_all_pickup_locations: MagicMock, _
    ):
        pickup_location = self._build_pickup_location()
        mock_get_all_pickup_locations.return_value = [pickup_location]

        errors = self._validate(pickup_location)

        self.assertEqual({}, errors)

    def test_validate_normalLocationWithoutCoordinates_returnsErrors(self, _, __):
        errors = self._validate(
            self._build_pickup_location(latitude=None, longitude=None)
        )

        self.assertEqual(
            {
                "latitude": "Koordinaten sind für Abholorte erforderlich.",
                "longitude": "Koordinaten sind für Abholorte erforderlich.",
            },
            errors,
        )

    def test_validate_homeDeliveryWithoutCoordinates_returnsNoErrors(self, _, __):
        errors = self._validate(
            self._build_pickup_location(
                is_home_delivery=True, latitude=None, longitude=None
            )
        )

        self.assertEqual({}, errors)
