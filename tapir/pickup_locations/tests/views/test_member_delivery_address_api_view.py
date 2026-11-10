import datetime
from unittest.mock import MagicMock, patch

from django.urls import reverse
from rest_framework import status

from tapir.pickup_locations.models import MemberDeliveryAddressChangedLogEntry
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberPickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone

MISSING_ADDRESS_MESSAGE = "Für die Hauslieferung wird eine vollständige Lieferadresse (Straße, PLZ und Ort) benötigt."


class TestMemberDeliveryAddressApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self) -> None:
        super().setUp()
        self.now = mock_timezone(
            self, now=datetime.datetime(year=2027, month=6, day=15)
        )

    @staticmethod
    def _build_separate_address(**overrides: str) -> dict[str, str | bool]:
        address = {
            "same_as_billing_address": False,
            "street": "Lieferweg 2",
            "street_2": "",
            "postcode": "22222",
            "city": "Lieferdorf",
            "country": "DE",
        }
        address.update(overrides)
        return address

    @staticmethod
    def _create_member_with_home_delivery() -> Member:
        return MemberPickupLocationFactory.create(
            pickup_location__is_home_delivery=True,
            valid_from=datetime.date(year=2027, month=1, day=1),
            member__street="Rechnungsstraße 1",
            member__street_2="",
            member__postcode="11111",
            member__city="Rechnungsstadt",
            member__country="DE",
        ).member

    def _get(self, member_id: str):
        return self.client.get(
            reverse("pickup_locations:member_delivery_address")
            + f"?member_id={member_id}"
        )

    def _put(self, member_id: str, data: dict[str, str | bool]):
        return self.client.put(
            reverse("pickup_locations:member_delivery_address")
            + f"?member_id={member_id}",
            data=data,
            content_type="application/json",
        )

    @patch(
        "tapir.pickup_locations.views.calculate_pickup_location_change_date",
        autospec=True,
    )
    def test_get_ownMemberWithHomeDelivery_returnsAddressData(
        self, mock_calculate_pickup_location_change_date: MagicMock
    ):
        mock_calculate_pickup_location_change_date.return_value = datetime.date(
            year=2027, month=6, day=15
        )
        member = self._create_member_with_home_delivery()
        self.client.force_login(member)

        response = self._get(member_id=member.id)

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {
                "same_as_billing_address": True,
                "street": "",
                "street_2": "",
                "postcode": "",
                "city": "",
                "country": "DE",
                "change_warning_text": "",
            },
            response.json(),
        )

    @patch(
        "tapir.pickup_locations.views.calculate_pickup_location_change_date",
        autospec=True,
    )
    def test_get_afterCutoff_returnsWarningText(
        self, mock_calculate_pickup_location_change_date: MagicMock
    ):
        mock_calculate_pickup_location_change_date.return_value = datetime.date(
            year=2027, month=6, day=21
        )
        self._set_parameter(
            key=ParameterKeys.MEMBER_DELIVERY_ADDRESS_CHANGE_WARNING_TEXT,
            value="test_warning",
        )
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self._get(member_id=member.id)

        self.assertEqual("test_warning", response.json()["change_warning_text"])

    def test_get_otherMemberAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        response = self._get(member_id=MemberFactory.create().id)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_put_ownMember_savesAddressAndLogsChange(self):
        member = self._create_member_with_home_delivery()
        self.client.force_login(member)

        response = self._put(member_id=member.id, data=self._build_separate_address())

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assert_order_confirmed(response.json())
        member.refresh_from_db()
        self.assertFalse(member.delivery_same_as_billing_address)
        self.assertEqual("Lieferweg 2", member.delivery_street)
        self.assertEqual("22222", member.delivery_postcode)
        self.assertEqual("Lieferdorf", member.delivery_city)
        self.assertTrue(
            MemberDeliveryAddressChangedLogEntry.objects.filter(user=member).exists()
        )

    def test_put_homeDeliveryAndIncompleteAddress_returnsErrorAndDoesNotSave(self):
        member = self._create_member_with_home_delivery()
        self.client.force_login(member)

        response = self._put(
            member_id=member.id, data=self._build_separate_address(street="")
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        self.assertEqual(
            {"order_confirmed": False, "error": MISSING_ADDRESS_MESSAGE},
            response.json(),
        )
        member.refresh_from_db()
        self.assertTrue(member.delivery_same_as_billing_address)
        self.assertFalse(MemberDeliveryAddressChangedLogEntry.objects.exists())

    def test_put_noHomeDeliveryAndIncompleteAddress_saves(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self._put(
            member_id=member.id, data=self._build_separate_address(street="")
        )

        self.assert_order_confirmed(response.json())
        member.refresh_from_db()
        self.assertFalse(member.delivery_same_as_billing_address)

    def test_put_otherMemberAsAdmin_saves(self):
        member = MemberFactory.create()
        self._login_as_admin()

        response = self._put(member_id=member.id, data=self._build_separate_address())

        self.assert_order_confirmed(response.json())
        member.refresh_from_db()
        self.assertEqual("Lieferweg 2", member.delivery_street)

    def test_put_otherMemberAsNormalMember_returns403(self):
        member = MemberFactory.create()
        self.client.force_login(MemberFactory.create())

        response = self._put(member_id=member.id, data=self._build_separate_address())

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)
        member.refresh_from_db()
        self.assertTrue(member.delivery_same_as_billing_address)
