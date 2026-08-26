import datetime
from decimal import Decimal

from tapir.deliveries.tests.factories import JokerFactory
from tapir.payments.models import MemberCredit
from tapir.payments.services.joker_credit_creator import JokerCreditCreator
from tapir.payments.tests.factories import MemberCreditFactory
from tapir.wirgarten.constants import WEEKLY
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    ProductFactory,
    ProductPriceFactory,
    MemberFactory,
    SubscriptionFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestJokerCreditCreator(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls) -> None:
        ParameterDefinitions().import_definitions(bulk_create=True)

        cls.product = ProductFactory.create(type__delivery_cycle=WEEKLY[0])
        ProductPriceFactory.create(
            product=cls.product,
            valid_from=datetime.date(year=2020, month=1, day=1),
            price=10,
        )
        cls._set_parameter(
            key=ParameterKeys.PAYMENT_INTENDED_USE_JOKER_CREDIT, value="test_pattern"
        )
        cls._set_parameter(key=ParameterKeys.DELIVERY_DAY, value=5)

    def setUp(self) -> None:
        super().setUp()
        self.member = MemberFactory.create()
        SubscriptionFactory.create(
            member=self.member,
            product=self.product,
            quantity=2,
            period__start_date=datetime.date(year=2020, month=1, day=1),
        )

    def test_createCreditsForJokers_noJoker_doesNothing(self):
        JokerCreditCreator.create_credits_for_jokers(
            reference_date=datetime.date.today(), cache={}
        )

    def test_createCreditsForJokers_jokerHasNoCreditAndCantBeCancelled_createsCredit(
        self,
    ):
        joker = JokerFactory.create(
            member=self.member, date=datetime.date(year=2020, month=1, day=15)
        )

        JokerCreditCreator.create_credits_for_jokers(
            reference_date=datetime.date(year=2020, month=3, day=1), cache={}
        )

        self.assertEqual(1, MemberCredit.objects.count())
        credit = MemberCredit.objects.get()
        self.assertEqual(self.member, credit.member)
        self.assertEqual(joker, credit.joker)
        self.assertEqual(
            Decimal("4.53"), credit.amount
        )  # 10€ * 2 (quantity) * 12 (month) / 53 (weeks in 2020) = 4.53
        self.assertEqual(datetime.date(year=2020, month=3, day=31), credit.due_date)
        self.assertEqual("test_pattern", credit.purpose)
        self.assertEqual("Joker am 18.01.2020", credit.comment)
        self.assertEqual("Joker", credit.source)

    def test_createCreditsForJokers_jokerAlreadyHasCredit_dontCreateCredit(
        self,
    ):
        joker = JokerFactory.create(
            member=self.member, date=datetime.date(year=2020, month=1, day=15)
        )
        MemberCreditFactory.create(member=self.member, joker=joker)

        JokerCreditCreator.create_credits_for_jokers(
            reference_date=datetime.date(year=2020, month=3, day=1), cache={}
        )

        self.assertEqual(1, MemberCredit.objects.count())

    def test_createCreditsForJokers_jokerHasNoCreditButCanStillBeCancelled_dontCreateCredit(
        self,
    ):
        JokerFactory.create(
            member=self.member, date=datetime.date(year=2020, month=1, day=15)
        )

        JokerCreditCreator.create_credits_for_jokers(
            reference_date=datetime.date(year=2020, month=1, day=5), cache={}
        )

        self.assertFalse(MemberCredit.objects.exists())
