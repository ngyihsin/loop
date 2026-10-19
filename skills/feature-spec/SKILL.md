---
name: feature-spec
description: Interview the engineer step by step (docforge style) to turn a Jira feature request — a new framework API, a new FastRPC call, a new backend capability — into SPEC.md, DESIGN.md and IMPLEMENTATION-GUIDE.md, then propose Jira sub-tasks, one per independently verifiable change. Use for "/feature-spec <JIRA-KEY>", "spec out this feature", "new API / new RPC for ...".
---

# feature-spec

Docforge's flow, scoped to one Jira ticket and stored in `$LOOP_DOSSIER/<KEY>/`. You draft; the human decides.
Read `$LOOP_HOME/skills/CONVENTIONS.md` first.

Principles (from docforge): discuss first, code later. Ask, don't tell — propose a solution and let the
engineer correct it; a proposal they push back on surfaces a misunderstanding cheaply. Keep documents honest:
when later stages learn the spec was wrong, they update the spec first.

## Phase 1 — SPEC.md

1. Fetch the ticket; read linked tickets, the Confluence pages it cites, and related knowledge entries.
2. Research before asking: use CodeAtlas to find the existing API surface, callers, and the closest precedent
   (the last time a similar API or RPC was added — its change, its review comments).
3. Ask in small rounds (2–4 questions per round), each with your recommended answer. Cover: problem and user
   (who calls this API?), goals / non-goals, functional and non-functional requirements (latency, memory,
   thread-safety, power), compatibility constraints, success criteria that a test can check, open questions.
4. Write SPEC.md (template: docforge `SPEC.md`). Status `Approved` only when the engineer says so.

## Phase 2 — DESIGN.md and IMPLEMENTATION-GUIDE.md

Architecture, the decisions with alternatives and rationale, and the data model / interface. For API or RPC
work, DESIGN.md must answer every item in `references/api-rpc-checklist.md`; write "N/A because ..." rather than
skipping one.

IMPLEMENTATION-GUIDE.md: ordered steps, each one a change that builds, has its own test, and can be reviewed
alone in Gerrit (e.g. 1. IDL + generated stubs, 2. DSP-side skel implementation + unit test, 3. host API + test,
4. framework integration, 5. docs/sample). Name the git, files, build and test command for each step.

## Phase 3 — Decompose into Jira

Propose one sub-task per IMPLEMENTATION-GUIDE step (summary, description linking the dossier section,
acceptance = that step's test). Print the list and wait for approval; creating sub-tasks is a Jira write.
After approval each sub-task gets `agent:ready` and enters the `implement` stage.

Update `HANDOFF.md` after every session — the docforge test: could a new engineer implement the next step from
it without asking questions?
