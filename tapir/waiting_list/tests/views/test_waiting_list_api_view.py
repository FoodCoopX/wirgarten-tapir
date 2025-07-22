import datetime

from django.urls import reverse
from tapir_mail.service.shortcuts import make_timezone_aware

from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.models import (
    MemberPickupLocation,
    WaitingListProductWish,
    WaitingListPickupLocationWish,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestWaitingListAPIView(TapirIntegrationTest):
    maxDiff = 3000

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_waitingListView_loggedInAsNormalUser_redirectsToUserProfile(self):
        member = MemberFactory.create()
        self.client.force_login(member)

        response = self.client.get(reverse("waiting_list:api_list"))

        self.assertEqual(response.status_code, 403)

    def test_waitingListView_loggedInAsAdmin_returns200(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        url = reverse("waiting_list:api_list")
        url = f"{url}?limit=1&offset=0"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_waitingListView_default_returnsCorrectData(self):
        member = MemberFactory.create(is_superuser=True)
        self.client.force_login(member)

        mock_timezone(self, datetime.datetime(year=2025, month=1, day=20))

        pickup_location = PickupLocationFactory.create()
        MemberPickupLocation.objects.create(
            pickup_location=pickup_location,
            member=member,
            valid_from=datetime.datetime(2025, 1, 1),
        )
        subscription = SubscriptionFactory.create(
            member=member,
            start_date=datetime.datetime(2025, 1, 1),
            end_date=datetime.datetime(2025, 12, 31),
        )

        entry_1 = WaitingListEntryFactory.create(member=member)
        entry_2 = WaitingListEntryFactory.create()
        entry_3 = WaitingListEntryFactory.create()

        # entries should be sorted by creation date
        entry_1.created_at = make_timezone_aware(
            datetime.datetime(year=2025, month=1, day=10)
        )
        entry_1.save()
        entry_2.created_at = make_timezone_aware(
            datetime.datetime(year=2025, month=1, day=15)
        )
        entry_2.save()
        entry_3.created_at = make_timezone_aware(
            datetime.datetime(year=2025, month=1, day=9)
        )
        entry_3.save()

        WaitingListProductWish.objects.create(
            waiting_list_entry=entry_1, product=subscription.product, quantity=7
        )
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry_1, pickup_location=pickup_location, priority=5
        )

        url = reverse("waiting_list:api_list")
        url = f"{url}?limit=2&offset=0&order_by=created_at"
        response = self.client.get(url)

        response_content = response.json()
        self.assertEqual(3, response_content["count"])
        self.assertEqual(2, len(response_content["results"]))

        self.assertEqual(
            {
                "id": entry_3.id,
                "first_name": entry_3.first_name,
                "last_name": entry_3.last_name,
                "email": entry_3.email,
                "member_already_exists": False,
                "member_no": None,
                "number_of_coop_shares": entry_3.number_of_coop_shares,
                "phone_number": str(entry_3.phone_number),
                "street": entry_3.street,
                "street_2": entry_3.street_2,
                "postcode": entry_3.postcode,
                "city": entry_3.city,
                "waiting_since": "2025-01-09T00:00:00+01:00",
                "pickup_location_wishes": [],
                "product_wishes": [],
                "category": entry_3.category,
                "comment": entry_3.comment,
                "current_pickup_location": None,
                "current_products": None,
                "date_of_entry_in_cooperative": None,
                "country": entry_3.country,
                "desired_start_date": None,
                "current_subscriptions": None,
                "url_to_member_profile": None,
                "link": None,
                "link_key": None,
                "link_sent_date": None,
            },
            response_content["results"][0],
        )

        self.assertEqual(entry_1.id, response_content["results"][1]["id"])
        self.assertTrue(response_content["results"][1]["member_already_exists"])
        self.assertEqual(
            member.first_name, response_content["results"][1]["first_name"]
        )
        self.assertEqual(
            pickup_location.id,
            response_content["results"][1]["current_pickup_location"]["id"],
        )
        self.assertEqual(
            subscription.product.id,
            response_content["results"][1]["current_products"][0]["id"],
        )
        self.assertEqual(
            subscription.product.id,
            response_content["results"][1]["product_wishes"][0]["product"]["id"],
        )
        self.assertEqual(
            7,
            response_content["results"][1]["product_wishes"][0]["quantity"],
        )
        self.assertEqual(
            5,
            response_content["results"][1]["pickup_location_wishes"][0]["priority"],
        )
        self.assertEqual(
            pickup_location.id,
            response_content["results"][1]["pickup_location_wishes"][0][
                "pickup_location"
            ]["id"],
        )
        self.assertEqual(
            subscription.id,
            response_content["results"][1]["current_subscriptions"][0]["id"],
        )
        self.assertEqual(
            subscription.id,
            response_content["results"][1]["current_subscriptions"][0]["id"],
        )
        url = reverse("wirgarten:member_detail", args=[member.id])
        self.assertEqual(
            url,
            response_content["results"][1]["url_to_member_profile"],
        )
