import datetime

from tapir.deliveries.services.joker_management_service import JokerManagementService
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestDoesMemberHaveADeliveryAffectedByJokersInWeek(TapirIntegrationTest):
    # 15.01.2020 is in the odd week 3
    REFERENCE_DATE = datetime.date(year=2020, month=1, day=15)

    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2020, month=1, day=1)
        )

    def setUp(self) -> None:
        super().setUp()
        self.member = MemberFactory.create()

    def create_subscription(self, delivery_cycle: str, is_affected_by_jokers: bool):
        SubscriptionFactory.create(
            member=self.member,
            period=self.growing_period,
            product__type__delivery_cycle=delivery_cycle,
            product__type__is_affected_by_jokers=is_affected_by_jokers,
        )

    def does_member_have_delivery(self):
        return JokerManagementService.does_member_have_a_delivery_affected_by_jokers_in_week(
            member=self.member, reference_date=self.REFERENCE_DATE, cache={}
        )

    def test_doesMemberHaveADeliveryAffectedByJokersInWeek_affectedSubscriptionDelivered_returnsTrue(
        self,
    ):
        self.create_subscription(delivery_cycle=WEEKLY[0], is_affected_by_jokers=True)

        self.assertTrue(self.does_member_have_delivery())

    def test_doesMemberHaveADeliveryAffectedByJokersInWeek_onlyUnaffectedSubscriptionDelivered_returnsFalse(
        self,
    ):
        self.create_subscription(delivery_cycle=WEEKLY[0], is_affected_by_jokers=False)

        self.assertFalse(self.does_member_have_delivery())

    def test_doesMemberHaveADeliveryAffectedByJokersInWeek_affectedSubscriptionNotDeliveredThisWeek_returnsFalse(
        self,
    ):
        self.create_subscription(
            delivery_cycle=EVEN_WEEKS[0], is_affected_by_jokers=True
        )
        self.create_subscription(delivery_cycle=WEEKLY[0], is_affected_by_jokers=False)

        self.assertFalse(self.does_member_have_delivery())

    def test_doesMemberHaveADeliveryAffectedByJokersInWeek_noSubscription_returnsFalse(
        self,
    ):
        self.assertFalse(self.does_member_have_delivery())

    def test_doesMemberHaveADeliveryAffectedByJokersInWeek_subscriptionOfOtherMember_returnsFalse(
        self,
    ):
        SubscriptionFactory.create(
            period=self.growing_period,
            product__type__delivery_cycle=WEEKLY[0],
            product__type__is_affected_by_jokers=True,
        )

        self.assertFalse(self.does_member_have_delivery())
