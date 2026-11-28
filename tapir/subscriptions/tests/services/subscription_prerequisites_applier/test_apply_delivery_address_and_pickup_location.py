import datetime
from unittest.mock import patch, MagicMock, Mock

from tapir.pickup_locations.services.member_delivery_address_setter import (
    MemberDeliveryAddressSetter,
)
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.member_pickup_location_setter import (
    MemberPickupLocationSetter,
)
from tapir.subscriptions.services.subscription_prerequisites_applier import (
    SubscriptionPrerequisitesApplier,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    MemberPickupLocationGetter,
    "get_member_pickup_location_id",
    autospec=True,
    return_value="current_id",
)
@patch.object(
    MemberPickupLocationSetter, "link_member_to_pickup_location", autospec=True
)
@patch.object(MemberDeliveryAddressSetter, "save_delivery_address", autospec=True)
class TestSubscriptionPrerequisitesApplierApplyDeliveryAddressAndPickupLocation(
    TapirUnitTest
):
    def test_applyDeliveryAddressAndPickupLocation_desiredLocationDiffersFromCurrent_linksMemberToDesiredLocation(
        self,
        mock_save_delivery_address: MagicMock,
        mock_link_member_to_pickup_location: MagicMock,
        mock_get_member_pickup_location_id: MagicMock,
    ):
        member = MemberFactory.build()
        actor = Mock()
        subscription_start_date = datetime.date(year=2027, month=3, day=1)
        cache = {}

        SubscriptionPrerequisitesApplier.apply_delivery_address_and_pickup_location(
            member=member,
            subscription_start_date=subscription_start_date,
            desired_pickup_location_id="desired_id",
            actor=actor,
            cache=cache,
        )

        mock_save_delivery_address.assert_called_once_with(member=member, actor=actor)
        mock_get_member_pickup_location_id.assert_called_once_with(
            member=member, reference_date=subscription_start_date
        )
        mock_link_member_to_pickup_location.assert_called_once_with(
            member=member,
            valid_from=subscription_start_date,
            pickup_location_id="desired_id",
            actor=actor,
            cache=cache,
        )

    def test_applyDeliveryAddressAndPickupLocation_desiredLocationIsCurrent_doesNotLinkAgain(
        self,
        mock_save_delivery_address: MagicMock,
        mock_link_member_to_pickup_location: MagicMock,
        _: MagicMock,
    ):
        member = MemberFactory.build()
        actor = Mock()

        SubscriptionPrerequisitesApplier.apply_delivery_address_and_pickup_location(
            member=member,
            subscription_start_date=datetime.date(year=2027, month=3, day=1),
            desired_pickup_location_id="current_id",
            actor=actor,
            cache={},
        )

        mock_save_delivery_address.assert_called_once_with(member=member, actor=actor)
        mock_link_member_to_pickup_location.assert_not_called()
