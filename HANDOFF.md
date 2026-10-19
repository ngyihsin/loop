# Handoff: loop

**Started:** 2026-10-19

**Project Docs:** [README](README.md) | [SPEC](docs/SPEC.md) | [DESIGN](docs/DESIGN.md) | [references](docs/references.md) | HANDOFF *(you are here)*

---

## Current Status

**Phase:** Phase 0 — skills usable by hand
**Progress:** environment confirmed (Gerrit + Jenkins; company-hosted Jira with token access; Claude Code / Codex on
workstation or build server; Android over adb and Windows on Snapdragon over ssh; CodeAtlas MCP tools; Jira text in
English). Docs are in English.
**Next Milestone:** evaluate `bug-analyze` and `model-enable` on real past tickets; then write `implement`.
**Blockers:** none for Phase 0; per-git build/test commands will come from `repo-onboard`.

> - ✅ Reference analysis
> - ✅ Spec / Design v3 (C++/Python, Windows on Snapdragon, CodeAtlas tools)
> - ✅ `tools/jira.py`: show / search / fetch (attachments) / comment / label; writes dry-run by default; DC/Cloud auto-detected from the URL
> - ✅ Skills: `bug-analyze`, `device` (Android + Windows), `model-enable`, `feature-spec` (+ API/FastRPC checklist), `repo-onboard`
> - ✅ C++/Python gates reference; build-hosts reference (Linux x64 / Windows x64, arm64 cross builds); knowledge repo template
> - ⬜ Evaluation: 3–5 solved bugs across layers + 1 past model-enablement ticket
> - ⬜ `repo-onboard` run on each owned git, overview reviewed by the engineer
> - ⬜ `implement` skill: owned git, `repo start loop/<KEY>`, gates, `repo upload --wip`, topic
> - ⬜ `report` (open-slide) and `review-prep` skills
> - ⬜ Phase 1 orchestrator: automatic `triage` / `bug-analyze` (read-only)
> - ⬜ Phase 3 Gerrit / Jenkins monitor

---

## Decisions

| Decision | Why |
|---|---|
| Build/test commands come from `repo-onboard` (Jenkinsfile first), reviewed by the engineer | the engineer cannot list them now; CI is the authoritative definition anyway |
| `jira.py` detects Cloud only for `*.atlassian.net`; default is Data Center with a Bearer PAT | Jira is on a company URL, which means Data Center/Server |
| Windows devices driven via OpenSSH + PowerShell, logs via `Get-WinEvent` and framework log files | no logcat/dmesg on Windows |
| All Jira text in English; all repo docs in English | team convention |
| Repo stays generic on external GitHub for now; company data git-ignored | moves to internal GitHub later |
| Fast gates on the x64 native build; arm64 builds cross-compiled on their host and executed only on devices | arm64 binaries cannot run on x64 build hosts |
| Agent runs on the Linux side; the Windows build host is driven over ssh, and the change travels as a hashed patch | one place for locks and dossiers; device artifacts stay traceable to an exact source state |

## Open Questions

1. **Evaluation tickets** — when ready, share 3–5 solved bugs (ideally different layers: converter, graph finalize,
   FastRPC, accuracy, performance, Windows-only) and one past model-enablement ticket.
2. **CodeAtlas in Codex** — is the CodeAtlas MCP server configured for Codex too, or only Claude Code? What do
   `find_case` results contain (Jira tickets? an internal case DB?) — this decides whether `triage` can rely on it
   for duplicate detection.
3. **Windows devices** — does the OpenSSH default shell on the laptops run PowerShell or cmd? Is there a standard
   place where the NPU frameworks write their log files on Windows?
4. **Windows build host source** — how does the Windows x64 build server get the source today: its own
   `repo sync`, plain `git` clones of the needed gits, or a network share from the Linux side? The patch-transfer
   design in `skills/references/build-hosts.md` assumes its own checkout at the same base revision.
5. **arm64 Linux devices** — are the adb-connected targets Android, or Qualcomm Linux boards (arm64 Linux)? This
   decides the log commands in the `device` skill (logcat vs. journalctl/syslog).
6. **Report audience** — who usually sees the slides (managers, cross-team, customers), and is there a company
   template to turn into an open-slide theme?

## Next Actions

0. Move to internal git: clone this branch (`git clone -b claude/agent-dev-workflow-jira-6rad9o <url> loop`), create
   the internal repo, `git remote add internal <internal url>` and `git push internal HEAD:main`. Continue
   development there with Codex (it reads `AGENTS.md`).
1. On the workstation: `scripts/install-skills.sh`, set the environment variables, `python3 tools/jira.py show <KEY>`.
2. Copy `knowledge-template/` into a new internal git repo; run `/repo-onboard <git>` for each owned git and correct
   the generated `overview.md`.
3. Run `/bug-analyze` and `/model-enable` on the evaluation tickets; report what was wrong or slow so the skills can
   be tuned.

## Session Logs

- **Session 1 (2026-10-19):** read the six reference projects; drafted SPEC / DESIGN / references / config.
- **Session 2 (2026-10-19):** folded in environment answers; added `tools/jira.py` with tests, four skills, the
  knowledge template, device inventory, install script.
- **Session 3 (2026-10-19):** C++/Python gates and `repo-onboard`; Windows on Snapdragon support in `device`;
  CodeAtlas tool names in all skills; Jira auth by URL (`JIRA_USER`); all docs translated to English.
- **Session 4 (2026-10-19):** build hosts — Linux x64 and Windows x64 with arm64 cross builds; `build-hosts.md`,
  `build-hosts.example.yml`; gates, repo-onboard, device provenance, and DESIGN updated.
- **Session 5 (2026-10-19):** prepared the hand-over to internal development with Codex: `AGENTS.md` (repo dev
  rules), `CLAUDE.md` pointer, Codex setup notes in README.
