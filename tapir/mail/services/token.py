import logging
import re
from typing import Any, Callable

from django.conf import settings

from tapir.mail.addressed_recipient import MailRecipient
from tapir.mail.services.segment import _check_base_queryset

LOG = logging.getLogger(__name__)

TOKEN_TYPE_RECIPIENT = "Empfänger"
TOKEN_TYPE_DYNAMIC = "Empfänger (extra)"
TOKEN_TYPE_GENERAL = "Allgemein"

token_registry = {
    TOKEN_TYPE_RECIPIENT: {},
    TOKEN_TYPE_GENERAL: {},
    TOKEN_TYPE_DYNAMIC: {},
}


def _register_user_tokens(user_tokens: dict):
    _check_base_queryset()

    LOG.info(f"Registering tokens {user_tokens}")

    from tapir.mail.services.segment import BASE_QUERYSET

    for label, value in user_tokens.items():
        if callable(value):
            continue
        if not isinstance(value, str):
            raise ValueError(
                f"User token {label} is not a string or callable! Check your token registration."
            )
        if not hasattr(BASE_QUERYSET.model, value):
            raise ValueError(
                f"Model {BASE_QUERYSET.model} does not have attribute {value}! Check your token registration for {label}."
            )

    token_registry[TOKEN_TYPE_RECIPIENT].update(user_tokens)


def _register_general_tokens(general_tokens: dict):
    LOG.info(f"Registering general tokens {general_tokens}")

    for k, v in general_tokens.items():
        if not callable(v) and not isinstance(v, str):
            raise ValueError(
                f"General token {k} is not a string or callable! Check your token registration."
            )

    token_registry[TOKEN_TYPE_GENERAL].update(general_tokens)


def _register_dynamic_tokens(dynamic_tokens: dict):
    LOG.info(f"Registering dynamic tokens {dynamic_tokens}")

    for k, v in dynamic_tokens.items():
        if not callable(v):
            raise ValueError(
                f"General token {k} is not a callable! Check your token registration."
            )

    token_registry[TOKEN_TYPE_DYNAMIC].update(dynamic_tokens)


def get_recipient_token_storage_key(label: str, value: str | Callable) -> str:
    return label if callable(value) else value


def register_tokens(user_tokens: dict, general_tokens: dict, dynamic_tokens: dict):
    _register_user_tokens(user_tokens)
    _register_general_tokens(general_tokens)
    _register_dynamic_tokens(dynamic_tokens)


def find_tokens(mjml: str, token_type: str = TOKEN_TYPE_RECIPIENT) -> list[Any]:
    """
    Find all unique tokens enclosed in double curly braces in the given MJML string,
    and resolve them using the provided token_registry.

    :param mjml: The MJML string to search for tokens.
    :param token_registry: A dictionary with the token types and keys.
    :return: A dict containing the resolved tokens and their corresponding keys.
    """
    pattern = re.compile(r"\{\{\s*(.*?)\s*\}\}")
    matches = pattern.findall(mjml)
    unique_tokens = set(matches)

    result_tokens = []
    for token in unique_tokens:
        t_type, key = token.split(".")
        if t_type == token_type and key in token_registry[t_type]:
            result_tokens.append(
                get_recipient_token_storage_key(
                    label=key, value=token_registry[t_type][key]
                )
                if token_type == TOKEN_TYPE_RECIPIENT
                else key
            )

    return result_tokens


def resolve_recipient_tokens(
    tokens_to_resolve: list[str], recipient: MailRecipient, cache: dict
) -> dict:
    """
    Resolve all tokens that are registered as recipient tokens and return them as a dict.

    :return: A dict containing the resolved tokens.
    """
    callables_by_storage_key = {
        label: value
        for label, value in token_registry[TOKEN_TYPE_RECIPIENT].items()
        if callable(value)
    }
    recipient_tokens = {}
    for token_key in tokens_to_resolve:
        if token_key in callables_by_storage_key:
            value = callables_by_storage_key[token_key](recipient, cache)
        else:
            value = getattr(recipient, token_key, "")
        recipient_tokens[token_key] = str(value or "")
    return recipient_tokens


def resolve_dynamic_tokens(
    tokens_to_resolve: list[str], recipient: MailRecipient, cache: dict
) -> dict:
    dynamic_tokens = {}
    for token in tokens_to_resolve:
        dynamic_tokens[token] = token_registry[TOKEN_TYPE_DYNAMIC][token](
            recipient, cache
        )
    return dynamic_tokens


def replace_tokens(
    mjml: str,
    recipient_tokens=None,
    transactional_tokens=None,
    strict_token_validation=None,
    cache: dict | None = None,
):
    if cache is None:
        cache = {}
    if recipient_tokens is None:
        recipient_tokens = {}
    if transactional_tokens is None:
        transactional_tokens = {}
    if strict_token_validation is None:
        strict_token_validation = (
            settings.EMAIL_TOKENS_STRICT_VALIDATION
            if hasattr(settings, "EMAIL_TOKENS_STRICT_VALIDATION")
            else True
        )

    def _do_replace(current_mjml, key, value):
        if value is None:
            value = ""
        return re.sub(
            re.compile(r"\{\{\s*(" + re.escape(key) + r")\s*\}\}"),
            str(value),
            current_mjml,
        )

    for token_type, tokens in token_registry.items():
        if token_type == TOKEN_TYPE_RECIPIENT:
            for key, value in tokens.items():
                mjml = _do_replace(
                    mjml,
                    f"{token_type}.{key}",
                    recipient_tokens.get(
                        get_recipient_token_storage_key(label=key, value=value), ""
                    ),
                )
        elif token_type == TOKEN_TYPE_GENERAL:
            for key, value in tokens.items():
                mjml = _do_replace(
                    mjml,
                    f"{token_type}.{key}",
                    value(cache) if callable(value) else value,
                )
        elif token_type == TOKEN_TYPE_DYNAMIC:
            for key, _ in tokens.items():
                mjml = _do_replace(
                    mjml,
                    f"{token_type}.{key}",
                    recipient_tokens.get(key, ""),
                )

    for key, value in transactional_tokens.items():
        mjml = _do_replace(mjml, key, value)

    pattern = re.compile(r"\{\{\s*(.*?)\s*\}\}")
    matches = list(set(pattern.findall(mjml)))
    if matches:
        if strict_token_validation:
            raise ValueError(
                f"Unknown Tokens: {matches}. To ignore unknown tokens, set EMAIL_TOKENS_STRICT_VALIDATION=False."
            )
        else:
            LOG.warning(
                f"Unknown Tokens: {matches}. To abort sending, set EMAIL_TOKENS_STRICT_VALIDATION=True."
            )

            # replace unknown tokens with empty string
            for match in matches:
                mjml = re.sub(
                    re.compile(r"\{\{\s*(" + re.escape(match) + r")\s*\}\}"),
                    "",
                    mjml,
                )

    return mjml
