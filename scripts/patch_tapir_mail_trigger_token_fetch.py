#!/usr/bin/env python3
"""Fetch trigger tokens in the tapir-mail editor even for unsaved mails.

tapir-mail only calls /api/trigger_tokens/get_tokens/ when a configuration id
already exists. New mails (/emailconfiguration/new) therefore never get the
trigger-specific Merge-tag groups (e.g. BestellWizard: Nur Geno-Mitgliedschaft).
"""

from __future__ import annotations

import sys
from pathlib import Path

CHUNK_GLOBS = (
    "**/tapir_mail/__static__/static/js/760.*.chunk.js",
    "**/static/js/760.*.chunk.js",
    "**/static/js/760.*.chunk.*.js",
)

GATED_TRIGGER_FETCH = (
    "a&&(re.emailConfigurationVersionGetBundledInfoRetrieve({id:a})"
)
UNCONDITIONAL_BUNDLED_INFO = (
    "a&&re.emailConfigurationVersionGetBundledInfoRetrieve({id:a})"
)
GATED_TRIGGER_FETCH_TAIL = (
    "ae.triggerTokensGetTokensRetrieve().then((e=>{Q(e)}))),ie.tokensGetTokensRetrieve()"
)
UNCONDITIONAL_TRIGGER_FETCH_TAIL = (
    "ae.triggerTokensGetTokensRetrieve().then((e=>{Q(e)})),ie.tokensGetTokensRetrieve()"
)


def find_editor_chunks(search_roots: list[Path]) -> list[Path]:
    matches: list[Path] = []
    if search_roots:
        for root in search_roots:
            for glob_pattern in CHUNK_GLOBS:
                matches.extend(root.glob(glob_pattern))
    else:
        import tapir_mail

        package_dir = Path(tapir_mail.__file__).resolve().parent
        matches.extend(package_dir.glob("__static__/static/js/760.*.chunk.js"))
    unique = sorted(
        {
            path
            for path in matches
            if path.suffix == ".js" and ".map" not in path.name
        }
    )
    if not unique:
        raise FileNotFoundError(
            "Expected at least one tapir-mail editor chunk, found none"
        )
    return unique


def patch_source(source: str) -> str:
    if UNCONDITIONAL_TRIGGER_FETCH_TAIL in source and GATED_TRIGGER_FETCH not in source:
        return source
    if GATED_TRIGGER_FETCH not in source or GATED_TRIGGER_FETCH_TAIL not in source:
        raise ValueError(
            "tapir-mail editor chunk does not contain the expected gated trigger-token fetch"
        )
    patched = source.replace(GATED_TRIGGER_FETCH, UNCONDITIONAL_BUNDLED_INFO, 1)
    patched = patched.replace(
        GATED_TRIGGER_FETCH_TAIL, UNCONDITIONAL_TRIGGER_FETCH_TAIL, 1
    )
    return patched


def main() -> int:
    search_roots = [Path(p) for p in sys.argv[1:]]
    for chunk_path in find_editor_chunks(search_roots):
        original = chunk_path.read_text(encoding="utf-8")
        patched = patch_source(original)
        if patched == original:
            print(f"Already patched: {chunk_path}")
            continue
        chunk_path.write_text(patched, encoding="utf-8")
        print(f"Patched trigger-token fetch: {chunk_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
