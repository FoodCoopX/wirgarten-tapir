import json

from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.pickup_locations.services.home_delivery_address_validator import (
    HomeDeliveryAddressValidator,
)
from tapir.wirgarten.models import (
    WaitingListEntry,
    WaitingListPickupLocationWish,
    WaitingListProductWish,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestWaitingListEntryUpdateView(TapirIntegrationTest):
    @staticmethod
    def _build_request_data(
        entry: WaitingListEntry, pickup_location_ids: list[str]
    ) -> dict:
        return {
            "id": entry.id,
            "first_name": entry.first_name,
            "last_name": entry.last_name,
            "email": entry.email,
            "phone_number": str(entry.phone_number),
            "street": entry.street,
            "street_2": entry.street_2,
            "postcode": entry.postcode,
            "city": entry.city,
            "pickup_location_ids": pickup_location_ids,
            "shopping_cart": {},
            "comment": "",
        }

    def _post(self, data: dict):
        return self.client.post(
            reverse("waiting_list:update_entry"),
            data=json.dumps(data),
            content_type="application/json",
        )

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.SUBSCRIPTION_WAITING_LIST_CATEGORIES
        ).update(value="cat1,cat2")

    def test_post_loggedInAsNormalUser_returns403(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        response = self.client.post(reverse("waiting_list:update_entry"))

        self.assertEqual(response.status_code, 403)

    def test_post_loggedInAsAdmin_updatesEntry(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        entry = WaitingListEntryFactory.create()
        pickup_location_1 = PickupLocationFactory.create()
        pickup_location_2 = PickupLocationFactory.create()
        product_1 = ProductFactory.create()

        data = {
            "id": entry.id,
            "first_name": "test_first_name",
            "last_name": "test_last_name",
            "email": "test@test.net",
            "phone_number": "+4917027264538",
            "street": "test_street",
            "street_2": "test_street_2",
            "postcode": "test_postcode",
            "city": "test_city",
            "pickup_location_ids": [pickup_location_2.id, pickup_location_1.id],
            "shopping_cart": {product_1.id: 8},
            "desired_start_date": "2026-11-05",
            "comment": "test_comment",
            "category": "cat2",
        }

        response = self.client.post(
            reverse("waiting_list:update_entry"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        entry.refresh_from_db()
        self.assertEqual("test_first_name", entry.first_name)
        self.assertEqual("test_last_name", entry.last_name)
        self.assertEqual("test@test.net", entry.email)
        self.assertEqual("+4917027264538", entry.phone_number)
        self.assertEqual("test_street", entry.street)
        self.assertEqual("test_street_2", entry.street_2)
        self.assertEqual("test_postcode", entry.postcode)
        self.assertEqual("test_city", entry.city)
        self.assertEqual("test_comment", entry.comment)
        self.assertEqual("cat2", entry.category)

        self.assertEqual(2, entry.pickup_location_wishes.count())
        self.assertEqual(
            1,
            WaitingListPickupLocationWish.objects.get(
                waiting_list_entry=entry, pickup_location=pickup_location_2
            ).priority,
        )
        self.assertEqual(
            2,
            WaitingListPickupLocationWish.objects.get(
                waiting_list_entry=entry, pickup_location=pickup_location_1
            ).priority,
        )
        self.assertEqual(
            8,
            WaitingListProductWish.objects.get(
                waiting_list_entry=entry, product=product_1
            ).quantity,
        )

    def test_post_deliveryAddressGiven_savesDeliveryAddress(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        entry = WaitingListEntryFactory.create()
        pickup_location = PickupLocationFactory.create(is_home_delivery=True)
        data = self._build_request_data(
            entry=entry, pickup_location_ids=[pickup_location.id]
        )
        data["delivery_address"] = {
            "same_as_billing_address": False,
            "street": "Lieferweg 1",
            "street_2": "Hinterhaus",
            "postcode": "12345",
            "city": "Lieferstadt",
            "country": "DE",
        }

        response = self._post(data)

        self.assertEqual(200, response.status_code)
        entry.refresh_from_db()
        self.assertFalse(entry.delivery_same_as_billing_address)
        self.assertEqual("Lieferweg 1", entry.delivery_street)
        self.assertEqual("Hinterhaus", entry.delivery_street_2)
        self.assertEqual("12345", entry.delivery_postcode)
        self.assertEqual("Lieferstadt", entry.delivery_city)

    def test_post_homeDeliveryWishWithIncompleteAddress_returns400AndDoesNotSave(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        entry = WaitingListEntryFactory.create(comment="old_comment")
        normal_location = PickupLocationFactory.create()
        home_delivery_location = PickupLocationFactory.create(is_home_delivery=True)
        data = self._build_request_data(
            entry=entry,
            pickup_location_ids=[normal_location.id, home_delivery_location.id],
        )
        data["comment"] = "new_comment"
        data["delivery_address"] = {
            "same_as_billing_address": False,
            "street": "Lieferweg 1",
            "postcode": "",
            "city": "Lieferstadt",
        }

        response = self._post(data)

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            HomeDeliveryAddressValidator.MISSING_ADDRESS_MESSAGE, response.json()
        )
        entry.refresh_from_db()
        self.assertEqual("old_comment", entry.comment)
        self.assertTrue(entry.delivery_same_as_billing_address)
        self.assertEqual(0, entry.pickup_location_wishes.count())

    def test_post_incompleteAddressWithoutHomeDeliveryWish_savesEntry(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        entry = WaitingListEntryFactory.create()
        pickup_location = PickupLocationFactory.create()
        data = self._build_request_data(
            entry=entry, pickup_location_ids=[pickup_location.id]
        )
        data["delivery_address"] = {"same_as_billing_address": False}

        response = self._post(data)

        self.assertEqual(200, response.status_code)
        entry.refresh_from_db()
        self.assertFalse(entry.delivery_same_as_billing_address)

    def test_post_noDeliveryAddressGiven_keepsStoredDeliveryAddress(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        entry = WaitingListEntryFactory.create(
            delivery_same_as_billing_address=False,
            delivery_street="Lieferweg 1",
            delivery_postcode="12345",
            delivery_city="Lieferstadt",
        )
        pickup_location = PickupLocationFactory.create(is_home_delivery=True)
        data = self._build_request_data(
            entry=entry, pickup_location_ids=[pickup_location.id]
        )

        response = self._post(data)

        self.assertEqual(200, response.status_code)
        entry.refresh_from_db()
        self.assertFalse(entry.delivery_same_as_billing_address)
        self.assertEqual("Lieferweg 1", entry.delivery_street)
