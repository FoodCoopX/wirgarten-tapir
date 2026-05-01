from unittest.mock import Mock

from tapir.payments.services.intended_use_pattern_expander import (
    IntendedUsePatternExpander,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestApplyReplacementsForLineWithMaxLength(TapirUnitTest):
    def test_applyReplacementsForLineWithMaxLength_tokenNotInLine_providerNotCalled(
        self,
    ):
        provider = Mock()
        replacements = {"vorname": provider}

        result = (
            IntendedUsePatternExpander._apply_replacements_for_line_with_max_length(
                line="static text without tokens",
                replacements=replacements,
                max_length=20,
                token_value_overrides={},
            )
        )

        self.assertEqual("static text without tokens", result)
        provider.assert_not_called()

    def test_applyReplacementsForLineWithMaxLength_tokenPresent_replacedByValue(
        self,
    ):
        replacements = {"vorname": lambda: "John"}

        result = (
            IntendedUsePatternExpander._apply_replacements_for_line_with_max_length(
                line="hi {vorname}",
                replacements=replacements,
                max_length=20,
                token_value_overrides={},
            )
        )

        self.assertEqual("hi John", result)

    def test_applyReplacementsForLineWithMaxLength_overridePresent_useOverrideInsteadOfProvider(
        self,
    ):
        provider = Mock()
        replacements = {"vorname": provider}

        result = (
            IntendedUsePatternExpander._apply_replacements_for_line_with_max_length(
                line="hi {vorname}",
                replacements=replacements,
                max_length=20,
                token_value_overrides={"vorname": "FromOverride"},
            )
        )

        self.assertEqual("hi FromOverride", result)
        provider.assert_not_called()

    def test_applyReplacementsForLineWithMaxLength_valueLongerThanMaxLength_valueTruncated(
        self,
    ):
        replacements = {"vorname": lambda: "ThisNameIsTooLong"}

        result = (
            IntendedUsePatternExpander._apply_replacements_for_line_with_max_length(
                line="{vorname}",
                replacements=replacements,
                max_length=5,
                token_value_overrides={},
            )
        )

        self.assertEqual("ThisN", result)

    def test_applyReplacementsForLineWithMaxLength_overrideLongerThanMaxLength_overrideTruncated(
        self,
    ):
        result = (
            IntendedUsePatternExpander._apply_replacements_for_line_with_max_length(
                line="{vorname}",
                replacements={"vorname": lambda: "ignored"},
                max_length=4,
                token_value_overrides={"vorname": "ThisNameIsTooLong"},
            )
        )

        self.assertEqual("ThisN"[:4], result)
