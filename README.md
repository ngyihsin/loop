# loop

**狀態:** Phase 0 — Spec / Design(尚未寫程式)

把軟體開發流程(解 bug、開發新功能、準備 code review、準備報告)從「工程師做」逐步轉成「agent 做、工程師審」。
概念來自 [autopilot](https://github.com/pavlov-net/autopilot)(Linear + GitHub 的自動開發迴圈),但改成適用於:

- **Bug tracking:** Jira
- **Source 管理:** Android `repo` manifest(多 git),只聚焦自己負責的 2–3 個 git
- **Review:** Gerrit(待確認,見 [HANDOFF](HANDOFF.md) 的 Open Questions)

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
