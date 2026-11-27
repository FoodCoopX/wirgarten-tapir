from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings


class UserProfileError(ValueError):
    pass


def resolve_user_profile_path(path: str) -> Path:
    profile_path = Path(path).expanduser()
    if profile_path.is_absolute():
        return profile_path
    return Path(settings.BASE_DIR).parent / profile_path


def load_user_profile(path: str) -> dict:
    if not path:
        raise UserProfileError(
            "KEYCLOAK_USER_PROFILE_FILE is not set but "
            "KEYCLOAK_USER_PROFILE_MANAGED is true"
        )

    profile_path = resolve_user_profile_path(path)
    try:
        raw = profile_path.read_text(encoding="utf-8")
    except OSError as error:
        raise UserProfileError(
            f"{str(profile_path)!r} cannot be read: {error}"
        ) from error

    try:
        profile = json.loads(raw)
    except json.JSONDecodeError as error:
        raise UserProfileError(
            f"{str(profile_path)!r} is not valid JSON: {error}"
        ) from error

    if not isinstance(profile, dict):
        raise UserProfileError(f"{str(profile_path)!r} must contain a JSON object")

    attributes = profile.get("attributes")
    if not isinstance(attributes, list):
        raise UserProfileError(
            f"{str(profile_path)!r} must contain an 'attributes' list"
        )

    names = []
    for index, attribute in enumerate(attributes):
        if (
            not isinstance(attribute, dict)
            or not isinstance(attribute.get("name"), str)
            or not attribute["name"]
        ):
            raise UserProfileError(
                f"{str(profile_path)!r} attribute {index} must have a "
                "non-empty 'name'"
            )
        names.append(attribute["name"])

    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise UserProfileError(
            f"{str(profile_path)!r} has duplicate attributes: " + ", ".join(duplicates)
        )

    return profile


def missing_user_profile_attributes(
    profile: dict, attribute_map: list[dict]
) -> tuple[str, ...]:
    present = {attribute["name"] for attribute in profile["attributes"]}
    return tuple(
        entry["keycloak"] for entry in attribute_map if entry["keycloak"] not in present
    )


def load_managed_user_profile(path: str, attribute_map: list[dict]) -> dict:
    profile = load_user_profile(path)
    missing = missing_user_profile_attributes(profile, attribute_map)
    if missing:
        raise UserProfileError(
            "KEYCLOAK_USER_PROFILE_ATTRIBUTE_MAP maps attributes that are "
            f"missing from KEYCLOAK_USER_PROFILE_FILE={path!r}: " + ", ".join(missing)
        )
    return profile
