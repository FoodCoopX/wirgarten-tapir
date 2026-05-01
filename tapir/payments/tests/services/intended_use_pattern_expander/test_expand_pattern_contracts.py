import datetime

from tapir.payments.config import IntendedUseTokens
from tapir.payments.models import MemberPaymentRhythm
from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.payments.services.member_payment_rhythm_service import (
    MemberPaymentRhythmService,
)
from tapir.solidarity_contribution.tests.factories import SolidarityContributionFactory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import (
    PaymentFactory,
    MemberFactory,
    SubscriptionFactory,
    ProductPriceFactory,
)
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExpandPatternContracts(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)
        cls._set_parameter(key=ParameterKeys.SITE_NAME, value="TestSiteName")
        cls._set_parameter(key=ParameterKeys.MEMBER_NUMBER_ZERO_PAD_LENGTH, value=5)
        cls._set_parameter(key=ParameterKeys.MEMBER_NUMBER_PREFIX, value="PF")

    def setUp(self):
        super().setUp()
        self.member = MemberFactory.create(
            first_name="John", last_name="Doe", member_no=123
        )
        self.subscription_1 = SubscriptionFactory.create(
            member=self.member,
            quantity=1,
            start_date=datetime.date(year=2020, month=1, day=1),
            product__name="p1",
            product__type__name="pt1",
        )
        ProductPriceFactory.create(
            product=self.subscription_1.product,
            price=12,
            valid_from=datetime.date(year=2020, month=1, day=1),
        )
        self.subscription_2 = SubscriptionFactory.create(
            member=self.member,
            quantity=3,
            start_date=datetime.date(year=2020, month=1, day=1),
            product__name="p2",
            product__type__name="pt2",
        )
        ProductPriceFactory.create(
            product=self.subscription_2.product,
            price=5.5,
            valid_from=datetime.date(year=2020, month=1, day=1),
        )
        self.payment = PaymentFactory.create(
            mandate_ref__member=self.member,
            subscription_payment_range_start=datetime.date(year=2020, month=1, day=1),
            subscription_payment_range_end=datetime.date(year=2020, month=12, day=31),
        )
        SolidarityContributionFactory.create(
            member=self.member, start_date=self.subscription_1.start_date, amount=6.7
        )
        MemberPaymentRhythmService.assign_payment_rhythm_to_member(
            member=self.member,
            rhythm=MemberPaymentRhythm.Rhythm.SEMIANNUALLY,
            valid_from=self.subscription_1.start_date,
            cache={},
            actor=None,
        )

    def test_expandPatternContracts_overrideSet_usesOverride(self):
        result = IntendedUsePatternExpander.expand_pattern_contracts(
            pattern="AA {monatsbeitrag_ohne_soli} BB",
            payment=self.payment,
            cache={},
            token_value_overrides={"monatsbeitrag_ohne_soli": "override value"},
        )

        self.assertEqual("AA override value BB", result)

    def test_expandPatternContracts_commonTokens_patternCorrectlyExpanded(self):
        result = IntendedUsePatternExpander.expand_pattern_contracts(
            pattern=f"{{{IntendedUseTokens.SITE_NAME}}}\n{{{IntendedUseTokens.FIRST_NAME}}} {{{IntendedUseTokens.LAST_NAME}}}\n{{{IntendedUseTokens.MEMBER_NUMBER_SHORT}}} {{{IntendedUseTokens.MEMBER_NUMBER_LONG}}} {{{IntendedUseTokens.MEMBER_NUMBER_WITHOUT_PREFIX}}}",
            payment=self.payment,
            cache={},
        )

        self.assertEqual("TestSiteName\nJohn Doe\n123 PF00123 00123", result)

    def test_expandPatternContracts_monthlyPriceContractsWithoutSoli_tokenCorrectlyReplaced(
        self,
    ):
        result = self._expand_token(
            IntendedUseTokens.MONTHLY_PRICE_CONTRACTS_WITHOUT_SOLI
        )

        self.assertEqual("28,50", result)  # 1x12 + 3x5.5 = 28.5

    def test_expandPatternContracts_monthlyPriceContractsWithSoli_tokenCorrectlyReplaced(
        self,
    ):
        result = self._expand_token(IntendedUseTokens.MONTHLY_PRICE_CONTRACTS_WITH_SOLI)

        self.assertEqual("35,20", result)  # 1x12 + 3x5.5 + 6.7 = 35.2

    def test_expandPatternContracts_monthlyPriceJustSoli_tokenCorrectlyReplaced(
        self,
    ):
        result = self._expand_token(IntendedUseTokens.MONTHLY_PRICE_JUST_SOLI)

        self.assertEqual("6,70", result)

    def test_expandPatternContracts_totalPriceWithoutSoli_tokenCorrectlyReplaced(
        self,
    ):
        result = self._expand_token(
            IntendedUseTokens.TOTAL_PRICE_CONTRACTS_WITHOUT_SOLI
        )

        self.assertEqual("171,00", result)  # 28.5 monthly, *6 month = 171

    def test_expandPatternContracts_totalPriceWithSoli_tokenCorrectlyReplaced(
        self,
    ):
        result = self._expand_token(IntendedUseTokens.TOTAL_PRICE_CONTRACTS_WITH_SOLI)

        self.assertEqual("211,20", result)  # 35,2 monthly, *6 month = 211,2

    def test_expandPatternContracts_totalPriceJustSoli_tokenCorrectlyReplaced(
        self,
    ):
        result = self._expand_token(IntendedUseTokens.TOTAL_PRICE_JUST_SOLI)

        self.assertEqual("40,20", result)  # 6,7 monthly, *6 month = 40,2

    def test_expandPatternContracts_contractList_tokenCorrectlyReplaced(
        self,
    ):
        result = self._expand_token(IntendedUseTokens.CONTRACT_LIST)

        self.assertEqual("1×p1,pt1, 3×p2,pt2", result)

    def test_expandPatternContracts_paymentRhythm_tokenCorrectlyReplaced(
        self,
    ):
        result = self._expand_token(IntendedUseTokens.PAYMENT_RHYTHM)

        self.assertEqual("Halbjährlich", result)

    def test_expandPatternContracts_patternIsMultiline_patternIsStripedAndLinesArePreserved(
        self,
    ):
        result = IntendedUsePatternExpander.expand_pattern_contracts(
            pattern="\t\n\t   {vorname}\n{nachname}\n{zahlungsintervall}\n   \n\n\t",
            payment=self.payment,
            cache={},
        )

        self.assertEqual("John\nDoe\nHalbjährlich", result)

    def _expand_token(self, token: str):
        return IntendedUsePatternExpander.expand_pattern_contracts(
            pattern=f"{{{token}}}",
            payment=self.payment,
            cache={},
        )
