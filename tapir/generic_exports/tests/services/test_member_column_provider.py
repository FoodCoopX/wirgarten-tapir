import datetime
from unittest.mock import Mock, call, patch

from tapir.deliveries.models import Joker
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.models import Member, CoopShareTransaction
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    GrowingPeriodFactory,
    MemberFactory,
    SubscriptionFactory,
    CoopShareTransactionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberColumnProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

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

    def test_getValueMemberFullAddress_default_returnsMemberFullAddress(self):
        member = MemberFactory.build(
            street="Musterstraße 1", postcode="12345", city="Musterstadt"
        )

        result = MemberColumnProvider.get_value_member_full_address(member, None, {})

        self.assertEqual("Musterstraße 1, 12345 Musterstadt", result)

    def create_terminated_member_with_share_history(self):
        member = MemberFactory.create()
        start = datetime.datetime(2024, 1, 1)
        # admission
        CoopShareTransactionFactory.create(member=member, quantity=23, valid_at=start)
        # more shares
        CoopShareTransactionFactory.create(
            member=member, quantity=19, valid_at=start + datetime.timedelta(days=20)
        )
        # termination
        CoopShareTransactionFactory.create(
            member=member,
            quantity=-42,
            valid_at=start + datetime.timedelta(days=40),
            transaction_type=CoopShareTransaction.CoopShareTransactionType.CANCELLATION,
        )
        return member

    def test_getValueMemberShareQuantity_default_returnsMemberShareQuantity(self):
        member = self.create_terminated_member_with_share_history()

        result = MemberColumnProvider.get_value_member_share_quantity(
            member, datetime.datetime(2023, 12, 1), {}
        )
        self.assertEqual(0, result)

        result = MemberColumnProvider.get_value_member_share_quantity(
            member, datetime.datetime(2024, 1, 1), {}
        )
        self.assertEqual(23, result)

        result = MemberColumnProvider.get_value_member_share_quantity(
            member, datetime.datetime(2024, 2, 1), {}
        )
        self.assertEqual(42, result)

        result = MemberColumnProvider.get_value_member_share_quantity(
            member, datetime.datetime(2024, 3, 1), {}
        )
        self.assertEqual(0, result)

    def test_getValueMemberAdmissionDate_default_returnsMemberAdmissionDate(self):
        member = self.create_terminated_member_with_share_history()

        result = MemberColumnProvider.get_value_member_admission_date(member, None, {})
        self.assertEqual("01.01.2024", result)

    def test_getValueMemberTerminationDate_default_returnsMemberTerminationDate(self):
        member = self.create_terminated_member_with_share_history()

        result = MemberColumnProvider.get_value_member_termination_date(
            member, None, {}
        )
        self.assertEqual("10.02.2024", result)

    def test_getValueMemberShareHistory_default_returnsMemberShareHistory(self):
        member = self.create_terminated_member_with_share_history()

        result = MemberColumnProvider.get_value_member_share_history(
            member, datetime.datetime(2023, 12, 1), {}
        )
        self.assertEqual("", result)

        result = MemberColumnProvider.get_value_member_share_history(
            member, datetime.datetime(2024, 1, 1), {}
        )
        self.assertEqual("+23 am 01.01.2024", result)

        result = MemberColumnProvider.get_value_member_share_history(
            member, datetime.datetime(2024, 2, 1), {}
        )
        self.assertEqual("+23 am 01.01.2024\n+19 am 21.01.2024", result)

        result = MemberColumnProvider.get_value_member_share_history(
            member, datetime.datetime(2024, 3, 1), {}
        )
        self.assertEqual(
            "+23 am 01.01.2024\n+19 am 21.01.2024\n-42 am 10.02.2024", result
        )

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

    def test_getValueMemberShareQuantityCancelledInPreviousYear_default_returnsMemberShareQuantityCancelledInPreviousYear(
        self,
    ):
        member = self.create_terminated_member_with_share_history()

        result = MemberColumnProvider.get_value_member_share_quantity_cancelled_in_previous_year(
            member, datetime.datetime(2023, 12, 1), {}
        )
        self.assertEqual(0, result)

        result = MemberColumnProvider.get_value_member_share_quantity_cancelled_in_previous_year(
            member, datetime.datetime(2024, 12, 31), {}
        )
        self.assertEqual(0, result)

        result = MemberColumnProvider.get_value_member_share_quantity_cancelled_in_previous_year(
            member, datetime.datetime(2025, 1, 1), {}
        )
        self.assertEqual(42, result)
