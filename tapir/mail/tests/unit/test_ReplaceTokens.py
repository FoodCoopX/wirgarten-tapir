from types import SimpleNamespace
from unittest.mock import patch

from tapir.mail.services.token import (
    TOKEN_TYPE_DYNAMIC,
    TOKEN_TYPE_GENERAL,
    TOKEN_TYPE_RECIPIENT,
    find_tokens,
    replace_tokens,
    resolve_recipient_tokens,
    token_registry,
)
from tapir.wirgarten.tests.test_utils import TapirUnitTest


class ReplaceTokensTest(TapirUnitTest):
    @staticmethod
    def _build_registry(
        general_tokens: dict | None = None, recipient_tokens: dict | None = None
    ) -> dict:
        return {
            TOKEN_TYPE_RECIPIENT: recipient_tokens or {},
            TOKEN_TYPE_GENERAL: general_tokens or {},
            TOKEN_TYPE_DYNAMIC: {},
        }

    def test_replaceTokens_givenCache_passesItToAllGeneralTokens(self):
        received_caches = []

        def general_token(cache: dict):
            received_caches.append(cache)
            return "value"

        given_cache = {}
        with patch.dict(
            token_registry,
            self._build_registry(
                general_tokens={"A": general_token, "B": general_token}
            ),
        ):
            result = replace_tokens(
                "{{Allgemein.A}} {{Allgemein.B}}", cache=given_cache
            )

        self.assertEqual("value value", result)
        self.assertEqual(2, len(received_caches))
        self.assertIs(given_cache, received_caches[0])
        self.assertIs(given_cache, received_caches[1])

    def test_replaceTokens_noCacheGiven_usesAFreshCacheForEachCall(self):
        def general_token(cache: dict):
            cache["calls"] = cache.get("calls", 0) + 1
            return cache["calls"]

        with patch.dict(
            token_registry, self._build_registry(general_tokens={"A": general_token})
        ):
            first = replace_tokens("{{Allgemein.A}}")
            second = replace_tokens("{{Allgemein.A}}")

        self.assertEqual("1", first)
        self.assertEqual("1", second)

    def test_replaceTokens_generalTokenIsString_replacesWithString(self):
        with patch.dict(
            token_registry, self._build_registry(general_tokens={"A": "static"})
        ):
            result = replace_tokens("{{Allgemein.A}}")

        self.assertEqual("static", result)

    def test_findTokens_recipientTokens_returnsAttributeNameOrLabelForCallables(self):
        def callable_token(recipient: object, cache: dict):
            return "value"

        with patch.dict(
            token_registry,
            self._build_registry(
                recipient_tokens={"Vorname": "first_name", "Abholort": callable_token}
            ),
        ):
            result = find_tokens("{{Empfänger.Vorname}} {{Empfänger.Abholort}}")

        self.assertEqual({"first_name", "Abholort"}, set(result))

    def test_resolveRecipientTokens_callableToken_calledWithRecipientAndCache(self):
        received_arguments = []

        def callable_token(recipient: object, cache: dict):
            received_arguments.append((recipient, cache))
            return "Callable value"

        recipient = SimpleNamespace(first_name="Max")
        given_cache = {}
        with patch.dict(
            token_registry,
            self._build_registry(
                recipient_tokens={"Vorname": "first_name", "Abholort": callable_token}
            ),
        ):
            result = resolve_recipient_tokens(
                tokens_to_resolve=["first_name", "Abholort"],
                recipient=recipient,
                cache=given_cache,
            )

        self.assertEqual({"first_name": "Max", "Abholort": "Callable value"}, result)
        self.assertEqual(1, len(received_arguments))
        self.assertIs(recipient, received_arguments[0][0])
        self.assertIs(given_cache, received_arguments[0][1])

    def test_replaceTokens_callableRecipientToken_usesValueStoredUnderLabel(self):
        def callable_token(recipient: object, cache: dict):
            return "unused"

        with patch.dict(
            token_registry,
            self._build_registry(
                recipient_tokens={"Vorname": "first_name", "Abholort": callable_token}
            ),
        ):
            result = replace_tokens(
                "{{Empfänger.Vorname}} {{Empfänger.Abholort}}",
                recipient_tokens={"first_name": "Max", "Abholort": "Station"},
            )

        self.assertEqual("Max Station", result)
