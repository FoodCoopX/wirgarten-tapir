import datetime
import uuid

from django.urls import reverse
from rest_framework import status

from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.models import WaitingListProductWish, WaitingListPickupLocationWish
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    ProductFactory,
    ProductPriceFactory,
    PickupLocationFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestPublicGetWaitingListEntryDetails(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_entryIdIsCorrectButLinkKeyIsInvalid_returns404(self):
        entry = WaitingListEntryFactory.create(confirmation_link_key=uuid.uuid4())

        url = reverse("waiting_list:public_get_waiting_list_entry_details")
        url = f"{url}?entry_id={entry.id}&link_key=test_key"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_404_NOT_FOUND)

    def test_get_entryHasNoMember_birthdateAndBankingFieldsAreEmpty(self):
        entry = WaitingListEntryFactory.create(confirmation_link_key=uuid.uuid4())

        url = reverse("waiting_list:public_get_waiting_list_entry_details")
        url = f"{url}?entry_id={entry.id}&link_key={entry.confirmation_link_key}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertIsNone(response_content["birthdate"])
        self.assertIsNone(response_content["account_owner"])
        self.assertIsNone(response_content["iban"])

    def test_get_entryHasAMember_birthdateAndBankingFieldsAreFilled(self):
        member = MemberFactory.create(
            birthdate=datetime.date(year=1990, month=12, day=22),
            account_owner="Bart Simpson",
            iban="NL35ABNA7806242643",
        )
        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(), member=member
        )

        url = reverse("waiting_list:public_get_waiting_list_entry_details")
        url = f"{url}?entry_id={entry.id}&link_key={entry.confirmation_link_key}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertEqual("1990-12-22", response_content["birthdate"])
        self.assertEqual("Bart Simpson", response_content["account_owner"])
        self.assertEqual("NL35ABNA7806242643", response_content["iban"])

    def test_get_default_loadsCorrectly(self):
        member = MemberFactory.create()
        entry = WaitingListEntryFactory.create(
            confirmation_link_key=uuid.uuid4(), member=member
        )
        product = ProductFactory.create()
        ProductPriceFactory.create(product=product)
        WaitingListProductWish.objects.create(
            waiting_list_entry=entry, product=product, quantity=1
        )
        pickup_location = PickupLocationFactory.create()
        WaitingListPickupLocationWish.objects.create(
            waiting_list_entry=entry,
            pickup_location=pickup_location,
            priority=1,
        )

        url = reverse("waiting_list:public_get_waiting_list_entry_details")
        url = f"{url}?entry_id={entry.id}&link_key={entry.confirmation_link_key}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)

        response_content = response.json()
        self.assertEqual(1, len(response_content["product_wishes"]))
        self.assertEqual(
            product.id, response_content["product_wishes"][0]["product"]["id"]
        )
        self.assertEqual(1, len(response_content["pickup_location_wishes"]))
        self.assertEqual(
            pickup_location.id, response_content["pickup_location_wishes"][0]["id"]
        )
