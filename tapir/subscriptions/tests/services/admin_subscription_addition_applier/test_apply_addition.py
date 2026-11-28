import datetime
from unittest.mock import patch, MagicMock

from tapir.mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.subscriptions.services.admin_subscription_addition_applier import (
    AdminSubscriptionAdditionApplier,
)
from tapir.subscriptions.types import (
    AdminSubscriptionAddition,
    SubscriptionPrerequisitesInput,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import Product, Subscription
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    MemberPickupLocationFactory,
    PickupLocationCapabilityFactory,
    PickupLocationFactory,
    ProductCapacityFactory,
    ProductFactory,
    ProductPriceFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest, mock_timezone


@patch.object(TransactionalTrigger, "fire_action", autospec=True)
class TestAdminSubscriptionAdditionApplierApplyAddition(TapirIntegrationTest):
    START_DATE = datetime.date(year=2030, month=6, day=10)
    NEXT_PERIOD_START = datetime.date(year=2031, month=1, day=1)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls.product_small = ProductFactory.create(type__delivery_cycle=WEEKLY[0])
        cls.product_medium = ProductFactory.create(type=cls.product_small.type)
        for product in [cls.product_small, cls.product_medium]:
            ProductPriceFactory.create(
                product=product,
                valid_from=datetime.date(year=2029, month=1, day=1),
                size=1,
            )
        cls.growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2030, month=1, day=1)
        )
        cls.next_growing_period = GrowingPeriodFactory.create(
            start_date=cls.NEXT_PERIOD_START
        )
        for growing_period in [cls.growing_period, cls.next_growing_period]:
            ProductCapacityFactory.create(
                period=growing_period,
                product_type=cls.product_small.type,
                capacity=1000,
            )
        cls.pickup_location = PickupLocationFactory.create()
        PickupLocationCapabilityFactory.create(
            pickup_location=cls.pickup_location,
            product_type=cls.product_small.type,
            max_capacity=1000,
        )

    def setUp(self) -> None:
        super().setUp()
        mock_timezone(test=self, now=datetime.datetime(year=2030, month=6, day=1))
        self.member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=self.member,
            pickup_location=self.pickup_location,
            valid_from=datetime.date(year=2029, month=1, day=1),
        )

    def _apply_addition(
        self,
        product: Product,
        quantity: int,
        start_date: datetime.date = START_DATE,
    ) -> list[Subscription]:
        cache = {}
        return AdminSubscriptionAdditionApplier.apply_addition(
            addition=AdminSubscriptionAddition(
                member=self.member,
                product=product,
                quantity=quantity,
                start_date=start_date,
                prerequisites=SubscriptionPrerequisitesInput(
                    desired_pickup_location_id=None,
                    iban="",
                    account_owner="",
                    sepa_mandate_confirmed=False,
                ),
            ),
            actor=MemberFactory.create(is_superuser=True),
            cache=cache,
        )

    def test_applyAddition_noExistingSubscription_createsConfirmedSubscriptionAndSendsChangeMail(
        self, mock_fire_action: MagicMock
    ):
        new_subscriptions = self._apply_addition(
            product=self.product_medium, quantity=2
        )

        self.assertEqual(1, len(new_subscriptions))
        subscription = Subscription.objects.get(id=new_subscriptions[0].id)
        self.assertEqual(self.START_DATE, subscription.start_date)
        self.assertEqual(self.growing_period.end_date, subscription.end_date)
        self.assertEqual(2, subscription.quantity)
        self.assertIsNotNone(subscription.admin_confirmed)
        self.assertIsNotNone(subscription.auto_confirmed)
        self.assert_mail_event_has_been_triggered(
            mock_fire_action=mock_fire_action, key=Events.MEMBERAREA_CHANGE_CONTRACT
        )

    def test_applyAddition_aSubscriptionForTheSameProductTypeExists_existingSubscriptionUntouched(
        self, _: MagicMock
    ):
        existing = SubscriptionFactory.create(
            member=self.member,
            period=self.growing_period,
            product=self.product_small,
            quantity=1,
            price_override=0,
        )

        new_subscriptions = self._apply_addition(
            product=self.product_medium, quantity=1
        )

        existing.refresh_from_db()
        self.assertEqual(self.growing_period.end_date, existing.end_date)
        self.assertIsNone(existing.cancellation_ts)
        self.assertEqual(0, existing.price_override)
        self.assertEqual(
            {existing.id, new_subscriptions[0].id},
            set(
                Subscription.objects.filter(member=self.member).values_list(
                    "id", flat=True
                )
            ),
        )

    def test_applyAddition_nextPeriodSubscriptionExists_createsNothingInNextPeriod(
        self, _: MagicMock
    ):
        next_period_subscription = SubscriptionFactory.create(
            member=self.member,
            period=self.next_growing_period,
            product=self.product_small,
            quantity=1,
        )

        self._apply_addition(product=self.product_medium, quantity=1)

        self.assertEqual(
            [next_period_subscription.id],
            list(
                Subscription.objects.filter(
                    member=self.member, period=self.next_growing_period
                ).values_list("id", flat=True)
            ),
        )

    def test_applyAddition_atNextPeriodStart_onlyAddsToNextPeriod(self, _: MagicMock):
        current = SubscriptionFactory.create(
            member=self.member,
            period=self.growing_period,
            product=self.product_small,
            quantity=1,
        )
        next_period_subscription = SubscriptionFactory.create(
            member=self.member,
            period=self.next_growing_period,
            product=self.product_small,
            quantity=1,
        )

        new_subscriptions = self._apply_addition(
            product=self.product_medium,
            quantity=1,
            start_date=self.NEXT_PERIOD_START,
        )

        self.assertEqual(1, len(new_subscriptions))
        self.assertEqual(self.NEXT_PERIOD_START, new_subscriptions[0].start_date)
        current.refresh_from_db()
        next_period_subscription.refresh_from_db()
        self.assertIsNone(current.cancellation_ts)
        self.assertIsNone(next_period_subscription.cancellation_ts)
        self.assertEqual(3, Subscription.objects.filter(member=self.member).count())
