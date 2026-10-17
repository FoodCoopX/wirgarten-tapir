#!/usr/bin/env bash
# Creates (or repairs) the vendor-specific symlinks that point into .agents/.
#
# All AI assistant configuration lives in .agents/; every tool-specific path is a symlink into it.
# Those symlinks are committed, so on Linux and macOS a plain checkout already works and this
# script only verifies them. On Windows, Git writes plain text files instead of symlinks unless
# `git config --global core.symlinks true` is set (requires Developer Mode) — run this script
# afterwards to turn them into real links.
#
# Usage:
#   ./scripts/setup_agent_links.sh           create or repair the links
#   ./scripts/setup_agent_links.sh --check   report only, exit 1 if something is wrong

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CHECK_ONLY=false
if [ "${1:-}" = "--check" ]; then
  CHECK_ONLY=true
elif [ -n "${1:-}" ]; then
  echo "unknown argument: $1" >&2
  echo "usage: $0 [--check]" >&2
  exit 2
fi

# "<link path>:<target, relative to the link's own directory>"
LINKS=(
  "AGENTS.md:.agents/rules/base-rules.md"
  ".github/agents:../.agents/agents"
  ".claude/agents:../.agents/agents"
  ".claude/skills:../.agents/skills"
  ".opencode/agents:../.agents/agents"
)

failures=0
changes=0

for entry in "${LINKS[@]}"; do
  link="${entry%%:*}"
  target="${entry#*:}"

  if [ -L "$link" ] && [ "$(readlink "$link")" = "$target" ] && [ -e "$link" ]; then
    echo "ok       $link -> $target"
    continue
  fi

  if $CHECK_ONLY; then
    if [ -L "$link" ]; then
      echo "BROKEN   $link -> $(readlink "$link") (expected $target)"
    elif [ -e "$link" ]; then
      echo "NOT LINK $link (expected a symlink to $target)"
    else
      echo "MISSING  $link (expected a symlink to $target)"
    fi
    failures=$((failures + 1))
    continue
  fi

  mkdir -p "$(dirname "$link")"
  rm -rf "$link"
  ln -s "$target" "$link"
  echo "linked   $link -> $target"
  changes=$((changes + 1))
done

if $CHECK_ONLY; then
  if [ "$failures" -gt 0 ]; then
    echo
    echo "$failures link(s) need repair. Run $0 without --check."
    exit 1
  fi
  echo
  echo "All AI assistant links are in place."
  exit 0
fi

echo
if [ "$changes" -gt 0 ]; then
  echo "Repaired $changes link(s)."
  echo "If git now shows these as modified, your checkout had no symlink support."
  echo "Enable it with: git config --global core.symlinks true"
else
  echo "Nothing to do, all links were already in place."
fi
