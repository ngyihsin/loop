# loop

**狀態:** Phase 0 — 第一批 skill 與 Jira 工具可手動使用

把軟體開發流程(解 bug、開發新功能、準備 code review、準備報告)從「工程師做」逐步轉成「agent 做、工程師審」。
概念來自 [autopilot](https://github.com/pavlov-net/autopilot)(Linear + GitHub 的自動開發迴圈),但改成適用於:

- **領域:** Qualcomm AI NPU framework(QNN / SNPE / Hexagon NN / ExecuTorch QNN backend / ORT QNN EP / FastRPC)
- **Bug tracking:** Jira;**Review:** Gerrit;**CI:** Jenkins
- **Source 管理:** Android `repo` manifest(多 git),只聚焦自己負責的 2–3 個 git
- **Agent:** Claude Code 或 Codex,在工作站 / build server 上跑;實機透過 adb / ssh
- **知識:** CodeAtlas MCP、Confluence、共享資料夾、內部 GitHub + 一個內部知識 repo

## Quick start(Phase 0,手動模式)

```bash
git clone <this repo> ~/loop && cd ~/loop
scripts/install-skills.sh            # 把 skills/ 連結到 ~/.claude/skills 與 ~/.codex/skills
cp devices.example.yml devices.yml   # 填入測試機
export LOOP_HOME=~/loop LOOP_KNOWLEDGE=~/npu-knowledge LOOP_OWNED="<git path> <git path>"
export JIRA_URL=https://jira.example.com JIRA_TOKEN=...   # Jira Cloud 另設 JIRA_EMAIL
python3 tools/jira.py show NPU-123   # 確認 Jira 連線
```

接著在 Android tree 裡開 Claude Code 或 Codex:`/bug-analyze NPU-123`、`/model-enable NPU-456`、`/feature-spec NPU-789`。
所有 Jira 寫入預設 dry-run,確認後才加 `--apply`。

## Skills

| Skill | 做什麼 | 改 code? |
|---|---|---|
| [bug-analyze](skills/bug-analyze/SKILL.md) | 收集 log、分層判斷、實機重現、找 root cause,寫 `analysis.md` | 否 |
| [device](skills/device/SKILL.md) | adb / ssh 安全操作:上鎖、只寫 scratch、每次留證據 | 否 |
| [model-enable](skills/model-enable/SKILL.md) | 找不支援的 op → 選改寫方式 → 驗證精度與效能 | 交給 implement |
| [feature-spec](skills/feature-spec/SKILL.md) | docforge 式訪談 → SPEC / DESIGN / 實作步驟 → Jira sub-task(含 FastRPC API checklist) | 否 |

共同規則:[skills/CONVENTIONS.md](skills/CONVENTIONS.md)。工具:[tools/jira.py](tools/jira.py)(`python3 -m unittest tools/test_jira.py`)。
知識 repo 範本:[knowledge-template/](knowledge-template/)(複製到內部 git,不要放在這個 repo)。

## 文件

| 文件 | 內容 |
|------|------|
| [docs/SPEC.md](docs/SPEC.md) | 要做什麼、為什麼、不做什麼、成功標準 |
| [docs/DESIGN.md](docs/DESIGN.md) | 架構、各種 agent、Jira 狀態機、workspace、知識庫 |
| [docs/references.md](docs/references.md) | 6 個參考專案各借用什麼、不借用什麼 |
| [loop.example.yml](loop.example.yml) | 設定檔草稿(用來把設計具體化) |
| [HANDOFF.md](HANDOFF.md) | 目前狀態、待回答問題、下一步 |

## 一句話架構

> **Jira 是唯一的真相來源;每張票有一個「dossier」資料夾在 agent 之間交接;每個階段是一個可單獨手動執行的 skill;orchestrator 只是把 skill 依 Jira 狀態串起來的薄薄一層。**
