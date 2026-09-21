from tapir.bestell_wizard.services.order_form_token_service import (
    OrderFormTokenService,
)
from tapir.configuration.models import TapirParameter, TapirParameterDatatype
from tapir.utils.tests_utils import mock_parameter_value
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class TestOrderFormTokenService(TapirUnitTest):
    @staticmethod
    def build_cache(revocation_link="https://example.com/widerruf"):
        cache = {}
        for key, value in {
            ParameterKeys.SITE_EMAIL: "kontakt@example.com",
            ParameterKeys.COOP_STATUTE_LINK: "https://example.com/satzung",
            ParameterKeys.SITE_PRIVACY_LINK: "https://example.com/datenschutz",
            ParameterKeys.SITE_REVOCATION_LINK: revocation_link,
            ParameterKeys.SITE_CONTRACT_TERMS_LINK: "https://example.com/agb",
        }.items():
            mock_parameter_value(key=key, value=value, cache=cache)
        return cache

    def test_replaceTokens_allTokensUsed_replacesWithFieldValues(self):
        text = (
            "((kontakt_mail)) ((satzung)) ((datenschutzerklärung)) "
            "((widerrufsbelehrung)) ((Vertragsbedingungen/AGBS))"
        )

        result = OrderFormTokenService.replace_tokens(text, self.build_cache())

        self.assertEqual(
            "kontakt@example.com https://example.com/satzung "
            "https://example.com/datenschutz https://example.com/widerruf "
            "https://example.com/agb",
            result,
        )

    def test_replaceTokens_unknownToken_staysUntouched(self):
        result = OrderFormTokenService.replace_tokens("((foo))", self.build_cache())

        self.assertEqual("((foo))", result)

    def test_findUsedTokensWithoutValue_fieldIsEmpty_returnsToken(self):
        cache = self.build_cache(revocation_link="")

        result = OrderFormTokenService.find_used_tokens_without_value(
            "<a href='((widerrufsbelehrung))'>x</a> ((satzung))", cache
        )

        self.assertEqual(["widerrufsbelehrung"], result)

    def test_findUsedTokensWithoutValue_fieldIsFilled_returnsNothing(self):
        result = OrderFormTokenService.find_used_tokens_without_value(
            "((widerrufsbelehrung))", self.build_cache()
        )

        self.assertEqual([], result)

    def test_isTextFieldOfOrderForm_titleField_returnsFalse(self):
        for key in [
            ParameterKeys.BESTELLWIZARD_STEP1A_TITLE,
            ParameterKeys.BESTELL_WIZARD_STEP4B_WAITING_LIST_MODAL_HEADER,
        ]:
            parameter = TapirParameter(
                key=key,
                category=ParameterCategory.BESTELLWIZARD,
                datatype=TapirParameterDatatype.STRING.value,
            )
            self.assertFalse(
                OrderFormTokenService.is_text_field_of_order_form(parameter)
            )

    def test_isTextFieldOfOrderForm_textField_returnsTrue(self):
        parameter = TapirParameter(
            key=ParameterKeys.BESTELLWIZARD_STEP1A_TEXT,
            category=ParameterCategory.BESTELLWIZARD,
            datatype=TapirParameterDatatype.STRING.value,
        )
        self.assertTrue(OrderFormTokenService.is_text_field_of_order_form(parameter))
