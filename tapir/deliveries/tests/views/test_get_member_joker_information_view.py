import datetime
import json

from rest_framework import status
from rest_framework.reverse import reverse

from tapir.configuration.parameter import get_parameter_value
from tapir.deliveries.models import Joker
from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.models import GrowingPeriod
from tapir.wirgarten.parameters import ParameterDefinitions, Parameter
from tapir.wirgarten.tests import factories
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestGetMemberJokerInformationView(TapirIntegrationTest):
    def setUp(self) -> None:
        ParameterDefinitions().import_definitions()
        mock_timezone(self, factories.NOW)
        GrowingPeriodFactory.create()

    def test_getMemberJokerInformationView_accessOtherMemberInfoAsNormalUser_returns403(
        self,
    ):
        user = MemberFactory.create()
        other_member = MemberFactory.create()

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
            get_parameter_value(Parameter.JOKERS_AMOUNT_PER_CONTRACT),
            response_content["max_jokers_per_growing_period"],
        )
        self.assertEqual(
            get_parameter_value(Parameter.MEMBER_PICKUP_LOCATION_CHANGE_UNTIL),
            response_content["weekday_limit"],
        )
        self.assertEqual(
            len(JokerManagementService.get_extra_joker_restrictions()),
            len(response_content["joker_restrictions"]),
        )

    def test_getMemberJokerInformationView_default_doesntReturnJokersOfPastPeriod(
        self,
    ):
        user = MemberFactory.create(is_superuser=False)
        self.client.force_login(user)
        GrowingPeriod.objects.update(
            end_date=factories.NOW - datetime.timedelta(days=1)
        )
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
