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
from tapir.subscriptions.services.contract_prerequisites_applier import (
    ContractPrerequisitesApplier,
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
class TestContractPrerequisitesApplierApplyPickupLocation(TapirUnitTest):
    def test_applyPickupLocation_desiredLocationDiffersFromCurrent_linksMemberToDesiredLocation(
        self,
        mock_save_delivery_address: MagicMock,
        mock_link_member_to_pickup_location: MagicMock,
        mock_get_member_pickup_location_id: MagicMock,
    ):
        member = MemberFactory.build()
        actor = Mock()
        contract_start_date = datetime.date(year=2027, month=3, day=1)
        cache = {}

        ContractPrerequisitesApplier.apply_pickup_location(
            member=member,
            contract_start_date=contract_start_date,
            desired_pickup_location_id="desired_id",
            actor=actor,
            cache=cache,
        )

        mock_save_delivery_address.assert_called_once_with(member=member, actor=actor)
        mock_get_member_pickup_location_id.assert_called_once_with(
            member=member, reference_date=contract_start_date
        )
        mock_link_member_to_pickup_location.assert_called_once_with(
            member=member,
            valid_from=contract_start_date,
            pickup_location_id="desired_id",
            actor=actor,
            cache=cache,
        )

    def test_applyPickupLocation_desiredLocationIsCurrent_doesNotLinkAgain(
        self,
        mock_save_delivery_address: MagicMock,
        mock_link_member_to_pickup_location: MagicMock,
        _: MagicMock,
    ):
        member = MemberFactory.build()
        actor = Mock()

        ContractPrerequisitesApplier.apply_pickup_location(
            member=member,
            contract_start_date=datetime.date(year=2027, month=3, day=1),
            desired_pickup_location_id="current_id",
            actor=actor,
            cache={},
        )

        mock_save_delivery_address.assert_called_once_with(member=member, actor=actor)
        mock_link_member_to_pickup_location.assert_not_called()
