from django.urls import reverse

from tapir.waiting_list.tests.factories import WaitingListEntryFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestGetMemberWaitingListEntryDetailsApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_get_normalMemberRequestsOtherMemberData_returns403(self):
        logged_in_member = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)

        url = reverse("waiting_list:member_waiting_list_entry_details")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 403)

    def test_get_normalMemberRequestsOwnData_returns200(self):
        logged_in_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(logged_in_member)

        url = reverse("waiting_list:member_waiting_list_entry_details")
        url = f"{url}?member_id={logged_in_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

    def test_get_adminRequestsOtherMemberData_returns200(self):
        logged_in_member = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)

        url = reverse("waiting_list:member_waiting_list_entry_details")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)

    def test_get_memberDoesntHaveWaitingListEntry_returnsNone(self):
        logged_in_member = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)

        url = reverse("waiting_list:member_waiting_list_entry_details")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)
        self.assertEqual({"entry": None}, response.json())

    def test_get_memberHasWaitingListEntry_returnsEntryData(self):
        logged_in_member = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(logged_in_member)
        entry = WaitingListEntryFactory.create(member=other_member)

        url = reverse("waiting_list:member_waiting_list_entry_details")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, 200)
        entry_data = response.json()["entry"]
        self.assertEqual(entry.id, entry_data["id"])
