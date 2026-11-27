# CLAUDE.md

This repository is both:

1. **A reference implementation** of the Azure Easy Auth + Google JWT 4-layer auth pattern (`backend/`, `frontend/`, `deploy/`), and
2. **A Claude Code plugin** (`azure-easy-auth-google`) whose skill tells an agent how to apply that pattern to another project. It is listed in the `SzTk/claude-patterns` marketplace.

How to *apply* the pattern lives in `skills/azure-easy-auth-google/SKILL.md`, not here. This file is about maintaining the repository itself.

## Layout

- `.claude-plugin/plugin.json` — plugin manifest (name, version)
- `skills/azure-easy-auth-google/SKILL.md` — the skill: when to use, design rationale, steps, pitfalls. It points at the reference files via `${CLAUDE_PLUGIN_ROOT}/...`
- `backend/app/core/auth.py`, `config.py` — the parts meant to be copied
- `backend/tests/` — unit tests (Google JWKS is stubbed; no network)
- `frontend/gsi-auth.js`, `frontend/nginx.conf.template`, `deploy/enable-auth.sh`

## Rules when changing this repo

- **Keep SKILL.md and the code in sync in the same commit.** If you rename/move a reference file, change a setting name, or change behavior, update the file table, steps, and pitfalls in SKILL.md.
- **Bump `version` in `.claude-plugin/plugin.json`** on every change meant to reach other environments (installed copies only update when the version changes). Do not also put `version` in the marketplace entry.
- **Update the "最終検証" line in SKILL.md** when you re-run the tests or re-verify on Azure, with the date and what was verified.
- When a pitfall is found while applying the pattern elsewhere, add it to SKILL.md's 落とし穴 section (with the date it was confirmed).

## Checks

```bash
cd backend && uv run --no-project --with-editable ".[dev]" python -m pytest -q
```

```bash
claude plugin validate .
```

Try the skill without installing: `claude --plugin-dir .` from the repo root, then `/azure-easy-auth-google:azure-easy-auth-google`.
