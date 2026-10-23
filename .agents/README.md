# `.agents/` — shared AI assistant configuration

This folder is the **single source of truth** for AI coding assistant configuration in this
repository. Contributors use different tools (GitHub Copilot, Claude Code, OpenCode, Codex, …),
and each of them looks for its configuration in a different place. Instead of maintaining the
same rules three times, every vendor-specific path is either a **native location** of this folder
or a **symlink** into it.

Write the instruction once here, and every assistant picks it up.

## Layout

```
.agents/
├── rules/      Repository-wide rules and context (always loaded)
├── agents/     Specialised role profiles, one Markdown file per agent (loaded when selected)
└── skills/     Repeatable task recipes, one folder per skill with a SKILL.md (loaded on demand)
```

- **rules** — always in context. Keep it short, factual and repo-specific; it costs tokens on
  every single request. [rules/base-rules.md](rules/base-rules.md) is the repo map.
- **agents** — a role ("code reviewer", "migration writer") with its own instructions. Only loaded
  when a user or another agent picks that role.
- **skills** — a procedure for a recurring task ("regenerate the API client"). The assistant reads
  the short description and loads the full file only when the task comes up.

## Vendor mapping

| Vendor path | Kind | Points at |
|---|---|---|
| `AGENTS.md` | symlink | `.agents/rules/base-rules.md` |
| `.github/agents/` | symlink | `.agents/agents/` |
| `.claude/agents/` | symlink | `.agents/agents/` |
| `.claude/skills/` | symlink | `.agents/skills/` |
| `.opencode/agents/` | symlink | `.agents/agents/` |
| `.agents/skills/` | native | read directly by Copilot (VS Code, CLI, coding agent), OpenCode and Codex |

`AGENTS.md` is read natively by Copilot, OpenCode, Codex and Cursor. Claude Code reads it too,
**unless** a `CLAUDE.md` exists — `CLAUDE.md` is git-ignored here, so don't add one. If you want a
personal one, make it import the shared rules with a single line: `@AGENTS.md`.

Some paths are deliberately *not* linked, because the tools in question already find the content
and a second copy would only be discovered twice:

- `.github/skills/` and `.opencode/skills/` — Copilot and OpenCode read `.agents/skills/` natively.
- `.github/copilot-instructions.md` — VS Code discovers `AGENTS.md` as project instructions, and
  would load both files into the same session.

## Writing portable files

The three vendors share a format, but only for a subset of the frontmatter. Stick to the subset so
one file works everywhere.

**Agents** — `.agents/agents/<name>.md`:

```markdown
---
name: code-reviewer
description: Reviews a diff against this repository's conventions.
---

Instructions for the role…
```

- Use a plain `.md` extension, not `.agent.md`: OpenCode derives the agent name from the file name,
  so `foo.agent.md` would become an agent called `foo.agent`.
- `name` and `description` are the only portable fields. Vendor-specific keys (`tools`, `model`,
  `mode`, `permission`, …) use incompatible value formats across vendors — leave them out, or
  accept that they only work for the vendor you wrote them for.

**Skills** — `.agents/skills/<name>/SKILL.md`:

```markdown
---
name: regenerate-api-client
description: When to use this skill. Be specific — this is what the model matches against.
---

Steps…
```

- The folder name must equal `name`, lowercase with single hyphens.
- Supporting files (scripts, templates) go next to `SKILL.md` and must be referenced from it with
  relative links to be picked up.

**References to repository files** are written relative to the repository root (`tapir/urls.py`, not
`../../tapir/urls.py`), because that is where assistants run — so they are not clickable when
browsing this folder on GitHub. Links *between* files inside `.agents/`, and links to a skill's own
supporting files, use normal relative paths.

## Checkout notes

The vendor paths are git-tracked symlinks. On Linux and macOS they just work.

On **Windows**, Git only creates real symlinks when symlink support is enabled — otherwise you get
plain text files containing the link target, and no assistant will find anything. Enable it once:

```powershell
git config --global core.symlinks true   # then re-clone, or re-checkout the affected paths
```

This requires Developer Mode (Settings → System → For developers) or an elevated shell.

To verify or repair the links in an existing checkout, run:

```bash
./scripts/setup_agent_links.sh          # --check to only report
```
