import datetime
from decimal import Decimal
from unittest.mock import patch, Mock

from tapir.deliveries.services.joker_value_service import JokerValueService
from tapir.pickup_locations.services.member_pickup_location_getter import (
    MemberPickupLocationGetter,
)
from tapir.pickup_locations.services.pickup_location_delivery_charge_service import (
    PickupLocationDeliveryChargeService,
)
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirUnitTest


@patch.object(
    PickupLocationDeliveryChargeService, "get_delivery_charge_at_date", autospec=True
)
@patch.object(
    MemberPickupLocationGetter,
    "get_member_pickup_location_id_from_cache",
    autospec=True,
)
class TestGetDeliveryChargePart(TapirUnitTest):
    JOKER_DATE = datetime.date(year=2021, month=5, day=7)

    def test_getDeliveryChargePart_pickupLocationHasCharge_returnsPart(
        self,
        mock_get_member_pickup_location_id: Mock,
        mock_get_delivery_charge_at_date: Mock,
    ):
        mock_get_member_pickup_location_id.return_value = "pickup_location_id"
        mock_get_delivery_charge_at_date.return_value = Decimal("1.5")
        member = MemberFactory.build()
        cache = {}

        part = JokerValueService._get_delivery_charge_part(
            member=member, joker_date=self.JOKER_DATE, cache=cache
        )

        self.assertEqual(Decimal("1.5"), part.value)
        self.assertEqual("Liefergebühr Abholort: 1,50 €", part.explanation)
        mock_get_member_pickup_location_id.assert_called_once_with(
            member_id=member.id, reference_date=self.JOKER_DATE, cache=cache
        )
        mock_get_delivery_charge_at_date.assert_called_once_with(
            pickup_location_id="pickup_location_id",
            reference_date=self.JOKER_DATE,
            cache=cache,
        )

    def test_getDeliveryChargePart_chargeIsZero_returnsNone(
        self,
        mock_get_member_pickup_location_id: Mock,
        mock_get_delivery_charge_at_date: Mock,
    ):
        mock_get_member_pickup_location_id.return_value = "pickup_location_id"
        mock_get_delivery_charge_at_date.return_value = Decimal(0)

        part = JokerValueService._get_delivery_charge_part(
            member=MemberFactory.build(), joker_date=self.JOKER_DATE, cache={}
        )

        self.assertIsNone(part)

    def test_getDeliveryChargePart_memberHasNoPickupLocation_returnsNone(
        self,
        mock_get_member_pickup_location_id: Mock,
        mock_get_delivery_charge_at_date: Mock,
    ):
        mock_get_member_pickup_location_id.return_value = None

        part = JokerValueService._get_delivery_charge_part(
            member=MemberFactory.build(), joker_date=self.JOKER_DATE, cache={}
        )

        self.assertIsNone(part)
        mock_get_delivery_charge_at_date.assert_not_called()
