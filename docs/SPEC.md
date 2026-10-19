# Spec: loop — an agent development loop for Jira + Android repo + Gerrit

**Created:** 2026-10-19
**Status:** Draft v3

**Project Docs:** [README](../README.md) | [SPEC](SPEC.md) *(you are here)* | [DESIGN](DESIGN.md) | [references](references.md) | [HANDOFF](../HANDOFF.md)

---

## Problem Statement

Engineers spend much of their time on process work: reading Jira, reading logs, finding root causes, changing
code, running builds, uploading for review, answering review comments, writing reports and slides. Each step
follows a pattern, but today a human stitches all of them together.

[autopilot](https://github.com/pavlov-net/autopilot) shows that "issue-tracker state drives Claude Code agents
working in isolated checkouts" works. It assumes, however:

- Linear (we use Jira)
- one GitHub repo, PRs, GitHub Actions (we use an Android `repo` manifest of many gits, Gerrit, Jenkins, and heavy
  multi-platform builds)
- one kind of work, "implement the issue" (we also need bug analysis, model enablement, API design interviews,
  review preparation, and reports)

### Background

- **Domain:** Qualcomm AI-accelerated NPU frameworks — QNN, SNPE, Hexagon NN, ExecuTorch (QNN backend), ONNX Runtime
  (QNN EP), and host ↔ DSP FastRPC. The code is mostly **C++ and Python**.
- **Scope:** the manifest has many gits; the engineer owns 2–3 of them. Agents **write** only there and **read**
  everything else (callers, framework behavior).
- **Tooling (confirmed):** Gerrit for review, Jenkins for CI (Verified), Jira on a company-hosted URL with API
  token access to labels and comments. Agents run on the engineer's workstation or build server; Claude Code and
  Codex are both approved.
- **Devices:** reproduction needs real hardware — Android devices over **adb**, and **Windows on Snapdragon (arm64)
  laptops over ssh**.
- **Existing knowledge:** the **CodeAtlas MCP server** (`search_semantic`, `find_symbol`, `get_callees`,
  `get_call_chain`, `get_references`, `get_source`, `find_knowledge`, `find_case`, `find_doc`), Confluence, shared
  folders, internal GitHub.
- New features are already specified with [docforge](https://github.com/ThinkerYzu/docforge) (agent interview →
  SPEC → DESIGN → IMPLEMENTATION-GUIDE). Reports should become slides via
  [open-slide](https://github.com/open-slide/open-slide).

---

## Goals

1. **One Jira ticket → one traceable agent pipeline.** Ticket labels decide which agent runs next; results go back
   to Jira.
2. **A dedicated agent per kind of work:** bug analysis, model enablement, API/RPC feature spec, implementation,
   review preparation, review response, reports.
3. **Every agent runs by hand first.** Each one is a skill usable from Claude Code or Codex; an orchestrator
   schedules it only after it has earned trust.
4. **Knowledge accumulates.** Root causes, op rewrite recipes, and per-git build facts are recorded so the next
   agent does not start from zero.
5. **Humans gate the decisive points:** approving a spec, Gerrit Code-Review +2, sending a report.

## Non-Goals

1. Not every git in the manifest — only the 2–3 owned gits at first.
2. Agents **never** +2, submit, or abandon Gerrit changes, change the Jira workflow, or close other people's tickets.
3. No autonomous planning (autopilot's CTO team filing its own tickets) in the first versions.
4. No flashing, driver installation, or device-lab management; agents run only in a scratch directory on existing
   devices.
5. No custom dashboard; Jira boards and the dossier are enough at first.

---

## Requirements

### Functional

1. **Jira** — JQL search; read description, comments, attachments (logcat, bugreports, traces, dumps); add
   comments and labels. All Jira text in English.
2. **Workspace** — a synced tree; each task gets its own branch in the owned git (`repo start loop/<KEY>`).
3. **Agents** (details in DESIGN)
   - `triage` — classify, find duplicates, find the owning git, ask for missing logs
   - `bug-analyze` — root cause from logs, code, and device reproduction; no code changes
   - `model-enable` — find unsupported / fallback ops, choose a rewrite, prove accuracy and latency on device
   - `feature-spec` — docforge-style interview for new APIs and FastRPC calls; decompose into Jira sub-tasks
   - `repo-onboard` — learn an owned git's build/test gates from its Jenkinsfile and build files
   - `implement` — change code, pass the C++/Python gates, upload a WIP Gerrit change
   - `review-prep`, `review-respond` / `fixer` — reviewer notes; answer comments, fix Verified -1, rebase
   - `report` — open-slide deck from the dossier, Jira, and git history
   - `reflect` — extract lessons into the knowledge repo after each run
4. **Dossier** — one folder per ticket holding every intermediate artifact; the hand-off interface between agents.
5. **Knowledge** — reuse CodeAtlas, Confluence, and shared folders as they are; loop adds only a distilled
   knowledge repo (op recipes, bug lessons, per-git overviews) on internal git.
6. **Devices** — adb (Android) and ssh (Windows on Snapdragon); one lock per device, scratch-only writes,
   evidence for every run.
7. **Claude Code and Codex** — skills use the Agent Skills `SKILL.md` format, which both load.

### Non-Functional

1. **Safety** — writes only in owned gits; uploads only to Gerrit; no credentials in prompts or files.
2. **Traceability** — every step leaves a Jira comment and dossier files a human can audit.
3. **Resumable** — stopping at any point and restarting continues from Jira labels and the dossier.
4. **Bounded cost** — timeouts, retry caps, and a parallelism limit.

---

## Constraints

- Builds are slow and multi-target (host, Android aarch64, Windows ARM64, Hexagon). Parallelism is bounded by the
  build machine; incremental builds of one target are the default gate.
- The Jira workflow is company-managed, so agent state lives in **labels**, not new statuses.
- Per-git build and test commands are not documented yet; `repo-onboard` derives them from Jenkins, and the
  engineer reviews them.
- This repo stays generic and temporarily lives on external GitHub; company data (dossiers, device lists,
  knowledge content) is git-ignored or kept in internal repos. The repo moves to internal GitHub later.

---

## Success Criteria

1. **bug-analyze:** on 3–5 solved historical bugs across layers, the agent's root cause matches the real fix, or the
   engineer rates it "usable as-is or with small edits", in ≥ 50% of cases.
2. **model-enable:** on one past enablement ticket, the op-gap analysis and rewrite plan match or beat what the team
   did; the rewrite passes unit tests and the on-device accuracy threshold.
3. **implement (Phase 2):** a simple analyzed bug goes from Jira to a WIP Gerrit change that passes the owned
   git's gates; the engineer only reviews.
4. **Full flow (Phase 4):** a new feature goes from interview to slides with the human only answering questions,
   reviewing, and approving.

---

## Open Questions

See [HANDOFF.md → Open Questions](../HANDOFF.md#open-questions).
