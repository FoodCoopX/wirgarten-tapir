import datetime
import json

from rest_framework import status
from rest_framework.reverse import reverse

from tapir.configuration.models import TapirParameter
from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetMemberJokerInformationView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def setUp(self) -> None:
        mock_timezone(self, factories.NOW)

    def test_getMemberJokerInformationView_accessOtherMemberInfoAsNormalUser_returns403(
        self,
    ):
        user = MemberFactory.create()
        other_member = MemberFactory.create()
        GrowingPeriodFactory.create()

        self.client.force_login(user)

        response = self.client.get(
            reverse("Deliveries:member_joker_information")
            + "?member_id="
            + other_member.id
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

    def test_getMemberJokerInformationView_accessOtherMemberInfoAsAdmin_returnsStatus200(
        self,
    ):
        user = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        GrowingPeriodFactory.create()
        self.client.force_login(user)

        response = self.client.get(
            reverse("Deliveries:member_joker_information")
            + "?member_id="
            + other_member.id
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)

    def test_getMemberJokerInformationView_accessOwnInfoAsNormalMember_returnsCorrectInformation(
        self,
    ):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2023, month=1, day=1),
            end_date=datetime.date(year=2023, month=12, day=31),
            max_jokers_per_member=3,
            joker_restrictions="01.08.-31.08.[2]",
        )
        GrowingPeriodFactory.create(
            start_date=datetime.date(year=2024, month=1, day=1),
            end_date=datetime.date(year=2024, month=12, day=31),
            max_jokers_per_member=2,
            joker_restrictions="disabled",
        )
        Joker.objects.create(
            member=user, date=datetime.date(year=2023, month=7, day=15)
        )

        response = self.client.get(
            reverse("Deliveries:member_joker_information") + "?member_id=" + user.id
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_content = json.loads(response.content)
        self.assertEqual(1, len(response_content["used_jokers"]))
        self.assertEqual(
            "2023-07-15", response_content["used_jokers"][0]["joker"]["date"]
        )
        self.assertEqual(
            get_parameter_value(ParameterKeys.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL),
            response_content["weekday_limit"],
        )
        self.assertEqual(len(response_content["used_joker_in_growing_period"]), 2)
        self.assertEqual(
            [
                {
                    "growing_period_end": "2023-12-31",
                    "growing_period_start": "2023-01-01",
                    "joker_restrictions": [
                        {
                            "end_day": 31,
                            "end_month": 8,
                            "max_jokers": 2,
                            "start_day": 1,
                            "start_month": 8,
                        }
                    ],
                    "max_jokers": 3,
                    "number_of_used_jokers": 1,
                },
                {
                    "growing_period_end": "2024-12-31",
                    "growing_period_start": "2024-01-01",
                    "joker_restrictions": [],
                    "max_jokers": 2,
                    "number_of_used_jokers": 0,
                },
            ],
            response_content["used_joker_in_growing_period"],
        )

    def test_getMemberJokerInformationView_default_doesntReturnJokersOfPastPeriod(
        self,
    ):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)
        GrowingPeriodFactory.create(end_date=factories.NOW - datetime.timedelta(days=1))
        Joker.objects.create(  # joker in past period
            member=user, date=factories.NOW - datetime.timedelta(days=2)
        )
        GrowingPeriodFactory.create(
            start_date=factories.NOW.date(),
            end_date=factories.NOW.date() + datetime.timedelta(days=20),
        )
        Joker.objects.create(  # joker in current period
            member=user, date=datetime.date(year=2023, month=7, day=15)
        )

        response = self.client.get(
            reverse("Deliveries:member_joker_information") + "?member_id=" + user.id
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)
        response_content = json.loads(response.content)
        self.assertEqual(1, len(response_content["used_jokers"]))
        self.assertEqual(
            "2023-07-15", response_content["used_jokers"][0]["joker"]["date"]
        )

    def test_getMemberJokerInformationView_jokerFeatureDisabled_returns403(
        self,
    ):
        TapirParameter.objects.filter(key=ParameterKeys.JOKERS_ENABLED).update(
            value="False"
        )
        GrowingPeriodFactory.create()

        user = MemberFactory.create(is_superuser=True)
        other_member = MemberFactory.create()
        self.client.force_login(user)

        response = self.client.get(
            reverse("Deliveries:member_joker_information")
            + "?member_id="
            + other_member.id
        )

        self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)
