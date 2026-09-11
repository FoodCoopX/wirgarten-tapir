import datetime
from unittest.mock import Mock

from tapir.payments.config import IntendedUseTokens
from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.wirgarten.models import Member
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.parameters import ParameterDefinitions
from tapir.wirgarten.tests.factories import CoopShareTransactionFactory
from tapir.wirgarten.tests.test_utils import TapirIntegrationTest


class TestExpandPatternCoopSharesBought(TapirIntegrationTest):
    @classmethod
    def setUpTestData(cls):
        ParameterDefinitions().import_definitions(bulk_create=True)

    def test_expandPatternCoopSharesBought_numberOfCoopShares_patternCorrectlyExpanded(
        self,
    ):
        result = self._expand_token(
            IntendedUseTokens.NUMBER_OF_COOP_SHARES, member=Mock()
        )

        self.assertEqual("12", result)

    def test_expandPatternCoopSharesBought_coopEntryDate_patternCorrectlyExpanded(
        self,
    ):
        transaction = CoopShareTransactionFactory.create(
            valid_at=datetime.date(year=2024, month=9, day=13)
        )
        result = self._expand_token(
            IntendedUseTokens.COOP_ENTRY_DATE, member=transaction.member
        )

        self.assertEqual("13.09.2024", result)

    def test_expandPatternCoopSharesBought_priceSingleShare_patternCorrectlyExpanded(
        self,
    ):
        self._set_parameter(key=ParameterKeys.COOP_SHARE_PRICE, value=123)
        result = self._expand_token(IntendedUseTokens.PRICE_SINGLE_SHARE, member=Mock())

        self.assertEqual("123,00", result)

    def _expand_token(self, token: str, member: Member):
        return IntendedUsePatternExpander.expand_pattern_coop_shares_bought(
            pattern=f"{{{token}}}",
            member=member,
            number_of_shares=12,
            cache={},
        )
