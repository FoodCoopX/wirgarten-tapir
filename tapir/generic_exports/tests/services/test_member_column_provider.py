import datetime
from unittest.mock import patch, Mock, call

from tapir.deliveries.models import Joker
from tapir.generic_exports.services.member_column_provider import MemberColumnProvider
from tapir.subscriptions.services.delivery_price_calculator import (
    DeliveryPriceCalculator,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    MemberFactory,
    SubscriptionFactory,
    GrowingPeriodFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestMemberColumnProvider(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions()

    def test_getValueMemberFirstName_default_returnsFirstName(self):
        member = MemberFactory.build(first_name="Bart")

        result = MemberColumnProvider.get_value_member_first_name(member, None)

        self.assertEqual("Bart", result)

    def test_getValueMemberLastName_default_returnsLastName(self):
        member = MemberFactory.build(last_name="Simpson")

        result = MemberColumnProvider.get_value_member_last_name(member, None)

        self.assertEqual("Simpson", result)

    def test_getValueMemberNumber_default_returnsMemberNumber(self):
        member = MemberFactory.build(member_no=1234)

        result = MemberColumnProvider.get_value_member_number(member, None)

        self.assertEqual("1234", result)

    def test_getValueMemberEmailAddress_default_returnsMemberEmailAddress(self):
        member = MemberFactory.build(email="test@mail.net")

        result = MemberColumnProvider.get_value_member_email_address(member, None)

        self.assertEqual("test@mail.net", result)

    def test_getValueMemberPhoneNumber_default_returnsMemberPhoneNumber(self):
        member = MemberFactory.build(phone_number="+49123456")

        result = MemberColumnProvider.get_value_member_phone_number(member, None)

        self.assertEqual("+49123456", result)

    def test_getValueMemberIban_default_returnsMemberIban(self):
        member = MemberFactory.build(iban="test_iban")

        result = MemberColumnProvider.get_value_member_iban(member, None)

        self.assertEqual("test_iban", result)

    def test_getValueMemberAccountOwner_default_returnsMemberAccountOwner(self):
        member = MemberFactory.build(account_owner="test owner")

        result = MemberColumnProvider.get_value_member_account_owner(member, None)

        self.assertEqual("test owner", result)

    def setupJokerData(self, member: Member):
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

        result = MemberColumnProvider.get_value_member_joker_credit_value(
            member, datetime.datetime(year=2025, month=1, day=3)
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
                )
                for joker in jokers_before_date
            ],
            any_order=True,
        )

    def test_getValueMemberJokerCreditDetails_default_returnsCorrectDetails(self):
        member = MemberFactory.create()
        self.setupJokerData(member)

        result = MemberColumnProvider.get_value_member_joker_credit_details(
            member, datetime.datetime(year=2025, month=1, day=3)
        )

        self.assertEqual(
            "Gutschrift 2 genutzte Joker in Vertragsjahr 01.01.2025-03.01.2025", result
        )
