import datetime

from tapir.mail.models import StaticSegmentRecipient

from tapir.bakery.services.bread_mail_token_service import BreadMailTokenService
from tapir.bakery.tests.factories import (
    AvailableBreadsForDeliveryDayFactory,
    BreadContentFactory,
    BreadDeliveryFactory,
    BreadFactory,
    BreadSubscriptionFactory,
    IngredientFactory,
)
from tapir.wirgarten.models import Member, PickupLocation
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationFactory,
    PickupLocationOpeningTimesFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone

YEAR = 2026
THIS_WEEK = 11  # Monday 2026-03-09
NEXT_WEEK = 12


class TestBreadMailTokenService(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def setUp(self):
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(2026, 3, 9, 12, 0))

    @staticmethod
    def _create_pickup_location(delivery_day: int) -> PickupLocation:
        pickup_location = PickupLocationFactory.create()
        PickupLocationOpeningTimesFactory.create(
            pickup_location=pickup_location, day_of_week=delivery_day
        )
        return pickup_location

    @staticmethod
    def _create_member_with_bread_delivery(
        pickup_location: PickupLocation | None,
        week: int = THIS_WEEK,
        joker_taken: bool = False,
    ) -> Member:
        delivery = BreadDeliveryFactory.create(
            year=YEAR,
            delivery_week=week,
            subscription=BreadSubscriptionFactory.create(),
            pickup_location=pickup_location,
            joker_taken=joker_taken,
            bread=None,
        )
        return delivery.subscription.member

    @staticmethod
    def _bake(
        name: str,
        delivery_day: int,
        description: str = "",
        ingredients: tuple[str, ...] = (),
        week: int = THIS_WEEK,
        is_active: bool = True,
    ):
        bread = BreadFactory.create(
            name=name, description=description, is_active=is_active
        )
        for sort_order, ingredient_name in enumerate(ingredients):
            BreadContentFactory.create(
                bread=bread,
                ingredient=IngredientFactory.create(name=ingredient_name),
                sort_order=sort_order,
            )
        AvailableBreadsForDeliveryDayFactory.create(
            year=YEAR, delivery_week=week, delivery_day=delivery_day, bread=bread
        )

    def test_breadsThisWeek_default_returnsDayAndBreadsSortedByName(self):
        pickup_location = self._create_pickup_location(delivery_day=1)
        member = self._create_member_with_bread_delivery(
            pickup_location=pickup_location
        )
        self._bake(
            name="Roggenbrot",
            delivery_day=1,
            description="Kräftig",
            ingredients=("Roggen", "Salz"),
        )
        self._bake(
            name="Dinkelkruste",
            delivery_day=1,
            description="Mild & locker",
            ingredients=("Dinkel",),
        )

        self.assertEqual(
            "Dienstag, 10.03.2026<br>"
            "Dinkelkruste<br>Mild &amp; locker<br>Zutaten: Dinkel<br><br>"
            "Roggenbrot<br>Kräftig<br>Zutaten: Roggen, Salz",
            BreadMailTokenService.breads_this_week(recipient=member, cache={}),
        )

    def test_breadsThisWeek_breadWithoutDescriptionNorIngredients_skipsEmptyLines(
        self,
    ):
        pickup_location = self._create_pickup_location(delivery_day=1)
        member = self._create_member_with_bread_delivery(
            pickup_location=pickup_location
        )
        self._bake(name="Roggenbrot", delivery_day=1)

        self.assertEqual(
            "Dienstag, 10.03.2026<br>Roggenbrot",
            BreadMailTokenService.breads_this_week(recipient=member, cache={}),
        )

    def test_breadsThisWeek_breadBakedOnAnotherDay_isNotListed(self):
        pickup_location = self._create_pickup_location(delivery_day=1)
        member = self._create_member_with_bread_delivery(
            pickup_location=pickup_location
        )
        self._bake(name="Roggenbrot", delivery_day=1)
        self._bake(name="Dinkelkruste", delivery_day=3)

        self.assertEqual(
            "Dienstag, 10.03.2026<br>Roggenbrot",
            BreadMailTokenService.breads_this_week(recipient=member, cache={}),
        )

    def test_breadsThisWeek_inactiveBread_isNotListed(self):
        pickup_location = self._create_pickup_location(delivery_day=1)
        member = self._create_member_with_bread_delivery(
            pickup_location=pickup_location
        )
        self._bake(name="Roggenbrot", delivery_day=1)
        self._bake(name="Dinkelkruste", delivery_day=1, is_active=False)

        self.assertEqual(
            "Dienstag, 10.03.2026<br>Roggenbrot",
            BreadMailTokenService.breads_this_week(recipient=member, cache={}),
        )

    def test_breadsThisWeek_recipientIsNotAMember_returnsNotApplicable(self):
        self.assertEqual(
            BreadMailTokenService.NOT_APPLICABLE,
            BreadMailTokenService.breads_this_week(
                recipient=StaticSegmentRecipient(email="extern@example.com"),
                cache={},
            ),
        )

    def test_breadsThisWeek_memberWithoutBreadDelivery_returnsNotApplicable(self):
        pickup_location = self._create_pickup_location(delivery_day=1)
        member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=pickup_location,
            valid_from=datetime.date(2000, 1, 1),
        )
        self._bake(name="Roggenbrot", delivery_day=1)

        self.assertEqual(
            BreadMailTokenService.NOT_APPLICABLE,
            BreadMailTokenService.breads_this_week(recipient=member, cache={}),
        )

    def test_breadsThisWeek_jokerTaken_returnsJokerTaken(self):
        pickup_location = self._create_pickup_location(delivery_day=1)
        member = self._create_member_with_bread_delivery(
            pickup_location=pickup_location, joker_taken=True
        )
        self._bake(name="Roggenbrot", delivery_day=1)

        self.assertEqual(
            BreadMailTokenService.JOKER_TAKEN,
            BreadMailTokenService.breads_this_week(recipient=member, cache={}),
        )

    def test_breadsThisWeek_memberWithoutPickupLocation_returnsNotApplicable(self):
        member = self._create_member_with_bread_delivery(pickup_location=None)

        self.assertEqual(
            BreadMailTokenService.NOT_APPLICABLE,
            BreadMailTokenService.breads_this_week(recipient=member, cache={}),
        )

    def test_breadsThisWeek_noBreadsBakedYet_returnsBreadsNotSetYet(self):
        pickup_location = self._create_pickup_location(delivery_day=1)
        member = self._create_member_with_bread_delivery(
            pickup_location=pickup_location
        )

        self.assertEqual(
            BreadMailTokenService.BREADS_NOT_SET_YET,
            BreadMailTokenService.breads_this_week(recipient=member, cache={}),
        )

    def test_breadsNextWeek_default_usesNextWeeksPickupLocationAndBreads(self):
        old_pickup_location = self._create_pickup_location(delivery_day=1)
        new_pickup_location = self._create_pickup_location(delivery_day=3)
        member = self._create_member_with_bread_delivery(
            pickup_location=old_pickup_location, week=NEXT_WEEK
        )
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=new_pickup_location,
            valid_from=datetime.date(2026, 3, 16),
        )
        self._bake(name="Roggenbrot", delivery_day=1, week=NEXT_WEEK)
        self._bake(name="Dinkelkruste", delivery_day=3, week=NEXT_WEEK)
        self._bake(name="Vollkornbrot", delivery_day=3)

        self.assertEqual(
            "Donnerstag, 19.03.2026<br>Dinkelkruste",
            BreadMailTokenService.breads_next_week(recipient=member, cache={}),
        )
