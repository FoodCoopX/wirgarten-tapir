from django.urls import reverse
from rest_framework import status

from tapir.bakery.models import (
    BreadCapacityPickupLocation,
    BreadContent,
    BreadLabel,
    BreadSpecificsPerDeliveryDay,
    PreferredBread,
    PreferredLabel,
)
from tapir.bakery.tests.factories import (
    BreadCapacityPickupLocationFactory,
    BreadContentFactory,
    BreadDeliveryFactory,
    BreadFactory,
    BreadLabelFactory,
    BreadSpecificsPerDeliveryDayFactory,
    BreadsPerPickupLocationPerWeekFactory,
    IngredientFactory,
    StoveSessionFactory,
)
from tapir.wirgarten.models import PickupLocationOpeningTime
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest

YEAR = 2026
WEEK = 11
DAY = 3


def create_pickup_location_with_delivery_day(day, **kwargs):
    pl = PickupLocationFactory.create(**kwargs)
    PickupLocationOpeningTime.objects.create(
        pickup_location=pl,
        day_of_week=day,
        open_time="08:00",
        close_time="18:00",
    )
    return pl


# ──────────────────────────────────────────────────────────────────────
# BreadLabelViewSet
# ──────────────────────────────────────────────────────────────────────
class TestBreadLabelViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_list_returnsAllLabels(self):
        BreadLabelFactory.create(name="Vollkorn")
        BreadLabelFactory.create(name="Sauerteig")

        response = self.client.get(reverse("bakery:labels-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [l["name"] for l in response.data]
        self.assertIn("Vollkorn", names)
        self.assertIn("Sauerteig", names)

    def test_create_createsLabel(self):
        response = self.client.post(
            reverse("bakery:labels-list"),
            {"name": "Glutenfrei"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(BreadLabel.objects.filter(name="Glutenfrei").exists())

    def test_unauthenticated_returns401or403(self):
        self.client.logout()
        response = self.client.get(reverse("bakery:labels-list"))
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )


# ──────────────────────────────────────────────────────────────────────
# IngredientViewSet
# ──────────────────────────────────────────────────────────────────────
class TestIngredientViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_list_returnsAll(self):
        IngredientFactory.create(name="Mehl")
        IngredientFactory.create(name="Wasser")

        response = self.client.get(reverse("bakery:ingredients-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_list_filterByOrganic(self):
        IngredientFactory.create(name="Bio-Mehl", is_organic=True, is_active=True)
        IngredientFactory.create(name="Salz", is_organic=False, is_active=True)

        response = self.client.get(
            reverse("bakery:ingredients-list"), {"is_organic": "true"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [i["name"] for i in response.data]
        self.assertIn("Bio-Mehl", names)
        self.assertNotIn("Salz", names)

    def test_list_filterByActive(self):
        IngredientFactory.create(name="Aktiv", is_active=True)
        IngredientFactory.create(name="Inaktiv", is_active=False)

        response = self.client.get(
            reverse("bakery:ingredients-list"), {"is_active": "false"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [i["name"] for i in response.data]
        self.assertIn("Inaktiv", names)
        self.assertNotIn("Aktiv", names)

    def test_list_filterByOrganicAndActive(self):
        IngredientFactory.create(name="A", is_organic=True, is_active=True)
        IngredientFactory.create(name="B", is_organic=True, is_active=False)
        IngredientFactory.create(name="C", is_organic=False, is_active=True)

        response = self.client.get(
            reverse("bakery:ingredients-list"),
            {"is_organic": "true", "is_active": "true"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [i["name"] for i in response.data]
        self.assertEqual(names, ["A"])


# ──────────────────────────────────────────────────────────────────────
# BreadViewSet
# ──────────────────────────────────────────────────────────────────────
class TestBreadViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_list_orderedByName(self):
        BreadFactory.create(name="Zopf")
        BreadFactory.create(name="Anisbrot")

        response = self.client.get(reverse("bakery:breads-list-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [b["name"] for b in response.data]
        self.assertEqual(names, ["Anisbrot", "Zopf"])

    def test_list_filterByActive(self):
        BreadFactory.create(name="Aktiv", is_active=True)
        BreadFactory.create(name="Inaktiv", is_active=False)

        response = self.client.get(
            reverse("bakery:breads-list-list"), {"is_active": "true"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [b["name"] for b in response.data]
        self.assertIn("Aktiv", names)
        self.assertNotIn("Inaktiv", names)

    def test_list_filterByLabel(self):
        label = BreadLabelFactory.create(name="Vollkorn")
        bread_with = BreadFactory.create(name="Vollkornbrot")
        bread_with.labels.add(label)
        BreadFactory.create(name="Weissbrot")

        response = self.client.get(
            reverse("bakery:breads-list-list"), {"label_id": str(label.id)}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [b["name"] for b in response.data]
        self.assertIn("Vollkornbrot", names)
        self.assertNotIn("Weissbrot", names)

    def test_list_filterByPickupLocationYearWeek_withCapacityAndAvailability(self):
        pl = PickupLocationFactory.create()
        bread = BreadFactory.create(name="Roggenbrot", is_active=True)
        BreadCapacityPickupLocationFactory.create(
            bread=bread,
            pickup_location=pl,
            year=YEAR,
            delivery_week=WEEK,
            capacity=5,
        )

        response = self.client.get(
            reverse("bakery:breads-list-list"),
            {
                "pickup_location_id": str(pl.id),
                "year": YEAR,
                "week": WEEK,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [b["name"] for b in response.data]
        self.assertIn("Roggenbrot", names)

    def test_list_filterByPickupLocation_noCapacityLeft_excluded(self):
        pl = PickupLocationFactory.create()
        bread = BreadFactory.create(name="Roggenbrot", is_active=True)
        BreadCapacityPickupLocationFactory.create(
            bread=bread,
            pickup_location=pl,
            year=YEAR,
            delivery_week=WEEK,
            capacity=1,
        )
        member = MemberFactory.create()
        sub = SubscriptionFactory.create(member=member)
        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=bread,
        )

        response = self.client.get(
            reverse("bakery:breads-list-list"),
            {
                "pickup_location_id": str(pl.id),
                "year": YEAR,
                "week": WEEK,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [b["name"] for b in response.data]
        self.assertNotIn("Roggenbrot", names)

    def test_byLabels_returnsMatchingBreads(self):
        label1 = BreadLabelFactory.create(name="Sauerteig")
        label2 = BreadLabelFactory.create(name="Vollkorn")
        bread1 = BreadFactory.create(name="Sauerteigbrot")
        bread1.labels.add(label1)
        bread2 = BreadFactory.create(name="Vollkornbrot")
        bread2.labels.add(label2)
        BreadFactory.create(name="Weissbrot")

        response = self.client.get(
            reverse("bakery:breads-list-by-labels"),
            {"label_ids": ",".join([str(label1.id), str(label2.id)])},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [b["name"] for b in response.data]
        self.assertIn("Sauerteigbrot", names)
        self.assertIn("Vollkornbrot", names)
        self.assertNotIn("Weissbrot", names)

    def test_byLabels_invalidIds_returns400(self):
        response = self.client.get(
            reverse("bakery:breads-list-by-labels"),
            {"label_ids": "abc,xyz"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_returnsDetailSerializer(self):
        bread = BreadFactory.create(name="Roggenbrot")

        response = self.client.get(
            reverse("bakery:breads-list-detail", kwargs={"pk": bread.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Roggenbrot")

    def test_contents_get_returnsIngredients(self):
        bread = BreadFactory.create(name="Roggenbrot")
        ingredient = IngredientFactory.create(name="Mehl")
        BreadContentFactory.create(bread=bread, ingredient=ingredient)

        response = self.client.get(
            reverse("bakery:breads-list-contents", kwargs={"pk": bread.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_contents_post_addsIngredient(self):
        bread = BreadFactory.create(name="Roggenbrot")
        ingredient = IngredientFactory.create(name="Mehl")

        response = self.client.post(
            reverse("bakery:breads-list-contents", kwargs={"pk": bread.pk}),
            {"ingredient": str(ingredient.id), "amount": 50.0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            BreadContent.objects.filter(bread=bread, ingredient=ingredient).exists()
        )


# ──────────────────────────────────────────────────────────────────────
# BreadContentViewSet
# ──────────────────────────────────────────────────────────────────────
class TestBreadContentViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_list_filterByBread(self):
        bread1 = BreadFactory.create(name="A")
        bread2 = BreadFactory.create(name="B")
        ing = IngredientFactory.create(name="Mehl")
        BreadContentFactory.create(bread=bread1, ingredient=ing)
        BreadContentFactory.create(bread=bread2, ingredient=ing)

        response = self.client.get(
            reverse("bakery:breadcontents-list"), {"bread": str(bread1.id)}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_filterByIngredient(self):
        bread = BreadFactory.create(name="A")
        ing1 = IngredientFactory.create(name="Mehl")
        ing2 = IngredientFactory.create(name="Salz")
        BreadContentFactory.create(bread=bread, ingredient=ing1)
        BreadContentFactory.create(bread=bread, ingredient=ing2)

        response = self.client.get(
            reverse("bakery:breadcontents-list"),
            {"ingredient_id": str(ing1.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


# ──────────────────────────────────────────────────────────────────────
# BreadCapacityPickupLocationViewSet
# ──────────────────────────────────────────────────────────────────────
class TestBreadCapacityPickupLocationViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_list_filterByYearAndWeek(self):
        pl = PickupLocationFactory.create()
        bread = BreadFactory.create(name="Roggenbrot")
        BreadCapacityPickupLocationFactory.create(
            bread=bread, pickup_location=pl, year=YEAR, delivery_week=WEEK, capacity=5
        )
        BreadCapacityPickupLocationFactory.create(
            bread=bread,
            pickup_location=pl,
            year=YEAR,
            delivery_week=WEEK + 1,
            capacity=3,
        )

        response = self.client.get(
            reverse("bakery:bread_capacity_pickup_location-list"),
            {"year": YEAR, "week": WEEK},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_filterByPickupLocationIds(self):
        pl1 = PickupLocationFactory.create()
        pl2 = PickupLocationFactory.create()
        bread = BreadFactory.create(name="Roggenbrot")
        BreadCapacityPickupLocationFactory.create(
            bread=bread, pickup_location=pl1, year=YEAR, delivery_week=WEEK, capacity=5
        )
        BreadCapacityPickupLocationFactory.create(
            bread=bread, pickup_location=pl2, year=YEAR, delivery_week=WEEK, capacity=3
        )

        response = self.client.get(
            reverse("bakery:bread_capacity_pickup_location-list"),
            {"pickup_location_ids[]": [str(pl1.id)]},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_bulkUpdate_createAndUpdate(self):
        pl = PickupLocationFactory.create()
        bread = BreadFactory.create(name="Roggenbrot")

        url = reverse("bakery:bread_capacity_pickup_location-bulk-update")

        response = self.client.post(
            url,
            data={
                "year": YEAR,
                "delivery_week": WEEK,
                "updates": [
                    {
                        "pickup_location": str(pl.id),
                        "bread": str(bread.id),
                        "capacity": 10,
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            BreadCapacityPickupLocation.objects.filter(
                year=YEAR,
                delivery_week=WEEK,
                pickup_location=pl,
                bread=bread,
                capacity=10,
            ).exists()
        )

        # Update
        response = self.client.post(
            url,
            data={
                "year": YEAR,
                "delivery_week": WEEK,
                "updates": [
                    {
                        "pickup_location": str(pl.id),
                        "bread": str(bread.id),
                        "capacity": 20,
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cap = BreadCapacityPickupLocation.objects.get(
            year=YEAR, delivery_week=WEEK, pickup_location=pl, bread=bread
        )
        self.assertEqual(cap.capacity, 20)

    def test_bulkUpdate_deleteWithNullCapacity(self):
        pl = PickupLocationFactory.create()
        bread = BreadFactory.create(name="Roggenbrot")
        BreadCapacityPickupLocationFactory.create(
            bread=bread, pickup_location=pl, year=YEAR, delivery_week=WEEK, capacity=5
        )

        response = self.client.post(
            reverse("bakery:bread_capacity_pickup_location-bulk-update"),
            data={
                "year": YEAR,
                "delivery_week": WEEK,
                "updates": [
                    {
                        "pickup_location": str(pl.id),
                        "bread": str(bread.id),
                        "capacity": None,
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            BreadCapacityPickupLocation.objects.filter(
                year=YEAR, delivery_week=WEEK, pickup_location=pl, bread=bread
            ).exists()
        )

    def test_bulkUpdate_missingYearOrWeek_returns400(self):
        response = self.client.post(
            reverse("bakery:bread_capacity_pickup_location-bulk-update"),
            data={"updates": []},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────────────────────────────
# BreadDeliveryViewSet
# ──────────────────────────────────────────────────────────────────────
class TestBreadDeliveryViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_list_filterByMember(self):
        pl = PickupLocationFactory.create()
        member1 = MemberFactory.create()
        member2 = MemberFactory.create()
        sub1 = SubscriptionFactory.create(member=member1)
        sub2 = SubscriptionFactory.create(member=member2)
        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub1,
            pickup_location=pl,
            bread=None,
        )
        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub2,
            pickup_location=pl,
            bread=None,
        )

        response = self.client.get(
            reverse("bakery:bread-deliveries-list"),
            {"member_id": str(member1.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_filterByYearAndWeek(self):
        pl = PickupLocationFactory.create()
        member = MemberFactory.create()
        sub = SubscriptionFactory.create(member=member)
        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=sub,
            pickup_location=pl,
            bread=None,
        )
        BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK + 1,
            subscription=sub,
            pickup_location=pl,
            bread=None,
        )

        response = self.client.get(
            reverse("bakery:bread-deliveries-list"),
            {"year": YEAR, "delivery_week": WEEK},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


# ──────────────────────────────────────────────────────────────────────
# PreferredLabelViewSet
# ──────────────────────────────────────────────────────────────────────
class TestPreferredLabelViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create(is_superuser=True)
        self.client.force_login(self.member)

    def test_list_filterByMember(self):
        label = BreadLabelFactory.create(name="Vollkorn")
        pref = PreferredLabel.objects.create(member=self.member)
        pref.labels.add(label)

        other = MemberFactory.create()
        PreferredLabel.objects.create(member=other)

        response = self.client.get(
            reverse("bakery:preferred-labels-list"),
            {"member_id": str(self.member.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_bulkUpdate_replacesLabels(self):
        label1 = BreadLabelFactory.create(name="Vollkorn")
        label2 = BreadLabelFactory.create(name="Sauerteig")
        PreferredLabel.objects.create(member=self.member)

        response = self.client.post(
            reverse(
                "bakery:preferred-labels-bulk-update",
                kwargs={"pk": self.member.id},
            ),
            {"labels": [str(label1.id), str(label2.id)]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pref = PreferredLabel.objects.get(member=self.member)
        self.assertEqual(
            set(pref.labels.values_list("id", flat=True)), {label1.id, label2.id}
        )

    def test_bulkUpdate_emptyList_clearsLabels(self):
        label = BreadLabelFactory.create(name="Vollkorn")
        pref = PreferredLabel.objects.create(member=self.member)
        pref.labels.add(label)

        response = self.client.post(
            reverse(
                "bakery:preferred-labels-bulk-update",
                kwargs={"pk": self.member.id},
            ),
            data={"labels": []},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pref.refresh_from_db()
        self.assertEqual(pref.labels.count(), 0)


# ──────────────────────────────────────────────────────────────────────
# PreferredBreadViewSet
# ──────────────────────────────────────────────────────────────────────
class TestPreferredBreadViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create(is_superuser=True)
        self.client.force_login(self.member)

    def test_list_filterByMember(self):
        bread = BreadFactory.create(name="Roggenbrot")
        pref = PreferredBread.objects.create(member=self.member)
        pref.breads.add(bread)

        other = MemberFactory.create()
        PreferredBread.objects.create(member=other)

        response = self.client.get(
            reverse("bakery:preferred-breads-list"),
            {"member_id": str(self.member.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_bulkUpdate_replacesBreads(self):
        bread1 = BreadFactory.create(name="Roggenbrot")
        bread2 = BreadFactory.create(name="Weizenbrot")
        PreferredBread.objects.create(member=self.member)

        response = self.client.post(
            reverse(
                "bakery:preferred-breads-bulk-update",
                kwargs={"pk": self.member.id},
            ),
            {"breads": [str(bread1.id), str(bread2.id)]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pref = PreferredBread.objects.get(member=self.member)
        self.assertEqual(
            set(pref.breads.values_list("id", flat=True)), {bread1.id, bread2.id}
        )

    def test_bulkUpdate_createsIfNotExists(self):
        bread = BreadFactory.create(name="Roggenbrot")

        response = self.client.post(
            reverse(
                "bakery:preferred-breads-bulk-update",
                kwargs={"pk": self.member.id},
            ),
            {"breads": [str(bread.id)]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PreferredBread.objects.filter(member=self.member).exists())


# ──────────────────────────────────────────────────────────────────────
# StoveSessionViewSet
# ──────────────────────────────────────────────────────────────────────
class TestStoveSessionViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_list_filterByYearWeekDay(self):
        bread = BreadFactory.create(name="Roggenbrot")
        StoveSessionFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            delivery_day=DAY,
            bread=bread,
            session_number=1,
            layer_number=1,
        )
        StoveSessionFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            delivery_day=DAY + 1,
            bread=bread,
            session_number=1,
            layer_number=1,
        )

        response = self.client.get(
            reverse("bakery:stove-sessions-list"),
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_orderedBySessionAndLayer(self):
        bread = BreadFactory.create(name="Roggenbrot")
        StoveSessionFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            delivery_day=DAY,
            bread=bread,
            session_number=2,
            layer_number=1,
        )
        StoveSessionFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            delivery_day=DAY,
            bread=bread,
            session_number=1,
            layer_number=2,
        )
        StoveSessionFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            delivery_day=DAY,
            bread=bread,
            session_number=1,
            layer_number=1,
        )

        response = self.client.get(
            reverse("bakery:stove-sessions-list"),
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        sessions = [(s["session_number"], s["layer_number"]) for s in response.data]
        self.assertEqual(sessions, [(1, 1), (1, 2), (2, 1)])

    def test_readOnly_postNotAllowed(self):
        response = self.client.post(
            reverse("bakery:stove-sessions-list"),
            {},
            format="json",
        )

        self.assertIn(
            response.status_code,
            [status.HTTP_405_METHOD_NOT_ALLOWED, status.HTTP_403_FORBIDDEN],
        )


# ──────────────────────────────────────────────────────────────────────
# BreadsPerPickupLocationPerWeekViewSet
# ──────────────────────────────────────────────────────────────────────
class TestBreadsPerPickupLocationPerWeekViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_list_filterByYearAndWeek(self):
        pl = PickupLocationFactory.create()
        bread = BreadFactory.create(name="Roggenbrot")
        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR, delivery_week=WEEK, pickup_location=pl, bread=bread, count=5
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR,
            delivery_week=WEEK + 1,
            pickup_location=pl,
            bread=bread,
            count=3,
        )

        response = self.client.get(
            reverse("bakery:breads-per-pickup-location-per-week-list"),
            {"year": YEAR, "delivery_week": WEEK},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_filterByDeliveryDay(self):
        pl_match = create_pickup_location_with_delivery_day(DAY, name="Match")
        pl_other = create_pickup_location_with_delivery_day(DAY + 1, name="Other")
        bread = BreadFactory.create(name="Roggenbrot")

        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pl_match,
            bread=bread,
            count=5,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=pl_other,
            bread=bread,
            count=3,
        )

        response = self.client.get(
            reverse("bakery:breads-per-pickup-location-per-week-list"),
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_orderedByBreadName(self):
        pl = PickupLocationFactory.create()
        bread_z = BreadFactory.create(name="Zopf")
        bread_a = BreadFactory.create(name="Anisbrot")
        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR, delivery_week=WEEK, pickup_location=pl, bread=bread_z, count=1
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=YEAR, delivery_week=WEEK, pickup_location=pl, bread=bread_a, count=1
        )

        response = self.client.get(
            reverse("bakery:breads-per-pickup-location-per-week-list"),
            {"year": YEAR, "delivery_week": WEEK},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # bread is serialized as a PK, so use bread_name instead
        names = [r["bread_name"] for r in response.data]
        self.assertEqual(names, ["Anisbrot", "Zopf"])


# ──────────────────────────────────────────────────────────────────────
# BreadSpecificsPerDeliveryDayViewSet
# ──────────────────────────────────────────────────────────────────────
class TestBreadSpecificsPerDeliveryDayViewSet(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_list_filterByYearWeekDay(self):
        bread = BreadFactory.create(name="Roggenbrot")
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread
        )
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY + 1, bread=bread
        )

        response = self.client.get(
            reverse("bakery:bread-specifics-list"),
            {"year": YEAR, "delivery_week": WEEK, "delivery_day": DAY},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_filterByBreadId(self):
        bread1 = BreadFactory.create(name="A")
        bread2 = BreadFactory.create(name="B")
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread1
        )
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread2
        )

        response = self.client.get(
            reverse("bakery:bread-specifics-list"),
            {"bread_id": str(bread1.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_bulkUpdate_createsEntries(self):
        bread = BreadFactory.create(name="Roggenbrot")

        response = self.client.post(
            reverse("bakery:bread-specifics-bulk-update"),
            data={
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "updates": [
                    {
                        "bread": str(bread.id),
                        "min_pieces": 5,
                        "max_pieces": 20,
                        "min_remaining_pieces": 2,
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        spec = BreadSpecificsPerDeliveryDay.objects.get(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread
        )
        self.assertEqual(spec.min_pieces, 5)
        self.assertEqual(spec.max_pieces, 20)
        self.assertEqual(spec.min_remaining_pieces, 2)
        self.assertIsNone(spec.fixed_pieces)

    def test_bulkUpdate_updatesExistingEntry(self):
        bread = BreadFactory.create(name="Roggenbrot")
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            delivery_day=DAY,
            bread=bread,
            min_pieces=1,
        )

        response = self.client.post(
            reverse("bakery:bread-specifics-bulk-update"),
            data={
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "updates": [
                    {
                        "bread": str(bread.id),
                        "min_pieces": 10,
                        "max_pieces": 30,
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        spec = BreadSpecificsPerDeliveryDay.objects.get(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread
        )
        self.assertEqual(spec.min_pieces, 10)
        self.assertEqual(spec.max_pieces, 30)

    def test_bulkUpdate_allNullFields_deletesEntry(self):
        bread = BreadFactory.create(name="Roggenbrot")
        BreadSpecificsPerDeliveryDayFactory.create(
            year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread
        )

        response = self.client.post(
            reverse("bakery:bread-specifics-bulk-update"),
            data={
                "year": YEAR,
                "delivery_week": WEEK,
                "delivery_day": DAY,
                "updates": [
                    {
                        "bread": str(bread.id),
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            BreadSpecificsPerDeliveryDay.objects.filter(
                year=YEAR, delivery_week=WEEK, delivery_day=DAY, bread=bread
            ).exists()
        )
