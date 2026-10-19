# loop

**Status:** Phase 0 — the first skills and the Jira tool are usable by hand

Move software-development work (fixing bugs, enabling models, building features, preparing reviews, preparing
reports) from "the engineer does it" to "an agent does it, the engineer reviews". The idea comes from
[autopilot](https://github.com/pavlov-net/autopilot) (Linear + GitHub), adapted to:

- **Domain:** Qualcomm AI NPU frameworks — QNN / SNPE / Hexagon NN / ExecuTorch QNN backend / ORT QNN EP / FastRPC;
  mostly **C++ and Python**
- **Tracking:** Jira · **Review:** Gerrit · **CI:** Jenkins
- **Source:** Android `repo` manifest with many gits; agents write only in the 2–3 owned gits
- **Agents:** Codex (or Claude Code), developed on the **Windows x64** build host first, Linux x64 later
- **Build hosts:** Windows x64 (→ cross arm64 Windows) and Linux x64 (→ cross arm64 Linux)
- **Devices:** arm64 Linux / Android over adb or ssh, Windows on Snapdragon (arm64) over ssh
- **Knowledge:** CodeAtlas MCP, Confluence, shared folders, internal GitHub, plus an internal knowledge repo

## Quick start (Phase 0, manual mode)

Requires Python 3.11+, git, OpenSSH client (`ssh`, `scp`; built into Windows 10/11), and `adb` if you use adb devices.

Windows x64 (PowerShell):
```powershell
git clone <internal url> D:\loop; cd D:\loop
python scripts\install_skills.py                 # links skills into ~/.codex/skills and ~/.claude/skills
Copy-Item devices.example.toml devices.toml       # your test devices
Copy-Item build-hosts.example.toml build-hosts.toml
setx LOOP_HOME D:\loop; setx LOOP_KNOWLEDGE D:\npu-knowledge; setx LOOP_OWNED "<git path> <git path>"
setx JIRA_URL https://<your company jira>; setx JIRA_TOKEN <personal access token>
# open a new terminal so setx values apply, then:
python tools\jira.py show NPU-123                 # check the Jira connection
python -m unittest discover -s tools -p "test_*.py"
```

Linux x64 (later):
```bash
git clone <internal url> ~/loop && cd ~/loop && python3 scripts/install_skills.py
cp devices.example.toml devices.toml; cp build-hosts.example.toml build-hosts.toml   # set transport = "local" for this host
export LOOP_HOME=~/loop LOOP_KNOWLEDGE=~/npu-knowledge LOOP_OWNED="<git path> <git path>" JIRA_URL=... JIRA_TOKEN=...
```

Then, inside the synced tree, open Claude Code or Codex and run `/repo-onboard <git path>` once per owned git,
followed by `/bug-analyze NPU-123`, `/model-enable NPU-456`, or `/feature-spec NPU-789`.
Jira writes are dry-run until you add `--apply`.

**Codex setup:** `python scripts/install_skills.py codex` links the skills into `${CODEX_HOME:-~/.codex}/skills`
(check your Codex version's skills folder if they don't show up). Register the CodeAtlas MCP server in
`~/.codex/config.toml` with the same command or URL you use for Claude Code, for example:

```toml
[mcp_servers.codeatlas]
command = "<codeatlas MCP launch command>"
args = []
```

Then ask Codex to use a skill by name, e.g. "use the bug-analyze skill on NPU-123".
Developing loop itself: start from [AGENTS.md](AGENTS.md).

**Jira auth:** a company-hosted Jira URL means Jira Data Center/Server. Create a Personal Access Token under your
Jira profile → Personal Access Tokens and set `JIRA_TOKEN`. If your Jira has PATs disabled, also set
`JIRA_USER=<username>` to use Basic auth. (Jira Cloud — `*.atlassian.net` — uses `JIRA_USER=<email>` plus an API
token.)

## Skills

| Skill | What it does | Changes code? |
|---|---|---|
| [bug-analyze](skills/bug-analyze/SKILL.md) | collect logs, classify the layer, reproduce on device, trace with CodeAtlas, write an evidence-backed `analysis.md` | no |
| [device](skills/device/SKILL.md) | safe adb / ssh (Android, Windows on Snapdragon): lock, scratch-only, evidence per run | no |
| [model-enable](skills/model-enable/SKILL.md) | find unsupported ops → choose the cheapest viable rewrite → prove accuracy and latency | via implement |
| [feature-spec](skills/feature-spec/SKILL.md) | docforge-style interview → SPEC / DESIGN / steps → Jira sub-tasks (with an API / FastRPC checklist) | no |
| [repo-onboard](skills/repo-onboard/SKILL.md) | derive an owned git's build / test gates from Jenkins and build files into `repos/<git>/overview.md` | no |

Shared rules: [skills/CONVENTIONS.md](skills/CONVENTIONS.md) · C++/Python gates:
[skills/references/cpp-python-gates.md](skills/references/cpp-python-gates.md) · Build hosts:
[skills/references/build-hosts.md](skills/references/build-hosts.md) · Tool: [tools/jira.py](tools/jira.py)
· [tools/lock.py](tools/lock.py) · [tools/device.py](tools/device.py)
(`python -m unittest discover -s tools -p "test_*.py"`) · Knowledge repo template: [knowledge-template/](knowledge-template/)
(copy into an internal git, not into this repo).

## Docs

| Doc | Content |
|------|------|
| [docs/SPEC.md](docs/SPEC.md) | what, why, non-goals, success criteria |
| [docs/DESIGN.md](docs/DESIGN.md) | architecture, agents, Jira state machine, workspace, gates, knowledge, devices |
| [docs/references.md](docs/references.md) | what we borrow from the six reference projects |
| [loop.example.toml](loop.example.toml) | orchestrator config draft |
| [HANDOFF.md](HANDOFF.md) | status, open questions, next actions |

## One-line architecture

> **Jira is the source of truth; each ticket has a dossier folder that agents hand off through; each stage is a
> skill you can run by hand; the orchestrator is a thin layer that chains skills by Jira label.**
