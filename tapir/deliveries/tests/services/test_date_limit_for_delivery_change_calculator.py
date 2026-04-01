import datetime

from tapir.configuration.models import TapirParameter
from tapir.deliveries.services.date_limit_for_delivery_change_calculator import (
    DateLimitForDeliveryChangeCalculator,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDateLimitForDeliveryChanceCalculator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_calculateDateLimitForDeliveryChanges_default_returnsCorrectDate(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        ).update(
            value="0"
        )  # changes must be done before monday EOD
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(
            value="2"
        )  # delivery day is wednesday

        self.assertEqual(
            datetime.date(year=2025, month=3, day=3),
            DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
                datetime.date(year=2025, month=3, day=7), cache={}
            ),
        )

    def test_calculateDateLimitForDeliveryChanges_weekdayForChangesIsInTheWeekBeforeDeliveryDay_returnsCorrectDate(
        self,
    ):
        TapirParameter.objects.filter(
            key=ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        ).update(
            value="5"
        )  # changes must be done before saturday EOD
        TapirParameter.objects.filter(key=ParameterKeys.DELIVERY_DAY).update(
            value="2"
        )  # delivery day is wednesday

        self.assertEqual(
            datetime.date(year=2025, month=3, day=1),
            DateLimitForDeliveryChangeCalculator.calculate_date_limit_for_delivery_changes_in_week(
                datetime.date(year=2025, month=3, day=7), cache={}
            ),
        )
