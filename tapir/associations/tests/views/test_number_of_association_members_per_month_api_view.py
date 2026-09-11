import datetime

from django.urls import reverse
from rest_framework import status

from tapir.associations.tests.factories import (
    AssociationMembershipFactory,
    AssociationMembershipTypeFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestNumberOfAssociationMembersPerMonthApiView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

    @staticmethod
    def _build_url():
        url = reverse("associations:number_of_association_members_per_month")
        return f"{url}?start_date=2017-01-15&end_date=2017-04-03"

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create(is_superuser=False))

        response = self.client.get(self._build_url())

        self.assertStatusCode(response, status.HTTP_403_FORBIDDEN)

    def test_get_default_returnsCorrectData(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        type_1 = AssociationMembershipTypeFactory.create(name="type_A")
        AssociationMembershipFactory.create(
            start_date=datetime.date(year=2016, month=1, day=1),
            end_date=None,
            type=type_1,
        )
        AssociationMembershipFactory.create(
            start_date=datetime.date(year=2017, month=1, day=1),
            end_date=datetime.date(year=2017, month=2, day=18),
            type=type_1,
        )
        type_2 = AssociationMembershipTypeFactory.create(name="type_B")
        AssociationMembershipFactory.create(
            start_date=datetime.date(year=2017, month=2, day=1),
            end_date=datetime.date(year=2017, month=4, day=12),
            type=type_2,
        )

        response = self.client.get(self._build_url())

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["labels"], ["01.2017", "02.2017", "03.2017", "04.2017"])
        self.assertEqual(3, len(data["datasets"]))
        self.assertEqual("type_A", data["datasets"][0]["name"])
        self.assertEqual("type_B", data["datasets"][1]["name"])
        self.assertEqual("Gesamt", data["datasets"][2]["name"])

        values_type_1 = data["datasets"][0]["values"]
        self.assertEqual([2, 2, 1, 1], values_type_1)
        values_type_2 = data["datasets"][1]["values"]
        self.assertEqual([0, 1, 1, 1], values_type_2)
        values_total = data["datasets"][2]["values"]
        self.assertEqual([2, 3, 2, 2], values_total)

    def test_get_onlyOneMembershipType_returnsDataWithTotal(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))

        type_1 = AssociationMembershipTypeFactory.create(name="type_A")
        AssociationMembershipFactory.create(
            start_date=datetime.date(year=2016, month=1, day=1),
            end_date=None,
            type=type_1,
        )
        AssociationMembershipFactory.create(
            start_date=datetime.date(year=2017, month=1, day=1),
            end_date=datetime.date(year=2017, month=2, day=18),
            type=type_1,
        )

        response = self.client.get(self._build_url())

        self.assertStatusCode(response, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(1, len(data["datasets"]))
