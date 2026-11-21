import datetime
from unittest.mock import patch, MagicMock

from tapir.coop.services.member_needs_banking_data_checker import (
    MemberNeedsBankingDataChecker,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.subscriptions.services.admin_subscription_change_member_data_builder import (
    AdminSubscriptionChangeMemberDataBuilder,
    SubscriptionPrerequisitesStatus,
)
from tapir.wirgarten.tests.factories import MemberFactory, PickupLocationFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest, mock_timezone


@patch.object(
    MemberNeedsBankingDataChecker,
    "does_member_need_banking_data",
    autospec=True,
    return_value=False,
)
@patch.object(MemberPickupLocationGetter, "get_member_pickup_location", autospec=True)
class TestAdminSubscriptionChangeMemberDataBuilderBuildPrerequisitesStatus(
    TapirUnitTest
):
    def setUp(self):
        super().setUp()
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2027, month=6, day=2)
        )
        self.member = MemberFactory.build()

    def test_buildPrerequisitesStatus_everythingPresent_returnsStatus(
        self,
        mock_get_member_pickup_location: MagicMock,
        mock_does_member_need_banking_data: MagicMock,
    ):
        mock_get_member_pickup_location.return_value = PickupLocationFactory.build(
            name="Hofladen"
        )
        cache = {}

        status = AdminSubscriptionChangeMemberDataBuilder.build_prerequisites_status(
            member=self.member, cache=cache
        )

        self.assertEqual(
            SubscriptionPrerequisitesStatus(
                pickup_location_name="Hofladen",
                has_banking_data=True,
            ),
            status,
        )
        mock_get_member_pickup_location.assert_called_once_with(
            member=self.member, reference_date=self.now.date(), cache=cache
        )
        mock_does_member_need_banking_data.assert_called_once_with(self.member)

    def test_buildPrerequisitesStatus_everythingMissing_returnsEmptyStatus(
        self,
        mock_get_member_pickup_location: MagicMock,
        mock_does_member_need_banking_data: MagicMock,
    ):
        mock_get_member_pickup_location.return_value = None
        mock_does_member_need_banking_data.return_value = True

        status = AdminSubscriptionChangeMemberDataBuilder.build_prerequisites_status(
            member=self.member, cache={}
        )

        self.assertIsNone(status.pickup_location_name)
        self.assertFalse(status.has_banking_data)
