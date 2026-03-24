import datetime

from django.urls import reverse
from rest_framework import status

from tapir.configuration.models import TapirParameter
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory, SubscriptionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMemberSolidarityContributionsApiView(TapirIntegrationTest):
    maxDiff = 1000

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)
        TapirParameter.objects.filter(
            key=ParameterKeys.HARVEST_MEMBERS_ARE_ALLOWED_TO_CHANGE_SOLIPRICE
        ).update(value=True)

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2013, month=7, day=5))

    def test_get_membersAccessesOwnData_returnsCorrectData(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)

        url = reverse("solidarity_contribution:member_solidarity_contributions")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        self.assertEqual(
            {
                "contributions": [],
                "change_valid_from": "2013-07-08",
                "alternative_change_valid_from": None,
                "user_can_set_lower_value": False,
                "user_can_update_contribution": True,
            },
            response_content,
        )

    def test_get_adminAccessesDataOfOtherMember_returnsCorrectData(self):
        admin = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(admin)

        url = reverse("solidarity_contribution:member_solidarity_contributions")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        self.assertEqual(
            {
                "contributions": [],
                "change_valid_from": "2013-07-08",
                "alternative_change_valid_from": None,
                "user_can_set_lower_value": True,
                "user_can_update_contribution": True,
            },
            response_content,
        )

    def test_get_normalMembersAccessesDataOfOtherMember_returns403(self):
        user = MemberFactory.create(is_superuser=False)
        other_member = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)

        url = reverse("solidarity_contribution:member_solidarity_contributions")
        url = f"{url}?member_id={other_member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_hasFutureContribution_returnsCorrectAlternativeChangeDate(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        contribution = SolidarityContributionFactory.create(
            member=member, start_date=datetime.date(year=2013, month=9, day=1)
        )

        url = reverse("solidarity_contribution:member_solidarity_contributions")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        self.assertEqual("2013-07-08", response_content["change_valid_from"])
        self.assertEqual(
            "2013-09-01", response_content["alternative_change_valid_from"]
        )
        self.assertEqual(1, len(response_content["contributions"]))
        self.assertEqual(contribution.id, response_content["contributions"][0]["id"])

    def test_get_hasFutureSubscription_returnsCorrectAlternativeChangeDate(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        SubscriptionFactory.create(
            member=member, start_date=datetime.date(year=2013, month=10, day=16)
        )

        url = reverse("solidarity_contribution:member_solidarity_contributions")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        self.assertEqual("2013-07-08", response_content["change_valid_from"])
        self.assertEqual(
            "2013-10-16", response_content["alternative_change_valid_from"]
        )
        self.assertEqual(0, len(response_content["contributions"]))

    def test_get_hasFutureContributionAndSubscription_returnsSmallestAlternativeChangeDate(
        self,
    ):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        contribution = SolidarityContributionFactory.create(
            member=member, start_date=datetime.date(year=2013, month=9, day=1)
        )
        SubscriptionFactory.create(
            member=member, start_date=datetime.date(year=2013, month=10, day=16)
        )

        url = reverse("solidarity_contribution:member_solidarity_contributions")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        self.assertEqual("2013-07-08", response_content["change_valid_from"])
        self.assertEqual(
            "2013-09-01", response_content["alternative_change_valid_from"]
        )
        self.assertEqual(1, len(response_content["contributions"]))
        self.assertEqual(contribution.id, response_content["contributions"][0]["id"])

    def test_get_hasPastContracts_returnsNoAlternativeDate(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        contribution = SolidarityContributionFactory.create(
            member=member, start_date=datetime.date(year=2013, month=9, day=1)
        )
        SubscriptionFactory.create(
            member=member, start_date=datetime.date(year=2013, month=10, day=16)
        )
        SubscriptionFactory.create(
            member=member, start_date=datetime.date(year=2013, month=1, day=1)
        )

        url = reverse("solidarity_contribution:member_solidarity_contributions")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        self.assertEqual("2013-07-08", response_content["change_valid_from"])
        self.assertIsNone(response_content["alternative_change_valid_from"])
        self.assertEqual(1, len(response_content["contributions"]))
        self.assertEqual(contribution.id, response_content["contributions"][0]["id"])

    def test_get_normalMembersCantUpdateSoli_returnsCannotUpdateSoli(self):
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(member)
        TapirParameter.objects.filter(
            key=ParameterKeys.HARVEST_MEMBERS_ARE_ALLOWED_TO_CHANGE_SOLIPRICE
        ).update(value=False)

        url = reverse("solidarity_contribution:member_solidarity_contributions")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        self.assertFalse(response_content["user_can_update_contribution"])

    def test_get_normalMembersCantUpdateSoliButUserIsAdmin_returnsCanUpdateSoli(self):
        user = MemberFactory.create(is_superuser=True)
        member = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)

        TapirParameter.objects.filter(
            key=ParameterKeys.HARVEST_MEMBERS_ARE_ALLOWED_TO_CHANGE_SOLIPRICE
        ).update(value=False)

        url = reverse("solidarity_contribution:member_solidarity_contributions")
        url = f"{url}?member_id={member.id}"
        response = self.client.get(url)

        self.assertStatusCode(response, status.HTTP_200_OK)
        response_content = response.json()

        self.assertTrue(response_content["user_can_update_contribution"])
