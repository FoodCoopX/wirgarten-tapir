from django.urls import reverse
from rest_framework import status

from tapir.bakery.tests.factories import (
    AvailableBreadsForDeliveryDayFactory,
    BreadFactory,
    BreadGroupFactory,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

YEAR = 2026
WEEK = 11
DAY = 3


class TestDirectOrderLimitsView(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.url = reverse("bakery:direct-order-limits")
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_get_default_returnsTheBreadsAndGroupsOfTheDay(self):
        group = BreadGroupFactory.create(name="Teig1")
        bread_a = BreadFactory.create(
            name="Brot A", group=group, max_pieces=40, min_remaining_pieces=0
        )
        bread_b = BreadFactory.create(
            name="Brot B",
            group=group,
            max_pieces=50,
            min_remaining_pieces=0,
            max_direct_order_percent=50,
        )
        for bread in (bread_a, bread_b):
            AvailableBreadsForDeliveryDayFactory.create(
                year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread
            )

        response = self.client.get(
            self.url, {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        breads = {b["bread_name"]: b for b in response.data["breads"]}
        self.assertEqual(breads["Brot A"]["bread_id"], bread_a.id)
        self.assertEqual(breads["Brot A"]["group_id"], group.id)
        self.assertEqual(breads["Brot A"]["total_capacity"], 40)
        self.assertEqual(breads["Brot A"]["total_capacity_source"], "group_max")
        self.assertEqual(breads["Brot A"]["limit"], 40)
        self.assertEqual(breads["Brot B"]["limit"], 20)
        self.assertEqual(breads["Brot B"]["default_percent"], 50)
        [group_limit] = response.data["groups"]
        self.assertEqual(group_limit["group_id"], group.id)
        self.assertEqual(group_limit["group_name"], "Teig1")
        self.assertEqual(
            sorted(group_limit["bread_ids"]), sorted([bread_a.id, bread_b.id])
        )
        self.assertEqual(group_limit["limit"], 40)

    def test_get_withoutDeliveryDay_returns400(self):
        response = self.client.get(self.url, {"year": YEAR, "delivery_week": WEEK})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_weekNotInTheYear_returns400(self):
        # 2027 has 52 ISO weeks.
        response = self.client.get(
            self.url, {"year": 2027, "delivery_week": 53, "delivery_day": DAY}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_loggedInAsNormalMember_returns403(self):
        self.client.force_login(MemberFactory.create())

        response = self.client.get(
            self.url, {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY}
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
