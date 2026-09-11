import datetime

from django.urls import reverse
from rest_framework import status

from tapir.bakery.services.bread_choice_deadline_service import (
    BreadChoiceDeadlineService,
)
from tapir.bakery.tests.factories import (
    BreadCapacityPickupLocationFactory,
    BreadDeliveryFactory,
    BreadFactory,
    BreadSubscriptionFactory,
)
from tapir.bakery.tests.tests_viewsets import create_pickup_location_with_delivery_day
from tapir.configuration.models import TapirParameter
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import MemberFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest
from tapir.wirgarten.utils import get_today

DAY = 4  # Freitag


class TestBreadChoiceDeadline(TapirIntegrationTest):
    """The deadline is enforced on the server, not only in the browser."""

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        self.pickup_location = create_pickup_location_with_delivery_day(DAY)
        self.bread = BreadFactory.create()

    def _delivery(self, member, year, week):
        BreadCapacityPickupLocationFactory.create(
            year=year,
            delivery_week=week,
            pickup_location=self.pickup_location,
            bread=self.bread,
            capacity=10,
        )
        return BreadDeliveryFactory.create(
            year=year,
            delivery_week=week,
            subscription=BreadSubscriptionFactory.create(member=member),
            pickup_location=self.pickup_location,
            bread=None,
        )

    def _patch(self, delivery):
        return self.client.patch(
            reverse("bakery:bread-deliveries-detail", args=[delivery.id]),
            {"bread": str(self.bread.id)},
            content_type="application/json",
        )

    # ── the rule itself ───────────────────────────────────────────────

    def test_getDeadline_isBakingAndChoosingOffsetsBeforeTheStationsDeliveryDay(self):
        # Seeded offsets are 1 baking day + 2 choosing days = 3.
        year, week, _ = get_today().isocalendar()
        deadline = BreadChoiceDeadlineService.get_deadline(
            year, week, self.pickup_location.id, cache={}
        )
        delivery_date = BreadChoiceDeadlineService.get_delivery_date(
            year, week, self.pickup_location.id, cache={}
        )

        self.assertEqual(delivery_date.weekday(), DAY)
        self.assertEqual((delivery_date - deadline).days, 3)

    def test_canStillChoose_stationWithNoOpeningTimes_staysOpen(self):
        # Nothing to enforce against, so missing setup must not block a member.
        from tapir.wirgarten.tests.factories import PickupLocationFactory

        year, week, _ = get_today().isocalendar()
        self.assertTrue(
            BreadChoiceDeadlineService.can_still_choose(
                year, week, PickupLocationFactory.create().id, cache={}
            )
        )

    # ── enforcement on the write path ─────────────────────────────────

    def test_patch_weekWhoseDeadlineHasPassed_isRejected(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        delivery = self._delivery(member, 2020, 5)

        response = self._patch(delivery)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Frist", response.json()["error"])
        delivery.refresh_from_db()
        self.assertIsNone(delivery.bread)

    def test_patch_wellBeforeTheDeadline_isAccepted(self):
        member = MemberFactory.create()
        self.client.force_login(member)
        later = get_today() + datetime.timedelta(weeks=3)
        year, week, _ = later.isocalendar()
        delivery = self._delivery(member, year, week)

        response = self._patch(delivery)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, self.bread.id)

    def test_patch_membersMayNotChoose_isRejected(self):
        TapirParameter.objects.filter(
            key=ParameterKeys.BAKERY_MEMBERS_CAN_CHOOSE_BREAD_SORTS
        ).update(value="False")
        member = MemberFactory.create()
        self.client.force_login(member)
        later = get_today() + datetime.timedelta(weeks=3)
        year, week, _ = later.isocalendar()
        delivery = self._delivery(member, year, week)

        response = self._patch(delivery)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("freigegeben", response.json()["error"])

    def test_patch_staffAfterTheDeadline_isAccepted(self):
        # Someone answering the phone has to be able to fix a past week.
        member = MemberFactory.create()
        delivery = self._delivery(member, 2020, 7)
        self.client.force_login(MemberFactory.create(is_superuser=True))

        response = self._patch(delivery)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        delivery.refresh_from_db()
        self.assertEqual(delivery.bread_id, self.bread.id)
