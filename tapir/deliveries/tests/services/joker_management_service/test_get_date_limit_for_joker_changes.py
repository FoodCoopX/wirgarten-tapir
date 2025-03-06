import datetime

from tapir.configuration.models import TapirParameter
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.parameters import Parameter, ParameterDefinitions
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestJokerManagementServiceGetDateLimitForJokerChanges(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()

    def test_getDateLimitForJokerChanges_default_returnsCorrectDate(self):
        TapirParameter.objects.filter(
            key=Parameter.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        ).update(
            value="0"
        )  # changes must be done before monday EOD
        TapirParameter.objects.filter(key=Parameter.DELIVERY_DAY).update(
            value="2"
        )  # delivery day is wednesday

        self.assertEqual(
            datetime.date(year=2025, month=3, day=3),
            JokerManagementService.get_date_limit_for_joker_changes(
                datetime.date(year=2025, month=3, day=7)
            ),
        )

    def test_getDateLimitForJokerChanges_weekdayForChangesIsInTheWeekBeforeDeliveryDay_returnsCorrectDate(
        self,
    ):
        TapirParameter.objects.filter(
            key=Parameter.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL
        ).update(
            value="5"
        )  # changes must be done before saturday EOD
        TapirParameter.objects.filter(key=Parameter.DELIVERY_DAY).update(
            value="2"
        )  # delivery day is wednesday

        self.assertEqual(
            datetime.date(year=2025, month=3, day=1),
            JokerManagementService.get_date_limit_for_joker_changes(
                datetime.date(year=2025, month=3, day=7)
            ),
        )
