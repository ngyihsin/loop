# Prompts

**Project Docs:** [README](../README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [references](references.md) | [PROMPTS](PROMPTS.md) *(you are here)* | [HANDOFF](../HANDOFF.md)

Copy-paste prompts for Codex (they work in Claude Code too). There are two places to open a session:

| Where | Purpose | What the agent reads first |
|---|---|---|
| the `loop` repo | develop loop itself | `AGENTS.md` (automatically), then `HANDOFF.md` |
| an owned git in the work tree | run a skill on a real Jira ticket | the skill's `SKILL.md` and `skills/CONVENTIONS.md` |

Replace `<KEY>` and `<git name>`. Prompts are in English to match the repo; Chinese works as well.

---

## 1. First session on Windows (in `loop`)

```
Read AGENTS.md and HANDOFF.md. This is the first session on the Windows x64 build host.
1. Check the Python version (needs 3.11+) and that git, ssh, scp, and adb are on PATH. Report what is missing.
2. Run the tool tests: python -m unittest discover -s tools -p "test_*.py". If any fail on Windows,
   find the root cause and fix it in the tool (not by weakening the test), then re-run until green.
3. Run python scripts\install_skills.py codex and confirm the skills appear in the Codex skills folder.
Do not commit anything that contains company hostnames, tokens, or ticket data.
Finish by updating HANDOFF.md (status + session log) and show me the diff before committing.
```

## 2. Setup (by hand, then a check)

Follow README → Quick start: copy `devices.example.toml` → `devices.toml` and `build-hosts.example.toml` →
`build-hosts.toml` with real values; `setx` `LOOP_HOME`, `JIRA_URL`, `JIRA_TOKEN`, `LOOP_OWNED`, `LOOP_KNOWLEDGE`;
register the CodeAtlas MCP server in `~/.codex/config.toml`. Then:

```
Check my loop setup without changing anything: run python %LOOP_HOME%\tools\jira.py show <KEY>,
python %LOOP_HOME%\tools\device.py list, and confirm the CodeAtlas MCP tools are available
(search_semantic, find_symbol, find_case). Report each as OK / failing with the error.
```

## 3. Running skills (in an owned git)

Onboard each owned git once:

```
Use the repo-onboard skill on this git. Write the overview to $env:LOOP_KNOWLEDGE\repos\<git name>\overview.md.
Only run build/test commands on this Windows x64 host; list the Linux-host commands as unverified.
```

Bug analysis — start with solved tickets so the result can be compared with the real fix:

```
Use the bug-analyze skill on <KEY>. Do not post anything to Jira; show me the proposed comment only.
```

Model enablement:

```
Use the model-enable skill on <KEY>. Stop after SPEC.md and op-gap.md and wait for my review before any code change.
```

New API / FastRPC feature:

```
Use the feature-spec skill on <KEY>. Ask me questions in small rounds, each with your recommended answer.
```

## 4. Developing loop (in `loop`)

Next skill to build:

```
Read AGENTS.md, HANDOFF.md, docs/DESIGN.md, and skills/CONVENTIONS.md.
Write the implement skill (skills/implement/SKILL.md): input = a ticket with analysis.md or an approved
IMPLEMENTATION-GUIDE step; change only LOOP_OWNED gits on branch loop/<KEY>; pass the gates from
repos/<git>/overview.md (skills/references/cpp-python-gates.md, build-hosts.md); upload to Gerrit as WIP with
topic <KEY>; never +2/submit. Follow the style of the existing skills, update README/DESIGN tables and HANDOFF.
Show me the diff before committing.
```

Tuning a skill after an evaluation run:

```
Here is the bug-analyze output for <KEY> and what the real fix was: <paste>.
Find where the skill led the agent wrong or slow, and propose a minimal change to skills/bug-analyze/SKILL.md.
```

## 5. End of every session

```
Update HANDOFF.md: status checklist, any decisions made, open questions, and a one-line session log.
```

## Habits

- One session, one focus (docforge).
- Ask for the diff before every commit and check it contains no company data.
- When a prompt here turns out to need changes, update this file in the same commit.
