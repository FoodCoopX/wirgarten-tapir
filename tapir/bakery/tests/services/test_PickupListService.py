from unittest.mock import patch

from tapir.bakery.services.pickup_list_service import PickupListService
from tapir.bakery.tests.factories import (
    BreadDeliveryFactory,
    BreadFactory,
    BreadsPerPickupLocationPerWeekFactory,
    PreferredBreadFactory,
)
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    PickupLocationFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, set_bypass_keycloak


@patch("tapir.wirgarten.tests.factories.KeycloakUserManager.get_keycloak_client")
class TestPickupListService(TapirIntegrationTest):
    YEAR = 2026
    WEEK = 11

    def setUp(self):
        super().setUp()
        set_bypass_keycloak()
        self.pickup_location = PickupLocationFactory.create()
        self.roggenbrot = BreadFactory.create(name="Roggenbrot")
        self.dinkelkruste = BreadFactory.create(name="Dinkelkruste")

    def _create_member_with_subscription(self, first_name="Anna", last_name="Müller"):
        member = MemberFactory.create(first_name=first_name, last_name=last_name)
        subscription = SubscriptionFactory.create(member=member)
        return member, subscription

    def _create_delivery(self, subscription, bread=None):
        return BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=subscription,
            pickup_location=self.pickup_location,
            bread=bread,
        )

    # ── No data ──────────────────────────────────────────────────────

    def test_getPickupList_noDeliveriesExist_returnsEmptyResult(self, mock_kc):
        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["entries"], [])
        self.assertEqual(result["bread_names"], [])
        self.assertEqual(result["grand_total"], 0)
        self.assertEqual(result["bread_totals"], {})

    # ── Single delivery ──────────────────────────────────────────────

    def test_getPickupList_oneDeliveryWithBread_returnsCorrectCounts(self, mock_kc):
        _member, subscription = self._create_member_with_subscription()
        self._create_delivery(subscription, bread=self.roggenbrot)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(len(result["entries"]), 1)

        entry = result["entries"][0]
        self.assertEqual(entry["bread_counts"].get("Roggenbrot"), 1)
        self.assertEqual(entry["total"], 1)
        self.assertEqual(entry["total_assigned"], 1)
        self.assertEqual(result["grand_total"], 1)
        self.assertEqual(result["bread_totals"]["Roggenbrot"], 1)

    def test_getPickupList_deliveryWithNoBreadAssigned_countsTotalButNotAssigned(
        self, mock_kc
    ):
        _member, subscription = self._create_member_with_subscription(
            first_name="Ben", last_name="Schmidt"
        )
        self._create_delivery(subscription, bread=None)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        entry = result["entries"][0]
        self.assertEqual(entry["total"], 1)
        self.assertEqual(entry["total_assigned"], 0)
        self.assertEqual(entry["bread_counts"], {})
        self.assertEqual(entry["breads"], [])

    # ── Multiple members / breads ────────────────────────────────────

    def test_getPickupList_multipleMembersMultipleBreads_totalsAreCorrect(
        self, mock_kc
    ):
        _anna, sub_anna = self._create_member_with_subscription(
            first_name="Anna", last_name="Müller"
        )
        _ben, sub_ben = self._create_member_with_subscription(
            first_name="Ben", last_name="Schmidt"
        )

        self._create_delivery(sub_anna, bread=self.roggenbrot)
        self._create_delivery(sub_anna, bread=self.dinkelkruste)
        self._create_delivery(sub_ben, bread=self.roggenbrot)
        self._create_delivery(sub_ben, bread=self.roggenbrot)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(len(result["entries"]), 2)
        self.assertEqual(result["bread_totals"]["Roggenbrot"], 3)
        self.assertEqual(result["bread_totals"]["Dinkelkruste"], 1)
        self.assertEqual(result["grand_total"], 4)

    # ── Sorting ──────────────────────────────────────────────────────

    def test_getPickupList_multipleMembers_entriesSortedByMemberName(self, mock_kc):
        _ben, sub_ben = self._create_member_with_subscription(
            first_name="Ben", last_name="Schmidt"
        )
        _anna, sub_anna = self._create_member_with_subscription(
            first_name="Anna", last_name="Müller"
        )

        self._create_delivery(sub_ben, bread=self.roggenbrot)
        self._create_delivery(sub_anna, bread=self.dinkelkruste)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        names = [e["member_name"] for e in result["entries"]]
        self.assertEqual(names, sorted(names, key=str.lower))

    def test_getPickupList_breadNamesAreSortedAlphabetically(self, mock_kc):
        _member, subscription = self._create_member_with_subscription()
        self._create_delivery(subscription, bread=self.roggenbrot)
        self._create_delivery(subscription, bread=self.dinkelkruste)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["bread_names"], ["Dinkelkruste", "Roggenbrot"])

    # ── Display name ─────────────────────────────────────────────────

    def test_getPickupList_memberWithLastName_displaysInitialAndFirstName(
        self, mock_kc
    ):
        _member, subscription = self._create_member_with_subscription(
            first_name="Anna", last_name="Müller"
        )
        self._create_delivery(subscription, bread=self.roggenbrot)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["entries"][0]["member_name"], "M., Anna")

    def test_getPickupList_memberWithNoLastName_displaysFirstNameOnly(self, mock_kc):
        _member, subscription = self._create_member_with_subscription(
            first_name="Anna", last_name=""
        )
        self._create_delivery(subscription, bread=self.roggenbrot)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["entries"][0]["member_name"], "Anna")

    def test_getPickupList_memberWithNoName_displaysUnbekannt(self, mock_kc):
        _member, subscription = self._create_member_with_subscription(
            first_name="", last_name=""
        )
        self._create_delivery(subscription, bread=self.roggenbrot)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["entries"][0]["member_name"], "Unbekannt")

    # ── Preferred breads ─────────────────────────────────────────────

    def test_getPickupList_preferredBreadNotDelivered_breadPreferredIsTrue(
        self, mock_kc
    ):
        member, subscription = self._create_member_with_subscription()
        self._create_delivery(subscription, bread=self.roggenbrot)

        pref = PreferredBreadFactory.create(member=member)
        pref.breads.add(self.dinkelkruste)

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=self.pickup_location,
            bread=self.dinkelkruste,
        )

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        entry = result["entries"][0]
        self.assertTrue(entry["bread_preferred"]["Dinkelkruste"])
        self.assertFalse(entry["bread_preferred"]["Roggenbrot"])

    def test_getPickupList_preferredBreadIsDelivered_breadPreferredIsFalse(
        self, mock_kc
    ):
        member, subscription = self._create_member_with_subscription()
        self._create_delivery(subscription, bread=self.roggenbrot)

        pref = PreferredBreadFactory.create(member=member)
        pref.breads.add(self.roggenbrot)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        entry = result["entries"][0]
        self.assertFalse(entry["bread_preferred"]["Roggenbrot"])

    def test_getPickupList_memberWithNoPreferences_allBreadPreferredAreFalse(
        self, mock_kc
    ):
        _member, subscription = self._create_member_with_subscription()
        self._create_delivery(subscription, bread=self.roggenbrot)

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=self.pickup_location,
            bread=self.dinkelkruste,
        )

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        entry = result["entries"][0]
        self.assertFalse(entry["bread_preferred"]["Roggenbrot"])
        self.assertFalse(entry["bread_preferred"]["Dinkelkruste"])

    def test_getPickupList_memberPrefersMultipleBreads_onlyUndeliveredShowAsPreferred(
        self, mock_kc
    ):
        member, subscription = self._create_member_with_subscription()
        vollkornbrot = BreadFactory.create(name="Vollkornbrot")
        self._create_delivery(subscription, bread=self.roggenbrot)

        pref = PreferredBreadFactory.create(member=member)
        pref.breads.add(self.roggenbrot, self.dinkelkruste, vollkornbrot)

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=self.pickup_location,
            bread=self.dinkelkruste,
        )
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=self.pickup_location,
            bread=vollkornbrot,
        )

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        entry = result["entries"][0]
        # Roggenbrot is preferred BUT already delivered → False
        self.assertFalse(entry["bread_preferred"]["Roggenbrot"])
        # Dinkelkruste and Vollkornbrot are preferred and NOT delivered → True
        self.assertTrue(entry["bread_preferred"]["Dinkelkruste"])
        self.assertTrue(entry["bread_preferred"]["Vollkornbrot"])

    # ── Bread names ──────────────────────────────────────────────────

    def test_getPickupList_breadNamesIncludeAssignedAndDelivered(self, mock_kc):
        _member, subscription = self._create_member_with_subscription()
        self._create_delivery(subscription, bread=self.roggenbrot)

        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=self.pickup_location,
            bread=self.dinkelkruste,
        )

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertIn("Roggenbrot", result["bread_names"])
        self.assertIn("Dinkelkruste", result["bread_names"])

    def test_getPickupList_onlyAssignedBreadsNoDeliveries_breadNamesStillPresent(
        self, mock_kc
    ):
        BreadsPerPickupLocationPerWeekFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            pickup_location=self.pickup_location,
            bread=self.roggenbrot,
        )

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        # No deliveries → no entries, but assigned bread names should appear
        self.assertEqual(result["entries"], [])
        self.assertIn("Roggenbrot", result["bread_names"])

    # ── Filtering ────────────────────────────────────────────────────

    def test_getPickupList_differentPickupLocation_doesNotIncludeThoseDeliveries(
        self, mock_kc
    ):
        other_location = PickupLocationFactory.create()

        _member, subscription = self._create_member_with_subscription()
        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=self.WEEK,
            subscription=subscription,
            pickup_location=other_location,
            bread=self.roggenbrot,
        )

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["entries"], [])
        self.assertEqual(result["grand_total"], 0)

    def test_getPickupList_differentWeek_doesNotIncludeThoseDeliveries(self, mock_kc):
        _member, subscription = self._create_member_with_subscription()
        BreadDeliveryFactory.create(
            year=self.YEAR,
            delivery_week=12,
            subscription=subscription,
            pickup_location=self.pickup_location,
            bread=self.roggenbrot,
        )

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["entries"], [])
        self.assertEqual(result["grand_total"], 0)

    def test_getPickupList_differentYear_doesNotIncludeThoseDeliveries(self, mock_kc):
        _member, subscription = self._create_member_with_subscription()
        BreadDeliveryFactory.create(
            year=2025,
            delivery_week=self.WEEK,
            subscription=subscription,
            pickup_location=self.pickup_location,
            bread=self.roggenbrot,
        )

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["entries"], [])
        self.assertEqual(result["grand_total"], 0)

    # ── Breads list per entry ────────────────────────────────────────

    def test_getPickupList_sameMemberMultipleBreads_breadsListIsComplete(self, mock_kc):
        _member, subscription = self._create_member_with_subscription()
        delivery1 = self._create_delivery(subscription, bread=self.roggenbrot)
        delivery2 = self._create_delivery(subscription, bread=self.dinkelkruste)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        entry = result["entries"][0]
        bread_list = entry["breads"]
        self.assertEqual(len(bread_list), 2)

        delivery_ids = {b["delivery_id"] for b in bread_list}
        self.assertIn(str(delivery1.id), delivery_ids)
        self.assertIn(str(delivery2.id), delivery_ids)

        bread_names = {b["bread_name"] for b in bread_list}
        self.assertEqual(bread_names, {"Roggenbrot", "Dinkelkruste"})

    def test_getPickupList_unassignedDelivery_breadsListDoesNotIncludeIt(self, mock_kc):
        _member, subscription = self._create_member_with_subscription()
        assigned = self._create_delivery(subscription, bread=self.roggenbrot)
        self._create_delivery(subscription, bread=None)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        entry = result["entries"][0]
        self.assertEqual(len(entry["breads"]), 1)
        self.assertEqual(entry["breads"][0]["delivery_id"], str(assigned.id))
        self.assertEqual(entry["breads"][0]["bread_name"], "Roggenbrot")

    # ── Same bread multiple times ────────────────────────────────────

    def test_getPickupList_sameBreadTwice_breadCountIsTwo(self, mock_kc):
        _member, subscription = self._create_member_with_subscription()
        self._create_delivery(subscription, bread=self.roggenbrot)
        self._create_delivery(subscription, bread=self.roggenbrot)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        entry = result["entries"][0]
        self.assertEqual(entry["bread_counts"]["Roggenbrot"], 2)
        self.assertEqual(entry["total"], 2)
        self.assertEqual(entry["total_assigned"], 2)
        self.assertEqual(len(entry["breads"]), 2)

    # ── Member ID ────────────────────────────────────────────────────

    def test_getPickupList_entryContainsCorrectMemberId(self, mock_kc):
        member, subscription = self._create_member_with_subscription()
        self._create_delivery(subscription, bread=self.roggenbrot)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["entries"][0]["member_id"], str(member.id))

    # ── Mixed assigned and unassigned across members ─────────────────

    def test_getPickupList_mixedAssignedAndUnassigned_grandTotalCountsAll(
        self, mock_kc
    ):
        _anna, sub_anna = self._create_member_with_subscription(
            first_name="Anna", last_name="Müller"
        )
        _ben, sub_ben = self._create_member_with_subscription(
            first_name="Ben", last_name="Schmidt"
        )

        self._create_delivery(sub_anna, bread=self.roggenbrot)
        self._create_delivery(sub_anna, bread=None)
        self._create_delivery(sub_ben, bread=self.dinkelkruste)

        result = PickupListService.get_pickup_list(
            year=self.YEAR,
            week=self.WEEK,
            pickup_location_id=self.pickup_location.id,
        )

        self.assertEqual(result["grand_total"], 3)
        # bread_totals should only count assigned breads
        self.assertEqual(result["bread_totals"].get("Roggenbrot", 0), 1)
        self.assertEqual(result["bread_totals"].get("Dinkelkruste", 0), 1)
