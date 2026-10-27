from unittest.mock import Mock

from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestApplyReplacementsForLine(TapirUnitTest):
    def test_applyReplacementsForLine_tokenNotInLine_providerNotCalled(self):
        provider = Mock()
        replacements = {"vorname": provider}

        result = IntendedUsePatternExpander._apply_replacements_for_line(
            line="static text without tokens",
            replacements=replacements,
            token_value_overrides={},
        )

        self.assertEqual("static text without tokens", result)
        provider.assert_not_called()

    def test_applyReplacementsForLine_tokenPresent_replacedByValue(self):
        replacements = {"vorname": lambda: "John"}

        result = IntendedUsePatternExpander._apply_replacements_for_line(
            line="hi {vorname}",
            replacements=replacements,
            token_value_overrides={},
        )

        self.assertEqual("hi John", result)

    def test_applyReplacementsForLine_overridePresent_useOverrideInsteadOfProvider(
        self,
    ):
        provider = Mock()
        replacements = {"vorname": provider}

        result = IntendedUsePatternExpander._apply_replacements_for_line(
            line="hi {vorname}",
            replacements=replacements,
            token_value_overrides={"vorname": "FromOverride"},
        )

        self.assertEqual("hi FromOverride", result)
        provider.assert_not_called()
