from django.core.exceptions import ValidationError


class MandateReferencePatternValidator:
    MANDATE_REF_LENGTH = 35
    RANDOM_TOKEN_ALPHABET = "1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    ALLOWED_SYMBOLS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ+?/-:().,"
    TOKEN_FIRST_NAME = "vorname"
    TOKEN_LAST_NAME = "nachname"
    TOKEN_MEMBER_NUMBER_SHORT = "mitgliedsnummer_kurz"
    TOKEN_MEMBER_NUMBER_LONG = "mitgliedsnummer_lang"
    TOKEN_MEMBER_NUMBER_WITHOUT_PREFIX = "mitgliedsnummer_ohne_prefix"
    TOKEN_RANDOM = "zufall"

    ALL_TOKENS = [
        TOKEN_FIRST_NAME,
        TOKEN_LAST_NAME,
        TOKEN_MEMBER_NUMBER_SHORT,
        TOKEN_MEMBER_NUMBER_LONG,
        TOKEN_MEMBER_NUMBER_WITHOUT_PREFIX,
        TOKEN_RANDOM,
    ]

    TOKENS_THAT_REQUIRE_A_MEMBER_NUMBER = [
        TOKEN_MEMBER_NUMBER_SHORT,
        TOKEN_MEMBER_NUMBER_LONG,
        TOKEN_MEMBER_NUMBER_WITHOUT_PREFIX,
    ]

    @classmethod
    def validate_pattern(cls, pattern: str):
        cls.validate_pattern_contains_at_least_one_unique_token(pattern)
        cls.validate_member_numbers_can_only_be_used_if_they_are_always_assigned(
            pattern
        )
        cls.validate_pattern_doesnt_container_illegal_characters(pattern)

    @classmethod
    def validate_pattern_contains_at_least_one_unique_token(cls, pattern: str):
        required_tokens = cls.TOKENS_THAT_REQUIRE_A_MEMBER_NUMBER + [cls.TOKEN_RANDOM]
        if any(
            cls.get_token_with_braces(token) in pattern for token in required_tokens
        ):
            return

        raise ValidationError(
            f"Es muss mindestens ein einzigartiges Token verwendet werden: {",".join(cls.TOKENS_THAT_REQUIRE_A_MEMBER_NUMBER + [cls.TOKEN_RANDOM])}"
        )

    @classmethod
    def validate_member_numbers_can_only_be_used_if_they_are_always_assigned(
        cls, pattern: str
    ):
        # TODO: to be implemented one US 4.3, PR #1084 is merged
        return
        if any(
            cls.get_token_with_braces(token) in pattern
            for token in cls.TOKENS_THAT_REQUIRE_A_MEMBER_NUMBER
        ) and get_parameter_value(
            ParameterKeys.MEMBER_NUMBER_ONLY_AFTER_TRIAL, cache={}
        ):
            raise ValidationError(
                "Mitgliedsnummer dürfen in der Mandatsreferenzen nur stehen wenn das Parameter 'Mitgliedsnummer erst nach Ablauf der Probezeit vergeben' ausgeschaltet ist"
            )

    @classmethod
    def validate_pattern_doesnt_container_illegal_characters(cls, pattern: str):
        for token in cls.ALL_TOKENS:
            pattern = pattern.replace(cls.get_token_with_braces(token), "")

        pattern = pattern.upper()

        for symbol in pattern:
            if symbol not in cls.ALLOWED_SYMBOLS:
                raise ValidationError(
                    f"Dieses Zeichen ist nicht in Mandatsreferenzen erlaubt: {symbol}, pattern: {pattern}"
                )

    @staticmethod
    def get_token_with_braces(token: str):
        return f"{{{token}}}"
