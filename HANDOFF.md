# Handoff: loop

**Started:** 2026-10-19

**Project Docs:** [README](README.md) | [SPEC](docs/SPEC.md) | [DESIGN](docs/DESIGN.md) | [references](docs/references.md) | HANDOFF *(you are here)*

---

## Current Status

**Phase:** Phase 0 — Spec drafted,等待 Open Questions 的回答
**Progress:** 讀完 6 個參考專案,完成 SPEC / DESIGN 草稿、設定檔草稿
**Next Milestone:** Spec finalized → 開始 Phase 0(knowledge wiki + 手動 skill)
**Blockers:** 下面的 Open Questions

> - ✅ 參考專案分析
> - ✅ Spec drafted
> - ⬜ Spec finalized(Open Questions 解決)
> - ⬜ Phase 0:knowledge wiki + `bug-analyze` / `spec-interview` / `report` skill(手動)
> - ⬜ Phase 1:Jira 介接 + 自動 triage / analyze(唯讀)
> - ⬜ Phase 2:implement → Gerrit WIP change
> - ⬜ Phase 3:Gerrit monitor(fixer / review 回應)
> - ⬜ Phase 4:spec → sub-task、report、review-prep 串接
> - ⬜ Phase 5:reflect、Memory Hub

---

## Open Questions

這些答案會直接改變設計,依重要性排序:

### 環境

1. **Code review 是 Gerrit 嗎?**(`repo upload`)還是 GitHub / GitLab / 其他?CI(Verified)是 Jenkins 還是別的?
2. **Jira 是 Cloud 還是 Server/Data Center?** 能用 API token / PAT 嗎?你有權限加 label、轉狀態嗎?能不能請 admin 加新狀態(或就用 label)?
3. **Agent 在哪裡跑?** 你的工作站 / 公司 build server / 雲端?能連到 Claude API 嗎(或要走公司 proxy / Bedrock / Vertex)?公司對「code 送到 LLM」有沒有限制?
4. **Build 規模:** 你負責的 2–3 個 git 是哪一類(app、framework service、HAL、kernel、vendor)?單一 module 增量 build 大約多久?有沒有 host 端可以跑的 unit test(Robolectric / host gtest),還是一定要實機?

### 流程

5. **Bug 的「重現」主要靠什麼?** Jira 附件的 logcat / bugreport / ANR / tombstone?還是需要接實機?(決定 `bug-analyze` 的能力邊界)
6. **你希望第一個上線的是哪一種?** 我建議先做 `bug-analyze`(唯讀、零風險、最快看出 agent 判斷力),但如果你最痛的是別的(例如 review 準備或報告),可以換順序。
7. **Dossier 存哪?** (a) 這個 `loop` repo 裡、(b) 另一個私人 git、(c) 只放在 Jira 附件/留言。公司資料能不能放 GitHub?
8. **Orchestrator 語言:** TypeScript(Bun,可直接參考 autopilot)還是 Python?團隊既有工具偏哪一種?

### 範圍

9. **知識庫:** Phase 0 用檔案型 markdown wiki 可以嗎?還是你已經想直接上 TencentDB Memory Hub(需要部署 + LLM 端點)?
10. **報告投影片:** 有公司模板嗎(open-slide 可以做成 theme)?報告對象通常是誰(主管 / 跨部門 / 客戶),要 PPTX 嗎?
11. 現有的 **docforge 流程有沒有你改過的地方**,或你覺得它不夠好的地方?

---

## Next Actions

1. 回答上面的 Open Questions → 更新 SPEC / DESIGN。
2. 選定第一個 skill(預設 `bug-analyze`),寫進 `.claude/skills/`,拿 3–5 張已解決的歷史 bug 當評測(看 agent 找到的 root cause 跟實際修法是否一致)。
3. 為負責的 git 各寫一份 `knowledge/repos/<git>/overview.md`(可讓 agent 先產草稿,你再修)。

## Session Logs

- **Session 1(2026-10-19):** 閱讀 autopilot、pstack、docforge、llm_wiki、TencentDB Agent Memory、open-slide;起草 SPEC / DESIGN / references / 設定檔。
