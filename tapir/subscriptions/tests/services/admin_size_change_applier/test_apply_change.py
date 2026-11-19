import datetime
from unittest.mock import patch, MagicMock

from tapir_mail.triggers.transactional_trigger import TransactionalTrigger

from tapir.payments.models import MemberPaymentRhythm
from tapir.subscriptions.services.admin_size_change_applier import (
    AdminSizeChangeApplier,
)
from tapir.subscriptions.services.admin_size_change_order_builder import (
    AdminSizeChangeOrderBuilder,
)
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.mail_events import Events
from tapir.wirgarten.models import (
    Member,
    Product,
    Subscription,
    SubscriptionChangeLogEntry,
)
from tapir.wirgarten.parameter_keys import ParameterKeys
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
class TestAdminSizeChangeApplierApplyChange(TapirIntegrationTest):
    CHANGE_DATE = datetime.date(year=2030, month=6, day=10)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_DEFAULT_RHYTHM,
            value=MemberPaymentRhythm.Rhythm.QUARTERLY,
        )

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
        ProductCapacityFactory.create(
            period=cls.growing_period,
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
        self.now = mock_timezone(
            test=self, now=datetime.datetime(year=2030, month=6, day=1)
        )

    def _create_member_with_subscription(
        self, quantity: int, member: Member | None = None
    ) -> Subscription:
        if member is None:
            member = MemberFactory.create()
        MemberPickupLocationFactory.create(
            member=member,
            pickup_location=self.pickup_location,
            valid_from=datetime.date(year=2029, month=1, day=1),
        )
        return SubscriptionFactory.create(
            member=member,
            period=self.growing_period,
            product=self.product_small,
            quantity=quantity,
        )

    def _apply_change(
        self,
        subscription: Subscription,
        new_product: Product,
        iban: str = "",
        account_owner: str = "",
        sepa_mandate_confirmed: bool = False,
    ) -> list[Subscription]:
        cache = {}
        return AdminSizeChangeApplier.apply_change(
            member=subscription.member,
            previous_subscription=subscription,
            change_date=self.CHANGE_DATE,
            order=AdminSizeChangeOrderBuilder.build_order(
                member=subscription.member,
                subscription=subscription,
                new_product=new_product,
                change_date=self.CHANGE_DATE,
                cache=cache,
            ),
            actor=MemberFactory.create(is_superuser=True),
            desired_pickup_location_id=None,
            payment_rhythm=None,
            iban=iban,
            account_owner=account_owner,
            sepa_mandate_confirmed=sepa_mandate_confirmed,
            cache=cache,
        )

    def test_applyChange_quantityOne_endsOldSubscriptionAndCreatesNewOne(
        self, _: MagicMock
    ):
        subscription = self._create_member_with_subscription(quantity=1)

        new_subscriptions = self._apply_change(
            subscription=subscription, new_product=self.product_medium
        )

        subscription.refresh_from_db()
        self.assertEqual(
            self.CHANGE_DATE - datetime.timedelta(days=1), subscription.end_date
        )
        self.assertEqual(self.now, subscription.cancellation_ts)
        self.assertEqual(self.now, subscription.cancellation_admin_confirmed)

        self.assertEqual(1, len(new_subscriptions))
        new_subscription = Subscription.objects.get(id=new_subscriptions[0].id)
        self.assertEqual(self.product_medium, new_subscription.product)
        self.assertEqual(1, new_subscription.quantity)
        self.assertEqual(self.CHANGE_DATE, new_subscription.start_date)
        self.assertEqual(self.growing_period.end_date, new_subscription.end_date)
        self.assertEqual(self.now, new_subscription.auto_confirmed)
        self.assertIsNone(new_subscription.price_override)

    def test_applyChange_quantityThree_keepsOldProductWithQuantityTwoInANewSubscription(
        self, _: MagicMock
    ):
        subscription = self._create_member_with_subscription(quantity=3)

        self._apply_change(subscription=subscription, new_product=self.product_medium)

        quantities_from_change_date = {
            new_subscription.product: new_subscription.quantity
            for new_subscription in Subscription.objects.filter(
                member=subscription.member, start_date=self.CHANGE_DATE
            )
        }
        self.assertEqual(
            {self.product_small: 2, self.product_medium: 1},
            quantities_from_change_date,
        )

    def test_applyChange_default_logsCancellationAndNewSubscriptions(
        self, _: MagicMock
    ):
        subscription = self._create_member_with_subscription(quantity=1)

        self._apply_change(subscription=subscription, new_product=self.product_medium)

        self.assertEqual(
            {
                SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.CANCELLED,
                SubscriptionChangeLogEntry.SubscriptionChangeLogEntryType.ADDED,
            },
            set(
                SubscriptionChangeLogEntry.objects.filter(
                    user=subscription.member
                ).values_list("change_type", flat=True)
            ),
        )

    def test_applyChange_default_sendsContractChangeMail(
        self, mock_fire_action: MagicMock
    ):
        subscription = self._create_member_with_subscription(quantity=1)

        self._apply_change(subscription=subscription, new_product=self.product_medium)

        self.assert_mail_event_has_been_triggered(
            mock_fire_action=mock_fire_action, key=Events.MEMBERAREA_CHANGE_CONTRACT
        )

    def test_applyChange_subscriptionInTrial_newSubscriptionKeepsTrialEndDate(
        self, _: MagicMock
    ):
        self._set_parameter(key=ParameterKeys.TRIAL_PERIOD_ENABLED, value=True)
        subscription = self._create_member_with_subscription(quantity=1)
        subscription.trial_end_date_override = datetime.date(year=2030, month=6, day=30)
        subscription.save()

        new_subscriptions = self._apply_change(
            subscription=subscription, new_product=self.product_medium
        )

        new_subscription = Subscription.objects.get(id=new_subscriptions[0].id)
        self.assertEqual(
            datetime.date(year=2030, month=6, day=30),
            new_subscription.trial_end_date_override,
        )
        self.assertFalse(new_subscription.trial_disabled)

    def test_applyChange_bankingDataEnteredWithMandate_savesBankingDataAndConsent(
        self, _: MagicMock
    ):
        member = MemberFactory.create(iban="", account_owner="", sepa_consent=None)
        subscription = self._create_member_with_subscription(quantity=1, member=member)

        self._apply_change(
            subscription=subscription,
            new_product=self.product_medium,
            iban="NL76RABO8675663943",
            account_owner="test account owner",
            sepa_mandate_confirmed=True,
        )

        member.refresh_from_db()
        self.assertEqual("NL76RABO8675663943", member.iban)
        self.assertEqual("test account owner", member.account_owner)
        self.assertEqual(self.now, member.sepa_consent)
