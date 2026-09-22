import datetime

from django.urls import reverse
from rest_framework import status

from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMemberListView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_memberListView_sortByLastNameAscending_compoundLowercaseLastNameSortedByFirstWord(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        member_ids = {
            MemberFactory.create(last_name="Vogel").id,
            MemberFactory.create(last_name="von Adler").id,
            MemberFactory.create(last_name="Voss").id,
            MemberFactory.create(last_name="Ahlers").id,
        }

        response = self.client.get(
            reverse("wirgarten:member_list"), {"o": "last_name_sort_key"}
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        last_names = [
            member.last_name
            for member in response.context["object_list"]
            if member.id in member_ids
        ]

        self.assertEqual(
            ["Ahlers", "Vogel", "von Adler", "Voss"],
            last_names,
        )

    def test_memberListView_sortByLastNameAscending_umlautLastNameSortedAsIfSpelledOut(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        member_ids = {
            MemberFactory.create(last_name="Häuser").id,
            MemberFactory.create(last_name="Heyne").id,
        }

        response = self.client.get(
            reverse("wirgarten:member_list"), {"o": "last_name_sort_key"}
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        last_names = [
            member.last_name
            for member in response.context["object_list"]
            if member.id in member_ids
        ]

        self.assertEqual(
            ["Häuser", "Heyne"],
            last_names,
        )

    def test_memberListView_sortBySolidarityContributionAscending_sortedByCurrentContributionAmount(
        self,
    ):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        now = mock_timezone(self, datetime.datetime(year=2026, month=6, day=15))
        today = now.date()

        member_low = MemberFactory.create(last_name="Low")
        member_high = MemberFactory.create(last_name="High")
        member_none = MemberFactory.create(last_name="None")
        SolidarityContributionFactory.create(
            member=member_low,
            amount=5,
            start_date=today - datetime.timedelta(days=1),
        )
        SolidarityContributionFactory.create(
            member=member_high,
            amount=25,
            start_date=today - datetime.timedelta(days=1),
        )
        member_ids = {member_low.id, member_high.id, member_none.id}

        response = self.client.get(
            reverse("wirgarten:member_list"), {"o": "current_member_contribution"}
        )

        self.assertStatusCode(response, status.HTTP_200_OK)
        last_names = [
            member.last_name
            for member in response.context["object_list"]
            if member.id in member_ids
        ]

        self.assertEqual(
            ["Low", "High", "None"],
            last_names,
        )
