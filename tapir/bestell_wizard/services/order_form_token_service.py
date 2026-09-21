import re

from tapir.configuration.parameter import get_parameter_value
from tapir.configuration.models import TapirParameter, TapirParameterDatatype
from tapir.wirgarten.constants import ParameterCategory
from tapir.wirgarten.parameter_keys import ParameterKeys


class OrderFormTokenService:
    """
    Tokens like ((satzung)) that can be used in the text fields of the order form.
    They are replaced by the value of the config field they point to.
    """

    TOKEN_TO_PARAMETER_KEY = {
        "kontakt_mail": ParameterKeys.SITE_EMAIL,
        "satzung": ParameterKeys.COOP_STATUTE_LINK,
        "datenschutzerklärung": ParameterKeys.SITE_PRIVACY_LINK,
        "widerrufsbelehrung": ParameterKeys.SITE_REVOCATION_LINK,
        "vertragsbedingungen/agbs": ParameterKeys.SITE_CONTRACT_TERMS_LINK,
    }
    DISPLAY_TOKENS = [
        "((kontakt_mail))",
        "((satzung))",
        "((datenschutzerklärung))",
        "((widerrufsbelehrung))",
        "((Vertragsbedingungen/AGBS))",
    ]
    TOKEN_PATTERN = re.compile(r"\(\(([^()]*)\)\)")
    NON_TEXT_KEY_PARTS = ["background", "solidarity_step_position"]
    TITLE_KEY_SUFFIXES = (".title", ".header")

    @classmethod
    def is_text_field_of_order_form(cls, parameter: TapirParameter) -> bool:
        return (
            parameter.category == ParameterCategory.BESTELLWIZARD
            and parameter.datatype == TapirParameterDatatype.STRING.value
            and not any(part in parameter.key for part in cls.NON_TEXT_KEY_PARTS)
            and not parameter.key.endswith(cls.TITLE_KEY_SUFFIXES)
        )

    @classmethod
    def find_used_tokens(cls, text: str) -> set[str]:
        used = set()
        for match in cls.TOKEN_PATTERN.findall(text or ""):
            token = match.strip().lower()
            if token in cls.TOKEN_TO_PARAMETER_KEY:
                used.add(token)
        return used

    @classmethod
    def find_used_tokens_without_value(cls, text: str, cache: dict = None) -> list[str]:
        return sorted(
            token
            for token in cls.find_used_tokens(text)
            if not cls.get_token_value(token, cache)
        )

    @classmethod
    def get_token_value(cls, token: str, cache: dict = None) -> str:
        return (
            get_parameter_value(cls.TOKEN_TO_PARAMETER_KEY[token], cache=cache) or ""
        ).strip()

    @classmethod
    def replace_tokens(cls, text: str, cache: dict = None) -> str:
        if not isinstance(text, str):
            return text

        def replace(match):
            token = match.group(1).strip().lower()
            if token not in cls.TOKEN_TO_PARAMETER_KEY:
                return match.group(0)
            return cls.get_token_value(token, cache)

        return cls.TOKEN_PATTERN.sub(replace, text)
