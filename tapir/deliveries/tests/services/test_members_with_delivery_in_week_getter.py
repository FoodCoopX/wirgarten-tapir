import datetime

from tapir.deliveries.config import DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE
from tapir.deliveries.services.members_with_delivery_in_week_getter import (
    MembersWithDeliveryInWeekGetter,
)
from tapir.deliveries.tests.factories import DeliveryDonationFactory, JokerFactory
from tapir.wirgarten.constants import WEEKLY, EVEN_WEEKS
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    ProductTypeFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


class TestMembersWithDeliveryInWeekGetter(TapirIntegrationTest):
    TODAY = datetime.date(year=2031, month=4, day=14)  # monday of week 16
    DELIVERY_DATE = datetime.date(year=2031, month=4, day=16)

    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(key=ParameterKeys.DELIVERY_DAY, value=2)
        cls._set_parameter(key=ParameterKeys.JOKERS_ENABLED, value=True)
        cls._set_parameter(
            key=ParameterKeys.DELIVERY_DONATION_MODE,
            value=DELIVERY_DONATION_MODE_ALWAYS_POSSIBLE,
        )

    def setUp(self):
        super().setUp()
        mock_timezone(
            test=self, now=datetime.datetime.combine(self.TODAY, datetime.time(10))
        )
        self.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2031, month=1, day=1),
            end_date=datetime.date(year=2031, month=12, day=31),
        )
        self.product_type = ProductTypeFactory.create(delivery_cycle=WEEKLY[0])

    def _get_members_with_delivery_in_week(
        self, reference_date: datetime.date | None = None
    ):
        return list(
            MembersWithDeliveryInWeekGetter.get_members_with_delivery_in_week(
                product_type=self.product_type,
                reference_date=reference_date or self.TODAY,
                cache={},
            )
        )

    def _create_member_with_subscription(self, product_type=None):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            period=self.growing_period,
            product__type=product_type or self.product_type,
        )
        return member

    def test_getMembersWithDeliveryInWeek_memberWithSubscription_memberIncluded(self):
        member = self._create_member_with_subscription()

        self.assertEqual([member], self._get_members_with_delivery_in_week())

    def test_getMembersWithDeliveryInWeek_subscriptionForOtherProductType_memberNotIncluded(
        self,
    ):
        self._create_member_with_subscription(
            product_type=ProductTypeFactory.create(delivery_cycle=WEEKLY[0])
        )

        self.assertEqual([], self._get_members_with_delivery_in_week())

    def test_getMembersWithDeliveryInWeek_subscriptionEndsBeforeEndOfWeek_memberNotIncluded(
        self,
    ):
        SubscriptionFactory.create(
            period=self.growing_period,
            product__type=self.product_type,
            end_date=self.DELIVERY_DATE,
        )

        self.assertEqual([], self._get_members_with_delivery_in_week())

    def test_getMembersWithDeliveryInWeek_weekWithoutDelivery_noMembers(self):
        self._create_member_with_subscription()
        self.growing_period.weeks_without_delivery = [
            self.DELIVERY_DATE.isocalendar().week
        ]
        self.growing_period.save()

        self.assertEqual([], self._get_members_with_delivery_in_week())

    def test_getMembersWithDeliveryInWeek_productTypeNotDeliveredInGivenWeek_noMembers(
        self,
    ):
        self.product_type.delivery_cycle = EVEN_WEEKS[0]  # week 16 is even
        self.product_type.save()
        self._create_member_with_subscription()

        self.assertEqual(
            [],
            self._get_members_with_delivery_in_week(
                self.TODAY + datetime.timedelta(days=7)
            ),
        )

    def test_getMembersWithDeliveryInWeek_memberHasJoker_memberNotIncluded(self):
        member = self._create_member_with_subscription()
        JokerFactory.create(member=member, date=self.DELIVERY_DATE)

        self.assertEqual([], self._get_members_with_delivery_in_week())

    def test_getMembersWithDeliveryInWeek_memberHasJokerButProductTypeNotAffectedByJokers_memberIncluded(
        self,
    ):
        self.product_type.is_affected_by_jokers = False
        self.product_type.save()
        member = self._create_member_with_subscription()
        JokerFactory.create(member=member, date=self.DELIVERY_DATE)

        self.assertEqual([member], self._get_members_with_delivery_in_week())

    def test_getMembersWithDeliveryInWeek_memberHasJokerInOtherWeek_memberIncluded(
        self,
    ):
        member = self._create_member_with_subscription()
        JokerFactory.create(
            member=member, date=self.DELIVERY_DATE + datetime.timedelta(days=7)
        )

        self.assertEqual([member], self._get_members_with_delivery_in_week())

    def test_getMembersWithDeliveryInWeek_memberDonatedDelivery_memberNotIncluded(
        self,
    ):
        member = self._create_member_with_subscription()
        DeliveryDonationFactory.create(member=member, date=self.DELIVERY_DATE)

        self.assertEqual([], self._get_members_with_delivery_in_week())
