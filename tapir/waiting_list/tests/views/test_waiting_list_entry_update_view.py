from django.urls import reverse

from tapir.configuration.models import TapirParameter
from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.models import WaitingListPickupLocationWish, WaitingListProductWish
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    ProductFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestWaitingListEntryUpdateView(TapirIntegrationTest):
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
            "product_ids": [product_1.id],
            "product_quantities": [8],
            "desired_start_date": "2026-11-05",
            "comment": "test_comment",
            "category": "cat2",
        }
        response = self.client.post(reverse("waiting_list:update_entry"), data=data)

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
