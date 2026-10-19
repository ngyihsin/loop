# Reference Projects: What We Borrow and What We Don't

**Project Docs:** [README](../README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [references](references.md) *(you are here)* | [HANDOFF](../HANDOFF.md)

## autopilot — pavlov-net/autopilot (the skeleton)

A fully autonomous loop on Linear + the Claude Agent SDK: Executor (Ready → PR), Monitor (CI failure / conflict /
review → fixer), Planning (a CTO agent with PM, Scout, Security, Quality, Architect files new issues), Projects
(project owners decompose issues), and Reviewer (analyzes agent transcripts and files improvement issues).

**Borrow**
- Issue-tracker state drives everything; "prompts are the product, the TypeScript is plumbing".
- The executor phases: Understand → Plan → Implement → Validate (max 3 attempts) → Simplify → Commit/Push →
  update the tracker; "when in doubt, block".
- Fixer rules: fix only the failure, no refactors, never edit tests to pass, never force-push, touch only branches
  the system created (`autopilot-*` → our `loop/*`).
- The Reviewer agent mining run transcripts for failure patterns → our `reflect`.
- Engineering: parallel slots, timeout + AbortController, circuit breaker, retry, sandboxing.

**Change or skip**
- Linear SDK → Jira REST/JQL; Linear states → Jira labels (no workflow change).
- GitHub PRs / Actions / auto-merge → Gerrit changes / Jenkins Verified / human submit.
- A worktree per issue → fixed slots of a synced manifest tree plus `repo start`.
- Planning (agents filing their own work) deferred to Phase 5; the dashboard is skipped.

## pstack — backnotprop/pstack (engineering discipline)

poteto's Agent Skills: `poteto-mode` with playbooks (bug-fix, feature, investigation, babysit, autopilot-full, …),
`principle-*` skills, and `reflect`, `recall`, `tdd`, `unslop`, `create-verification-skill`.

**Borrow**
- **bug-fix playbook:** reproduce first → rule out hypotheses with the experiment that splits the space most →
  confirm the mechanism with runtime evidence → smallest fix; failing repro lands before the fix. This is the
  method of `bug-analyze` and `implement`.
- **autopilot-full:** the agent that wrote the code never certifies it; an independent verifier does → `review-prep`
  runs as a separate agent.
- **create-verification-skill:** interview the repo, not the user; prove commands by running them → `repo-onboard`
  and the `device` skill's doctor step.
- `reflect` (several reviewer angles + a synthesizer) and `show-me-your-work` (decision trail) → dossier `runs/`.
- Principles: Laziness Protocol (smallest diff), Fix Root Causes, Prove It Works.

**Skip:** Cursor-specific multi-model routing, Graphite stacked PRs.

## docforge — ThinkerYzu/docforge (feature interviews)

`AGENT-warm-up.md` as the session entry; SPEC → DESIGN → IMPLEMENTATION-GUIDE → HANDOFF + session logs; "ask,
don't tell"; "discuss first, code later".

**Borrow**
- The whole flow becomes the `feature-spec` skill, with output in `dossier/<KEY>/`.
- HANDOFF's quality bar ("could a new team member continue without asking questions?") applies to every stage.
- This repo's own docs use the docforge structure.

**Change:** IMPLEMENTATION-GUIDE steps map to Jira sub-tasks, each one an independently verifiable Gerrit change.

## llm_wiki — nashsu/llm_wiki (knowledge pattern)

A desktop app for Karpathy's LLM-Wiki pattern: immutable raw sources → LLM-maintained wiki → schema; Ingest /
Query / Lint; `purpose.md`; two-step ingest (analyze, then generate); `sources:` frontmatter; an MCP server.

**Borrow:** the file layout (`purpose.md`, `schema.md`, `index.md`, `log.md`, `[[wikilinks]]`), two-step ingest,
source traceability. Phase 0 uses plain markdown; the folder opens in Obsidian or llm_wiki if a graph/search UI is
wanted later.

## TencentDB Agent Memory (team memory — later, maybe)

Memory Hub: layered chat memory (L0 → L3), a versioned skill library, Wiki, CodeGraph (symbols, callers, impact),
attached to Claude Code via a proxy base URL.

**Borrow (ideas):** "anything that saves the next agent rework should be stored"; skills with versions and
validation rules.

**Defer:** the company's CodeAtlas MCP already provides the code graph, cases, and docs; distilled lessons fit in a
file-based knowledge repo. Re-evaluate when many users need shared memory with access control.

## open-slide — open-slide/open-slide (reports)

A React slide framework for agents (1920×1080 canvas) with `create-slide`, `slide-authoring`, `apply-comments`, and
`create-theme` skills; exports HTML / PDF / PPTX; in-browser comments → `/apply-comments`.

**Borrow:** the `report` agent reads the dossier (SPEC, DESIGN, analysis, op-gap, review notes), Jira, and git log
and drafts a deck with `create-slide`; the company template becomes a `theme`; the engineer comments in the
inspector and the agent applies them; PPTX export for delivery.
