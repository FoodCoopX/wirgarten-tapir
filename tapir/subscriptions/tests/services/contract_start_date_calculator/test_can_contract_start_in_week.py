import datetime

from tapir.configuration.models import TapirParameter
from tapir.subscriptions.services.contract_start_date_calculator import (
    ContractStartDateCalculator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestCanContractStartOnDate(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        ).update(
            value=6
        )  # Sunday
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(
            value=2
        )  # Wednesday

    def test_canContractStartOnDate_noBuffer_dateLimitIsThePickupLocationChangeLimit(
        self,
    ):
        mock_timezone(self, now=datetime.datetime(year=2025, month=7, day=15))
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_BUFFER_TIME_BEFORE_START
        ).update(value=0)

        self.assertFalse(
            ContractStartDateCalculator.can_contract_start_in_week(
                reference_date=datetime.date(year=2025, month=7, day=20), cache={}
            )
        )
        self.assertTrue(
            ContractStartDateCalculator.can_contract_start_in_week(
                reference_date=datetime.date(year=2025, month=7, day=21), cache={}
            )
        )

    def test_canContractStartOnDate_withBuffer_dateLimitIsThePickupLocationChangeLimit(
        self,
    ):
        mock_timezone(self, now=datetime.datetime(year=2025, month=7, day=15))
        # Today is Tuesday, Delivery is on Wednesday: contracts can start from Thursday
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_BUFFER_TIME_BEFORE_START
        ).update(value=7)

        self.assertFalse(
            ContractStartDateCalculator.can_contract_start_in_week(
                reference_date=datetime.date(year=2025, month=7, day=27), cache={}
            )
        )
        self.assertTrue(
            ContractStartDateCalculator.can_contract_start_in_week(
                reference_date=datetime.date(year=2025, month=7, day=28), cache={}
            )
        )
