import datetime
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError

from tapir.bestell_wizard.services.bestell_wizard_order_validator import (
    BestellWizardOrderValidator,
)
from tapir.bestell_wizard.services.contract_start_date_with_pickup_location import (
    ContractStartDateWithPickupLocation,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestContractStartDateWithPickupLocation(TapirUnitTest):
    def build_pickup_location(self, start_date):
        pickup_location = Mock()
        pickup_location.start_date = start_date
        return pickup_location

    def test_getContractStartDateConsideringPickupLocation_noStartDate_returnsContractStartDate(
        self,
    ):
        contract_start_date = datetime.date(year=2024, month=6, day=10)
        pickup_location = self.build_pickup_location(start_date=None)
        growing_period = Mock()
        growing_period.end_date = datetime.date(year=2025, month=2, day=28)

        result = ContractStartDateWithPickupLocation.get_contract_start_date_considering_pickup_location(
            contract_start_date=contract_start_date,
            pickup_location=pickup_location,
            growing_period=growing_period,
        )

        self.assertEqual(contract_start_date, result)

    def test_getContractStartDateConsideringPickupLocation_startDateBeforeContractStart_returnsContractStartDate(
        self,
    ):
        contract_start_date = datetime.date(year=2024, month=6, day=10)
        pickup_location = self.build_pickup_location(
            start_date=datetime.date(year=2024, month=5, day=1)
        )
        growing_period = Mock()
        growing_period.end_date = datetime.date(year=2025, month=2, day=28)

        result = ContractStartDateWithPickupLocation.get_contract_start_date_considering_pickup_location(
            contract_start_date=contract_start_date,
            pickup_location=pickup_location,
            growing_period=growing_period,
        )

        self.assertEqual(contract_start_date, result)

    def test_getContractStartDateConsideringPickupLocation_startDateWithinGrowingPeriod_returnsStartDate(
        self,
    ):
        contract_start_date = datetime.date(year=2024, month=6, day=10)
        start_date = datetime.date(year=2024, month=8, day=1)
        pickup_location = self.build_pickup_location(start_date=start_date)
        growing_period = Mock()
        growing_period.end_date = datetime.date(year=2025, month=2, day=28)

        result = ContractStartDateWithPickupLocation.get_contract_start_date_considering_pickup_location(
            contract_start_date=contract_start_date,
            pickup_location=pickup_location,
            growing_period=growing_period,
        )

        self.assertEqual(start_date, result)

    def test_getContractStartDateConsideringPickupLocation_startDateAfterGrowingPeriodEnd_raisesValidationError(
        self,
    ):
        contract_start_date = datetime.date(year=2024, month=6, day=10)
        pickup_location = self.build_pickup_location(
            start_date=datetime.date(year=2025, month=6, day=1)
        )
        growing_period = Mock()
        growing_period.end_date = datetime.date(year=2025, month=2, day=28)

        with self.assertRaises(ValidationError):
            ContractStartDateWithPickupLocation.get_contract_start_date_considering_pickup_location(
                contract_start_date=contract_start_date,
                pickup_location=pickup_location,
                growing_period=growing_period,
            )

    @patch.object(
        BestellWizardOrderValidator,
        "get_first_pickup_location_with_enough_capacity",
        autospec=True,
    )
    def test_resolveContractStartDateForPickupLocation_noLocationWithCapacity_returnsNoneAndContractStartDate(
        self, mock_get_first_pickup_location_with_enough_capacity: Mock
    ):
        contract_start_date = datetime.date(year=2024, month=6, day=10)
        mock_get_first_pickup_location_with_enough_capacity.return_value = None
        growing_period = Mock()
        growing_period.end_date = datetime.date(year=2025, month=2, day=28)

        result_location, result_date = (
            ContractStartDateWithPickupLocation.resolve_contract_start_date_for_pickup_location(
                pickup_location_ids=["a"],
                order={},
                contract_start_date=contract_start_date,
                growing_period=growing_period,
                cache={},
            )
        )

        self.assertIsNone(result_location)
        self.assertEqual(contract_start_date, result_date)

    @patch.object(
        BestellWizardOrderValidator,
        "get_first_pickup_location_with_enough_capacity",
        autospec=True,
    )
    def test_resolveContractStartDateForPickupLocation_locationOpensBeforeContractStart_returnsLocationAndContractStartDate(
        self, mock_get_first_pickup_location_with_enough_capacity: Mock
    ):
        contract_start_date = datetime.date(year=2024, month=6, day=10)
        pickup_location = self.build_pickup_location(
            start_date=datetime.date(year=2024, month=5, day=1)
        )
        mock_get_first_pickup_location_with_enough_capacity.return_value = (
            pickup_location
        )
        growing_period = Mock()
        growing_period.end_date = datetime.date(year=2025, month=2, day=28)

        result_location, result_date = (
            ContractStartDateWithPickupLocation.resolve_contract_start_date_for_pickup_location(
                pickup_location_ids=["a"],
                order={},
                contract_start_date=contract_start_date,
                growing_period=growing_period,
                cache={},
            )
        )

        self.assertEqual(pickup_location, result_location)
        self.assertEqual(contract_start_date, result_date)

    @patch.object(
        BestellWizardOrderValidator,
        "get_first_pickup_location_with_enough_capacity",
        autospec=True,
    )
    def test_resolveContractStartDateForPickupLocation_locationOpensLaterWithinPeriod_returnsLocationAndPushedDate(
        self, mock_get_first_pickup_location_with_enough_capacity: Mock
    ):
        contract_start_date = datetime.date(year=2024, month=6, day=10)
        start_date = datetime.date(year=2024, month=8, day=1)
        pickup_location = self.build_pickup_location(start_date=start_date)
        mock_get_first_pickup_location_with_enough_capacity.return_value = (
            pickup_location
        )
        growing_period = Mock()
        growing_period.end_date = datetime.date(year=2025, month=2, day=28)

        result_location, result_date = (
            ContractStartDateWithPickupLocation.resolve_contract_start_date_for_pickup_location(
                pickup_location_ids=["a"],
                order={},
                contract_start_date=contract_start_date,
                growing_period=growing_period,
                cache={},
            )
        )

        self.assertEqual(pickup_location, result_location)
        self.assertEqual(start_date, result_date)
        self.assertEqual(
            2, mock_get_first_pickup_location_with_enough_capacity.call_count
        )

    @patch.object(
        BestellWizardOrderValidator,
        "get_first_pickup_location_with_enough_capacity",
        autospec=True,
    )
    def test_resolveContractStartDateForPickupLocation_locationLosesCapacityAfterPush_picksNextLocationAtAdjustedDate(
        self, mock_get_first_pickup_location_with_enough_capacity: Mock
    ):
        contract_start_date = datetime.date(year=2024, month=6, day=10)
        location_a = self.build_pickup_location(
            start_date=datetime.date(year=2024, month=8, day=1)
        )
        location_b = self.build_pickup_location(
            start_date=datetime.date(year=2024, month=9, day=1)
        )
        growing_period = Mock()
        growing_period.end_date = datetime.date(year=2025, month=2, day=28)

        def pick(**kwargs):
            reference_date = kwargs["contract_start_date"]
            if reference_date < datetime.date(year=2024, month=8, day=1):
                return location_a
            return location_b

        mock_get_first_pickup_location_with_enough_capacity.side_effect = pick

        result_location, result_date = (
            ContractStartDateWithPickupLocation.resolve_contract_start_date_for_pickup_location(
                pickup_location_ids=["a", "b"],
                order={},
                contract_start_date=contract_start_date,
                growing_period=growing_period,
                cache={},
            )
        )

        self.assertEqual(location_b, result_location)
        self.assertEqual(datetime.date(year=2024, month=9, day=1), result_date)

    @patch.object(
        BestellWizardOrderValidator,
        "get_first_pickup_location_with_enough_capacity",
        autospec=True,
    )
    def test_resolveContractStartDateForPickupLocation_locationBeyondGrowingPeriod_raisesValidationError(
        self, mock_get_first_pickup_location_with_enough_capacity: Mock
    ):
        contract_start_date = datetime.date(year=2024, month=6, day=10)
        pickup_location = self.build_pickup_location(
            start_date=datetime.date(year=2025, month=6, day=1)
        )
        mock_get_first_pickup_location_with_enough_capacity.return_value = (
            pickup_location
        )
        growing_period = Mock()
        growing_period.end_date = datetime.date(year=2025, month=2, day=28)

        with self.assertRaises(ValidationError):
            ContractStartDateWithPickupLocation.resolve_contract_start_date_for_pickup_location(
                pickup_location_ids=["a"],
                order={},
                contract_start_date=contract_start_date,
                growing_period=growing_period,
                cache={},
            )
