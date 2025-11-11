import datetime
from unittest.mock import patch, Mock, call

from tapir_mail.service.shortcuts import make_timezone_aware

from tapir.deliveries.models import Joker
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.models import (
    Member,
    MemberPickupLocation,
    CoopShareTransaction,
    HarvestShareProduct,
)
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
    PickupLocationFactory,
    ProductFactory,
    CoopShareTransactionFactory,
    ProductPriceFactory,
    ProductTypeFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberColumnProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_getValueMemberFirstName_default_returnsFirstName(self):
        member = MemberFactory.build(first_name="Bart")

        result = MemberColumnProvider.get_value_member_first_name(member, None, {})

        self.assertEqual("Bart", result)

    def test_getValueMemberLastName_default_returnsLastName(self):
        member = MemberFactory.build(last_name="Simpson")

        result = MemberColumnProvider.get_value_member_last_name(member, None, {})

        self.assertEqual("Simpson", result)

    def test_getValueMemberNumber_default_returnsMemberNumber(self):
        member = MemberFactory.build(member_no=1234)

        result = MemberColumnProvider.get_value_member_number(member, None, {})

        self.assertEqual("1234", result)

    def test_getValueMemberEmailAddress_default_returnsMemberEmailAddress(self):
        member = MemberFactory.build(email="test@mail.net")

        result = MemberColumnProvider.get_value_member_email_address(member, None, {})

        self.assertEqual("test@mail.net", result)

    def test_getValueMemberPhoneNumber_default_returnsMemberPhoneNumber(self):
        member = MemberFactory.build(phone_number="+49123456")

        result = MemberColumnProvider.get_value_member_phone_number(member, None, {})

        self.assertEqual("+49123456", result)

    def test_getValueMemberIban_default_returnsMemberIban(self):
        member = MemberFactory.build(iban="test_iban")

        result = MemberColumnProvider.get_value_member_iban(member, None, {})

        self.assertEqual("test_iban", result)

    def test_getValueMemberAccountOwner_default_returnsMemberAccountOwner(self):
        member = MemberFactory.build(account_owner="test owner")

        result = MemberColumnProvider.get_value_member_account_owner(member, None, {})

        self.assertEqual("test owner", result)

    @staticmethod
    def setupJokerData(member: Member):
        growing_period = GrowingPeriodFactory.create(
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
        )
        SubscriptionFactory.create(member=member, period=growing_period)
        SubscriptionFactory.create(member=member, period=growing_period)

        joker_1 = Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=1, day=2)
        )
        joker_2 = Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=1, day=3)
        )
        Joker.objects.create(
            member=member, date=datetime.date(year=2025, month=1, day=4)
        )
        return [joker_1, joker_2]

    @patch.object(
        DeliveryPriceCalculator, "get_price_of_subscriptions_delivered_in_week"
    )
    def test_getValueMemberJokerCreditValue_default_returnsSummedPriceOfAllJokersThatAreBeforeDate(
        self, mock_get_price_of_subscriptions_delivered_in_week: Mock
    ):
        member = MemberFactory.create()
        mock_get_price_of_subscriptions_delivered_in_week.side_effect = [12, 27]
        jokers_before_date = self.setupJokerData(member)
        cache = {}

        result = MemberColumnProvider.get_value_member_joker_credit_value(
            member, datetime.datetime(year=2025, month=1, day=3), cache
        )

        self.assertEqual("39.00", result)

        self.assertEqual(
            2, mock_get_price_of_subscriptions_delivered_in_week.call_count
        )
        mock_get_price_of_subscriptions_delivered_in_week.assert_has_calls(
            [
                call(
                    member=member,
                    reference_date=joker.date,
                    only_subscriptions_affected_by_jokers=True,
                    cache=cache,
                )
                for joker in jokers_before_date
            ],
            any_order=True,
        )

    def test_getValueMemberJokerCreditDetails_default_returnsCorrectDetails(self):
        member = MemberFactory.create()
        self.setupJokerData(member)

        result = MemberColumnProvider.get_value_member_joker_credit_details(
            member, datetime.datetime(year=2025, month=1, day=3), {}
        )

        self.assertEqual(
            "Gutschrift 2 genutzte Joker in Vertragsjahr 01.01.2025-03.01.2025", result
        )

    def test_getValueMemberPickupLocation_default_returnsCorrectLocationName(self):
        member = MemberFactory.create()
        pickup_location_1 = PickupLocationFactory.create(name="correct location")
        PickupLocationFactory.create(name="wrong location")
        MemberPickupLocation.objects.create(
            member=member,
            pickup_location=pickup_location_1,
            valid_from=datetime.date(year=2025, month=1, day=2),
        )

        result = MemberColumnProvider.get_value_member_pickup_location(
            member, datetime.datetime(year=2025, month=1, day=3), {}
        )

        self.assertEqual("correct location", result)

    def test_getValueAmountActiveSubscription_noSubscription_returns0(self):
        member = MemberFactory.create()

        result = MemberColumnProvider.get_value_amount_active_subscriptions(
            member,
            datetime.datetime(year=2025, month=1, day=3),
            {},
            product=ProductFactory.create(),
        )

        self.assertEqual("0", result)

    def test_getValueAmountActiveSubscription_subscriptionInThePast_returns0(self):
        member = MemberFactory.create()
        product = ProductFactory.create()
        SubscriptionFactory.create(
            product=product,
            member=member,
            start_date=datetime.date(year=2024, month=1, day=3),
            end_date=datetime.date(year=2025, month=1, day=2),
        )

        result = MemberColumnProvider.get_value_amount_active_subscriptions(
            member,
            datetime.datetime(year=2025, month=1, day=3),
            {},
            product=product,
        )

        self.assertEqual("0", result)

    def test_getValueAmountActiveSubscription_subscriptionInTheFuture_returns0(self):
        member = MemberFactory.create()
        product = ProductFactory.create()
        SubscriptionFactory.create(
            product=product,
            member=member,
            start_date=datetime.date(year=2025, month=1, day=4),
            end_date=datetime.date(year=2025, month=1, day=6),
        )

        result = MemberColumnProvider.get_value_amount_active_subscriptions(
            member,
            datetime.datetime(year=2025, month=1, day=3),
            {},
            product=product,
        )

        self.assertEqual("0", result)

    def test_getValueAmountActiveSubscription_subscriptionActive_returnsCorrectQuantity(
        self,
    ):
        member = MemberFactory.create()
        product = ProductFactory.create()
        SubscriptionFactory.create(
            product=product,
            member=member,
            start_date=datetime.date(year=2024, month=1, day=3),
            end_date=datetime.date(year=2025, month=1, day=2),
            quantity=7,
        )

        result = MemberColumnProvider.get_value_amount_active_subscriptions(
            member,
            datetime.datetime(year=2025, month=1, day=1),
            {},
            product=product,
        )

        self.assertEqual("7", result)

    def test_getValueMemberMembershipStatus_memberHasShares_returnsActive(self):
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member, valid_at=datetime.date(year=2025, month=1, day=3)
        )

        result = MemberColumnProvider.get_value_member_membership_status(
            member,
            datetime.datetime(year=2025, month=1, day=4),
            {},
        )

        self.assertEqual("Aktiv", result)

    def test_getValueMemberMembershipStatus_memberDoesntHaveShares_returnsInactive(
        self,
    ):
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member, valid_at=datetime.date(year=2025, month=1, day=5)
        )

        result = MemberColumnProvider.get_value_member_membership_status(
            member,
            datetime.datetime(year=2025, month=1, day=4),
            {},
        )

        self.assertEqual("Inaktiv", result)

    def test_getValueMemberSubscriptionSummary_default_returnsCorrectSummary(self):
        member = MemberFactory.create()
        SubscriptionFactory.create(
            member=member,
            product__name="p1",
            quantity=4,
            start_date=datetime.date(year=2025, month=1, day=3),
            end_date=datetime.date(year=2025, month=12, day=31),
        )
        SubscriptionFactory.create(
            member=member,
            product__name="p2",
            quantity=7,
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
        )
        SubscriptionFactory.create(
            member=member,
            product__name="p3",
            quantity=2,
            start_date=datetime.date(year=2025, month=1, day=12),
            end_date=datetime.date(year=2025, month=12, day=31),
        )

        result = MemberColumnProvider.get_value_member_subscription_summary(
            member,
            datetime.datetime(year=2025, month=1, day=4),
            {},
        )

        self.assertEqual("p1:4, p2:7", result)

    def test_getValueMemberAmountToPay_default_returnsCorrectAmount(self):
        member = MemberFactory.create()
        product_1, product_2, product_3 = ProductFactory.create_batch(size=3)
        SubscriptionFactory.create(
            member=member,
            product=product_1,
            quantity=4,
            start_date=datetime.date(year=2025, month=1, day=3),
            end_date=datetime.date(year=2025, month=12, day=31),
            solidarity_price_percentage=0,
        )
        ProductPriceFactory.create(price=1.25, product=product_1)
        SubscriptionFactory.create(
            member=member,
            product=product_2,
            quantity=7,
            start_date=datetime.date(year=2025, month=1, day=1),
            end_date=datetime.date(year=2025, month=12, day=31),
            solidarity_price_percentage=0,
        )
        ProductPriceFactory.create(price=2.33, product=product_2)
        SubscriptionFactory.create(
            member=member,
            product=product_3,
            quantity=2,
            start_date=datetime.date(year=2025, month=1, day=12),
            end_date=datetime.date(year=2025, month=12, day=31),
            solidarity_price_percentage=0,
        )
        ProductPriceFactory.create(price=28, product=product_3)

        result = MemberColumnProvider.get_value_member_amount_to_pay(
            member,
            datetime.datetime(year=2025, month=1, day=4),
            {},
        )

        self.assertEqual("21.31", result)

    def test_getValueMemberMembershipEndDate_membershipDoesntEnd_returnsEmptyString(
        self,
    ):
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(member=member)

        result = MemberColumnProvider.get_value_member_membership_end_date(
            member,
            None,
            {},
        )

        self.assertEqual("", result)

    def test_getValueMemberMembershipEndDate_membershipEnds_returnsCorrectEndDate(
        self,
    ):
        member = MemberFactory.create()
        CoopShareTransactionFactory.create(
            member=member, quantity=2, valid_at=datetime.date(year=2025, month=1, day=4)
        )
        CoopShareTransactionFactory.create(
            member=member,
            quantity=-2,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
            valid_at=datetime.date(year=2025, month=1, day=28),
        )

        result = MemberColumnProvider.get_value_member_membership_end_date(
            member,
            datetime.datetime(year=2024, month=2, day=3),
            {},
        )

        self.assertEqual("28.01.2025: -2 Anteile", result)

    def test_getValueMemberSubscriptionEndDates_default_returnsCorrectEndDates(
        self,
    ):
        member = MemberFactory.create()
        product_1 = ProductFactory.create(name="p1")
        product_2 = ProductFactory.create(name="p2")

        # all cancelled: get the max end date
        SubscriptionFactory.create(
            member=member,
            product=product_1,
            cancellation_ts=make_timezone_aware(
                datetime.datetime(year=2025, month=1, day=12)
            ),
            end_date=datetime.date(year=2025, month=12, day=28),
        )
        SubscriptionFactory.create(
            member=member,
            product=product_1,
            cancellation_ts=make_timezone_aware(
                datetime.datetime(year=2025, month=1, day=12)
            ),
            end_date=datetime.date(year=2025, month=11, day=30),
        )

        # not cancelled: should not appear in the result
        SubscriptionFactory.create(
            member=member,
            product=product_2,
            cancellation_ts=None,
            end_date=datetime.date(year=2025, month=12, day=31),
        )

        result = MemberColumnProvider.get_value_member_subscription_end_dates(
            member,
            datetime.datetime(year=2024, month=2, day=3),
            {},
        )

        self.assertEqual("p1:28.12.2025", result)

    def test_getValueMemberCurrentNumberOfCoopShares_default_returnsCorrectValue(self):
        member = MemberFactory.create()
        CoopShareTransaction.objects.create(
            member=member,
            share_price=100,
            transaction_type=CoopShareTransaction.CoopShareTransactionType.PURCHASE,
            quantity=2,
            valid_at=datetime.date(year=2024, month=2, day=1),
        )

        result = MemberColumnProvider.get_value_member_current_number_of_coop_shares(
            member,
            datetime.datetime(year=2024, month=2, day=3),
            {},
        )

        self.assertEqual("2", result)

    def test_getValueMemberRequiredNumberOfCoopShares_default_returnsCorrectValue(self):
        member = MemberFactory.create()
        product = HarvestShareProduct.objects.create(
            min_coop_shares=2,
            type=ProductTypeFactory.create(),
            name="test_product",
            base=True,
        )
        SubscriptionFactory.create(
            member=member,
            product=product,
            quantity=3,
            period=GrowingPeriodFactory.create(
                start_date=datetime.date(year=2024, month=1, day=1)
            ),
        )

        result = MemberColumnProvider.get_value_member_required_number_of_coop_shares(
            member,
            datetime.datetime(year=2024, month=2, day=3),
            {},
        )

        self.assertEqual("6", result)
