# AGENTS.md — working on the loop repo itself

This file is for agents (Codex, Claude Code) that **develop loop**. The skills in `skills/` are for agents that
**use** loop on Jira tickets; their shared rules are in `skills/CONVENTIONS.md`.

## Start every session here

1. Read `HANDOFF.md` (status, decisions, open questions, next actions).
2. Read `docs/SPEC.md` and `docs/DESIGN.md` for the part you are changing.
3. At the end of the session, update `HANDOFF.md` (status checklist, decisions, a one-line session log) — the
   docforge rule: a new engineer must be able to continue from it without asking questions.

## Layout

| Path | What |
|---|---|
| `skills/<name>/SKILL.md` | one skill per pipeline stage (Agent Skills format; YAML frontmatter `name`, `description`) |
| `skills/CONVENTIONS.md`, `skills/references/` | rules and checklists shared by all skills |
| `tools/` | deterministic helpers the skills call (`jira.py`) with their tests |
| `knowledge-template/` | template for the internal knowledge repo (not the knowledge itself) |
| `docs/` | SPEC, DESIGN, references (docforge structure) |
| `*.example.yml` | config templates; the real `devices.yml`, `build-hosts.yml`, `loop.yml` are git-ignored |

## Rules

- **English** for all docs, code, comments, and commit messages.
- **No company data in this repo**: no internal hostnames, tokens, ticket contents, logs, device serials, or
  knowledge pages. Those live in git-ignored files or internal repos. Check `git diff --cached` before committing.
- **Tools are Python 3 standard library only**, so they run on any workstation or build server without installs.
  Writes to external systems (Jira, Gerrit) are dry-run unless `--apply` is passed.
- Every tool change comes with a test against a local fake server (see `tools/test_jira.py`).
  Run: `python3 -m unittest discover -s tools -p 'test_*.py'`
- Skill changes: keep `SKILL.md` focused on the workflow; put long checklists in `references/`. A skill must say its
  input, its output files in the dossier, what it may write, and when it must stop and block. Reference shared
  files by `$LOOP_HOME/...`, since skills are symlinked into `~/.codex/skills` / `~/.claude/skills`.
- After adding a skill, add it to the skills table in `README.md` and the agents table in `docs/DESIGN.md`, and
  re-run `scripts/install-skills.sh`.
- When implementation shows the design was wrong, update `docs/DESIGN.md` (or `docs/SPEC.md`) in the same change.

## Next work

See `HANDOFF.md → Next Actions`. Planned skills: `implement` (Gerrit WIP upload), `review-prep`, `report`
(open-slide), `reflect`; then the Phase 1 orchestrator.
