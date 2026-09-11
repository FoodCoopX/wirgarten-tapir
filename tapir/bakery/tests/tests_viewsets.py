import datetime
from django.urls import reverse
from rest_framework import status

from tapir.bakery.models import (
    Bread,
    BreadCapacityPickupLocation,
    BreadContent,
    BreadLabel,
    BreadSpecificsPerDeliveryDay,
    Ingredient,
    PreferredBread,
)
from tapir.bakery.tests.factories import (
    BreadSubscriptionFactory,
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
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
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
        sub = BreadSubscriptionFactory.create(member=member)
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
        sub1 = BreadSubscriptionFactory.create(member=member1)
        sub2 = BreadSubscriptionFactory.create(member=member2)
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
        sub = BreadSubscriptionFactory.create(member=member)
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

    def test_bulkUpdate_unknownBreadId_returns400(self):
        # The ids go into .set(), so an unknown or over-long one has to be
        # rejected by the serializer rather than by the database.
        PreferredBread.objects.create(member=self.member)

        response = self.client.post(
            reverse(
                "bakery:preferred-breads-bulk-update", kwargs={"pk": self.member.id}
            ),
            {"breads": ["kein-brot-mit-viel-zu-langer-id"]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("breads", response.data)

    def test_create_isNotAllowed(self):
        # The serializer has no writable member, so a create could only ever
        # reach a NOT NULL violation. bulk-update is the write path.
        response = self.client.post(
            reverse("bakery:preferred-breads-list"),
            {"breads": []},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_isNotAllowed(self):
        # A TapirModel id is a plain writable CharField, so a PATCH carrying
        # "id" made Django insert a second row for the same member and break
        # the OneToOne.
        pref = PreferredBread.objects.create(member=self.member)

        response = self.client.patch(
            reverse("bakery:preferred-breads-detail", kwargs={"pk": pref.id}),
            {"id": "entfuehrt"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(
            list(PreferredBread.objects.values_list("id", flat=True)), [pref.id]
        )


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


class TestBreadDeliveryViewSetOwnership(TapirIntegrationTest):
    """A plain member must not reach another member's bread deliveries."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.attacker = MemberFactory.create()
        self.victim = MemberFactory.create()
        self.client.force_login(self.attacker)

        pl = PickupLocationFactory.create()
        self.victim_delivery = BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=BreadSubscriptionFactory.create(member=self.victim),
            pickup_location=pl,
            bread=None,
        )
        self.own_delivery = BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=BreadSubscriptionFactory.create(member=self.attacker),
            pickup_location=pl,
            bread=None,
        )

    def test_list_withoutMemberId_returnsOnlyOwnDeliveries(self):
        response = self.client.get(reverse("bakery:bread-deliveries-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], str(self.own_delivery.id))

    def test_list_withForeignMemberId_returnsNothing(self):
        response = self.client.get(
            reverse("bakery:bread-deliveries-list"),
            {"member_id": str(self.victim.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_retrieve_foreignDelivery_returns404(self):
        response = self.client.get(
            reverse("bakery:bread-deliveries-detail", args=[self.victim_delivery.id])
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_foreignDelivery_returns404(self):
        bread = BreadFactory.create(name="Roggenbrot")
        response = self.client.patch(
            reverse("bakery:bread-deliveries-detail", args=[self.victim_delivery.id]),
            {"bread": str(bread.id)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.victim_delivery.refresh_from_db()
        self.assertIsNone(self.victim_delivery.bread)

    def test_delete_notAllowed(self):
        response = self.client.delete(
            reverse("bakery:bread-deliveries-detail", args=[self.own_delivery.id])
        )

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_post_notAllowed(self):
        response = self.client.post(reverse("bakery:bread-deliveries-list"), {})

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_cannotReassignSubscriptionToStealSlot(self):
        own_subscription = self.own_delivery.subscription
        response = self.client.patch(
            reverse("bakery:bread-deliveries-detail", args=[self.own_delivery.id]),
            {"subscription": str(self.victim_delivery.subscription_id)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.own_delivery.refresh_from_db()
        self.assertEqual(self.own_delivery.subscription, own_subscription)

    def test_patch_cannotForgeJokerTaken(self):
        # joker_taken is derived from the member's jokers now, so a posted
        # value has nowhere to land - the response still reports the truth.
        response = self.client.patch(
            reverse("bakery:bread-deliveries-detail", args=[self.own_delivery.id]),
            {"joker_taken": True},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["joker_taken"])


class TestPreferredBreadViewSetOwnership(TapirIntegrationTest):
    """A plain member must not read or rewrite another member's preferences."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.attacker = MemberFactory.create()
        self.victim = MemberFactory.create()
        self.client.force_login(self.attacker)

        self.bread = BreadFactory.create(name="Roggenbrot")
        self.victim_pref = PreferredBread.objects.create(member=self.victim)
        self.victim_pref.breads.add(self.bread)
        PreferredBread.objects.create(member=self.attacker)

    def test_list_returnsOnlyOwnPreferences(self):
        response = self.client.get(reverse("bakery:preferred-breads-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["member_id"], str(self.attacker.id))

    def test_bulkUpdate_forForeignMember_returns403(self):
        other_bread = BreadFactory.create(name="Weizenbrot")
        response = self.client.post(
            reverse("bakery:preferred-breads-bulk-update", args=[self.victim.id]),
            {"breads": [str(other_bread.id)]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(list(self.victim_pref.breads.all()), [self.bread])

    def test_bulkUpdate_forSelf_isAllowed(self):
        response = self.client.post(
            reverse("bakery:preferred-breads-bulk-update", args=[self.attacker.id]),
            {"breads": [str(self.bread.id)]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestMasterdataReadWriteSplit(TapirIntegrationTest):
    """
    Members read bakery masterdata to choose their bread, but must not change
    it. Planning data is admin-only outright.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create())
        self.bread = BreadFactory.create(name="Roggenbrot")
        self.label = BreadLabelFactory.create(name="Vollkorn")
        self.ingredient = IngredientFactory.create(name="Roggenmehl")

    def test_plainMember_canReadMasterdata(self):
        for name in ("breads-list", "labels", "breadcontents"):
            with self.subTest(endpoint=name):
                response = self.client.get(reverse(f"bakery:{name}-list"))
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_plainMember_cannotCreateBread(self):
        response = self.client.post(
            reverse("bakery:breads-list-list"), {"name": "Schummelbrot", "weight": 500}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_plainMember_cannotCreateLabel(self):
        response = self.client.post(reverse("bakery:labels-list"), {"name": "Fake"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_plainMember_cannotDeleteBread(self):
        response = self.client.delete(
            reverse("bakery:breads-list-detail", args=[self.bread.id])
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_plainMember_cannotPostToBreadContentsAction(self):
        response = self.client.post(
            reverse("bakery:breads-list-contents", args=[self.bread.id]),
            {"ingredient": str(self.ingredient.id), "amount": 100},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_plainMember_canGetBreadContentsAction(self):
        response = self.client.get(
            reverse("bakery:breads-list-contents", args=[self.bread.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_plainMember_cannotReadPlanningData(self):
        for name in (
            "ingredients",
            "stove-sessions",
            "breads-per-pickup-location-per-week",
            "bread-specifics",
            "bread_capacity_pickup_location",
        ):
            with self.subTest(endpoint=name):
                response = self.client.get(reverse(f"bakery:{name}-list"))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_coopManager_canWriteMasterdata(self):
        self.client.force_login(MemberFactory.create(is_superuser=True))
        response = self.client.post(
            reverse("bakery:labels-list"), {"name": "Sauerteig"}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TestNumericQueryParams(TapirIntegrationTest):
    """
    Query-string values are parsed before they reach the ORM, where a
    non-numeric year would surface as an unhandled ValueError.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_nonNumericParams_return400(self):
        for url_name, params in [
            ("bakery:bread-deliveries-list", {"year": "abc"}),
            ("bakery:bread-deliveries-list", {"delivery_week": "??"}),
            ("bakery:breads-per-pickup-location-per-week-list", {"delivery_day": "x"}),
            ("bakery:stove-sessions-list", {"year": "nope"}),
        ]:
            with self.subTest(url_name=url_name, params=params):
                response = self.client.get(reverse(url_name), params)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_numericParams_stillWork(self):
        response = self.client.get(
            reverse("bakery:bread-deliveries-list"),
            {"year": YEAR, "delivery_week": WEEK},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_emptyParams_areIgnoredNotRejected(self):
        response = self.client.get(
            reverse("bakery:bread-deliveries-list"), {"year": ""}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestProtectedDelete(TapirIntegrationTest):
    """
    Bread and Ingredient are referenced with on_delete=PROTECT, so deleting one
    that is still in use has to come back as a 409 rather than a ProtectedError.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_deleteBread_stillChosenForAWeek_returns409(self):
        bread = BreadFactory.create(name="Roggenbrot")
        location = PickupLocationFactory.create()
        BreadCapacityPickupLocationFactory.create(
            year=2026,
            delivery_week=11,
            pickup_location=location,
            bread=bread,
            capacity=10,
        )
        BreadDeliveryFactory.create(
            year=2026, delivery_week=11, pickup_location=location, bread=bread
        )

        response = self.client.delete(
            reverse("bakery:breads-list-detail", kwargs={"pk": bread.id})
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Bread.objects.filter(id=bread.id).exists())

    def test_deleteBread_unused_isAllowed(self):
        bread = BreadFactory.create(name="Roggenbrot")

        response = self.client.delete(
            reverse("bakery:breads-list-detail", kwargs={"pk": bread.id})
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Bread.objects.filter(id=bread.id).exists())

    def test_deleteIngredient_usedInARecipe_returns409(self):
        ingredient = IngredientFactory.create(name="Roggenmehl")
        BreadContentFactory.create(
            bread=BreadFactory.create(name="Roggenbrot"),
            ingredient=ingredient,
            amount=500,
        )

        response = self.client.delete(
            reverse("bakery:ingredients-detail", kwargs={"pk": ingredient.id})
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(Ingredient.objects.filter(id=ingredient.id).exists())


class TestBreadChoiceCapacityGuard(TapirIntegrationTest):
    """
    The two rejection branches of the capacity guard inside select_for_update.
    Both are what stop a member choosing a bread the station cannot supply, and
    neither was covered - the guard could have been deleted with the suite green.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.admin = MemberFactory.create(is_superuser=True)
        self.client.force_login(self.admin)
        self.bread = BreadFactory.create(name="Roggenbrot")
        self.location = PickupLocationFactory.create()

    def _delivery(self, member=None):
        return BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            subscription=BreadSubscriptionFactory.create(
                member=member or MemberFactory.create()
            ),
            pickup_location=self.location,
            bread=None,
        )

    def test_patch_breadNotAvailableAtThatStation_returns400(self):
        # No BreadCapacityPickupLocation row at all for this bread/week/station.
        delivery = self._delivery()

        response = self.client.patch(
            reverse("bakery:bread-deliveries-detail", args=[delivery.id]),
            {"bread": str(self.bread.id)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nicht verfügbar", response.data["error"])
        delivery.refresh_from_db()
        self.assertIsNone(delivery.bread_id)

    def test_patch_capacityAlreadyTaken_returns400(self):
        BreadCapacityPickupLocationFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=self.location,
            bread=self.bread,
            capacity=1,
        )
        # The single loaf is already claimed by somebody else's slot.
        taken = self._delivery()
        taken.bread = self.bread
        taken.save()

        mine = self._delivery()

        response = self.client.patch(
            reverse("bakery:bread-deliveries-detail", args=[mine.id]),
            {"bread": str(self.bread.id)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Keine Kapazität", response.data["error"])
        mine.refresh_from_db()
        self.assertIsNone(mine.bread_id)

    def test_patch_capacityAvailable_isAccepted(self):
        BreadCapacityPickupLocationFactory.create(
            year=YEAR,
            delivery_week=WEEK,
            pickup_location=self.location,
            bread=self.bread,
            capacity=2,
        )
        delivery = self._delivery()

        response = self.client.patch(
            reverse("bakery:bread-deliveries-detail", args=[delivery.id]),
            {"bread": str(self.bread.id)},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, self.bread.id)


class TestWritableIdIsClosed(TapirIntegrationTest):
    """
    A TapirModel id is a plain editable CharField, so DRF leaves it writable
    under fields="__all__" and a PATCH carrying a forged id makes Django INSERT
    a second row instead of updating this one.
    """

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_patchBreadWithForgedId_updatesInPlaceAndCreatesNothing(self):
        bread = BreadFactory.create(name="Roggenbrot")
        before = Bread.objects.count()

        response = self.client.patch(
            reverse("bakery:breads-list-detail", args=[bread.id]),
            {"id": "GEFAELSCHT", "name": "Umbenannt"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Bread.objects.count(), before)
        self.assertFalse(Bread.objects.filter(id="GEFAELSCHT").exists())
        bread.refresh_from_db()
        self.assertEqual(bread.name, "Umbenannt")

    def test_patchLabelWithForgedId_createsNothing(self):
        label = BreadLabelFactory.create(name="Vollkorn")
        before = BreadLabel.objects.count()

        self.client.patch(
            reverse("bakery:labels-detail", args=[label.id]),
            {"id": "GEFAELSCHT", "name": "Dinkel"},
            content_type="application/json",
        )

        self.assertEqual(BreadLabel.objects.count(), before)
        self.assertFalse(BreadLabel.objects.filter(id="GEFAELSCHT").exists())


class TestPreferredBreadsBulkUpdateValidation(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create(is_superuser=True)
        self.client.force_login(self.member)

    def test_unknownMemberId_returns404NotAServerError(self):
        # The FK is DEFERRABLE INITIALLY DEFERRED, so an unknown id survives
        # get_or_create and would otherwise fail as an IntegrityError at commit.
        response = self.client.post(
            reverse("bakery:preferred-breads-bulk-update", kwargs={"pk": "NICHTDA123"}),
            {"breads": []},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_moreThanTheLimit_returns400(self):
        # Enforced on the server too: favouriting every bread would make a
        # member trivially satisfied in the metrics and multiply their weight
        # in the solver.
        breads = [BreadFactory.create(name=f"Brot {i}") for i in range(4)]

        response = self.client.post(
            reverse(
                "bakery:preferred-breads-bulk-update", kwargs={"pk": self.member.id}
            ),
            {"breads": [str(bread.id) for bread in breads]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PreferredBread.objects.filter(member=self.member).exists())

    def test_theSameBreadTwice_returns400(self):
        bread = BreadFactory.create(name="Roggenbrot")

        response = self.client.post(
            reverse(
                "bakery:preferred-breads-bulk-update", kwargs={"pk": self.member.id}
            ),
            {"breads": [str(bread.id), str(bread.id)]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_exactlyTheLimit_isAccepted(self):
        breads = [BreadFactory.create(name=f"Brot {i}") for i in range(3)]

        response = self.client.post(
            reverse(
                "bakery:preferred-breads-bulk-update", kwargs={"pk": self.member.id}
            ),
            {"breads": [str(bread.id) for bread in breads]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            PreferredBread.objects.get(member=self.member).breads.count(), 3
        )


class TestCapacityBulkUpdateValidation(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.client.force_login(MemberFactory.create(is_superuser=True))

    def test_negativeCapacity_returns400NotAServerError(self):
        # The column carries CHECK (capacity >= 0), so a negative value has to
        # be rejected before it reaches the database.
        bread = BreadFactory.create(name="Roggenbrot")
        location = PickupLocationFactory.create()

        response = self.client.post(
            reverse("bakery:bread_capacity_pickup_location-bulk-update"),
            {
                "year": YEAR,
                "delivery_week": WEEK,
                "updates": [
                    {
                        "pickup_location": str(location.id),
                        "bread": str(bread.id),
                        "capacity": -5,
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(BreadCapacityPickupLocation.objects.exists())


class TestBreadChoiceDeadline(TapirIntegrationTest):
    """
    The two rules a member is bound by when picking a bread, which staff on the
    phone are not. Both are reached only as a plain member: a superuser takes
    the Accounts.MANAGE short-circuit above them.
    """

    PAST_YEAR = 2025
    PAST_WEEK = 3

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create()
        self.client.force_login(self.member)
        self.bread = BreadFactory.create(name="Roggenbrot")
        self.location = PickupLocationFactory.create()
        PickupLocationOpeningTime.objects.create(
            pickup_location=self.location,
            day_of_week=3,
            open_time=datetime.time(8),
            close_time=datetime.time(18),
        )

    def _delivery(self, year, week, member=None):
        BreadCapacityPickupLocationFactory.create(
            year=year,
            delivery_week=week,
            pickup_location=self.location,
            bread=self.bread,
            capacity=10,
        )
        return BreadDeliveryFactory.create(
            year=year,
            delivery_week=week,
            subscription=BreadSubscriptionFactory.create(member=member or self.member),
            pickup_location=self.location,
            bread=None,
        )

    def _patch(self, delivery, payload):
        return self.client.patch(
            reverse("bakery:bread-deliveries-detail", args=[delivery.id]),
            payload,
            content_type="application/json",
        )

    def test_patch_choosingSwitchedOff_returns400(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BAKERY_MEMBERS_CAN_CHOOSE_BREAD_SORTS
        ).update(value="False")
        delivery = self._delivery(YEAR, WEEK)

        response = self._patch(delivery, {"bread": str(self.bread.id)})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("nicht freigegeben", response.data["error"])
        delivery.refresh_from_db()
        self.assertIsNone(delivery.bread_id)

    def test_patch_afterTheDeadline_returns400(self):
        delivery = self._delivery(self.PAST_YEAR, self.PAST_WEEK)

        response = self._patch(delivery, {"bread": str(self.bread.id)})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("abgelaufen", response.data["error"])
        delivery.refresh_from_db()
        self.assertIsNone(delivery.bread_id)

    def test_patch_clearingTheChoiceAfterTheDeadline_returns400(self):
        # An explicit null is a change like any other, so it is subject to the
        # deadline: a member must not withdraw a loaf after the baking list is
        # fixed.
        delivery = self._delivery(self.PAST_YEAR, self.PAST_WEEK)
        delivery.bread = self.bread
        delivery.save()

        response = self._patch(delivery, {"bread": None})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, self.bread.id)

    def test_patch_afterTheDeadline_staffAreNotBound(self):
        delivery = self._delivery(self.PAST_YEAR, self.PAST_WEEK)
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self._patch(delivery, {"bread": str(self.bread.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, self.bread.id)

    def test_patch_withinTheDeadline_isAccepted(self):
        year, week = datetime.date.today().isocalendar()[:2]
        delivery = self._delivery(year, week + 4)

        response = self._patch(delivery, {"bread": str(self.bread.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
