# Spec: loop — Jira + Android repo 的 agent 開發流程

**Created:** 2026-10-19
**Status:** Draft v2(已納入第一輪回答)

**Project Docs:** [README](../README.md) | [SPEC](SPEC.md) *(you are here)* | [DESIGN](DESIGN.md) | [references](references.md) | [HANDOFF](../HANDOFF.md)

---

## Problem Statement

工程師的時間大量花在「流程型」工作:讀 Jira、看 log、找 root cause、改 code、跑 build、上傳 review、回 review comment、寫報告做投影片。
這些工作每一步都有固定模式,但目前全靠人工串接。

autopilot 證明了「issue tracker 狀態驅動 + Claude Code agent 在隔離 worktree 執行」這個模式可行,但它假設:

- Linear(我們用 Jira)
- 單一 GitHub repo + PR + GitHub Actions CI(我們是 Android `repo` 多 git,review 走 Gerrit,build 很重)
- 只有「實作 issue」一種工作(我們還要 bug 分析、需求訪談、review 準備、報告)

### Background

- 專案是 **Qualcomm AI 加速 NPU framework**:QNN / SNPE / Hexagon NN / ExecuTorch(QNN backend)/ ONNX Runtime(QNN EP),以及 host ↔ DSP 的 FastRPC。
- 整個 manifest 有大量 git,但我負責的只有 2–3 個;agent 只在這些 git 內**寫入**,其他 git 只**讀取**(看 caller / framework 行為)。
- 環境(已確認):review 用 **Gerrit**、CI 用 **Jenkins**、Jira 可用 API token 加 label;agent 在**自己的工作站 / build server** 跑,公司允許用 **Claude Code 與 Codex**。
- 重現 bug 需要透過 **adb 或 ssh 連到實機**。
- 知識來源已存在:**CodeAtlas MCP**(code graph、caller/callee、semantic search)、**Confluence**、共享資料夾、內部 GitHub。
- 新功能開發已經用 [docforge](https://github.com/ThinkerYzu/docforge) 的流程:agent 一步步訪談 → SPEC → DESIGN → IMPLEMENTATION-GUIDE。
- 報告想用 [open-slide](https://github.com/open-slide/open-slide) 產生投影片。

---

## Goals

1. **一張 Jira 票 → 一條可追蹤的 agent 流水線**:票的狀態 / label 決定下一個該跑哪個 agent,結果寫回 Jira。
2. **不同工作類型用不同 agent**:bug 分析、bug 修正、功能訪談、實作、review 準備、review 回應、報告,各自有專屬 prompt / skill。
3. **每個 agent 都能先手動跑**:先當 Claude Code skill 用,穩定後再交給 orchestrator 自動排程(漸進式自動化)。
4. **累積知識**:每次執行的 root cause、模組知識、踩過的坑,寫進知識庫,下一個 agent 不必從頭讀 code。
5. **人只在關鍵點把關**:需求確認、Gerrit Code-Review +2、送出報告。

## Non-Goals

1. 不處理整個 manifest 的所有 git(先只做自己的 2–3 個)。
2. Agent **永遠不** +2 / submit Gerrit change,不改 Jira workflow 定義,不關別人的票。
3. 第一版不做自動 planning(autopilot 的 CTO 團隊自己開票),先處理既有的票。
4. 不做自動刷機 / device lab 管理;agent 只在既有裝置的 scratch 目錄執行(見 `device` skill)。
5. 不自己做 UI dashboard(初期用 Jira board + log 就夠)。

---

## Requirements

### Functional

1. **Jira 介接** — 以 JQL 撈票、讀描述 / 留言 / 附件(logcat、bugreport、ANR trace)、留言、改 label、轉狀態。
2. **Workspace 管理** — 維護一份 `repo sync` 好的 tree;每個任務在負責的 git 開獨立 branch(`repo start` 或 `git worktree`),互不干擾。
3. **Agent 類型**(詳見 DESIGN)
   - Triage:分類、找重複、判斷是哪個 git、資訊不足就留言要 log
   - Bug Analyst:讀 log + code 找 root cause,寫分析報告(不改 code)
   - Bug Fixer / Executor:依分析或 spec 改 code、build、跑測試、上傳 Gerrit
   - Spec Interviewer(`feature-spec`):docforge 流程,用於新 API / 新 RPC call,產生 SPEC / DESIGN,並拆成 Jira sub-task
   - Model Enabler(`model-enable`):找出 HTP 不支援 / fallback 的 op,選擇改寫方式(builder 對應、拆成支援的 op、op package),並在實機驗證精度與效能
   - Review Prep:自我審查、產生給 reviewer 的說明
   - Review Responder / Fixer:處理 Gerrit comment、Verified -1、rebase 衝突
   - Reporter:從 dossier + Jira + commit 產生 open-slide 投影片
   - Reflector:執行後萃取經驗寫進知識庫
4. **Dossier** — 每張票一個資料夾,存所有中間產物,作為 agent 之間的交接介面。
5. **知識庫** — 不重建已有的東西:code 用 CodeAtlas MCP,文件用 Confluence / 共享資料夾;loop 只另外維護一個**萃取後的知識 repo**(op 改寫配方、bug lessons、各 git 的 overview),放在內部 git。
6. **實機存取** — 透過 adb / ssh,每台裝置一把鎖,只寫 scratch 目錄,每次執行留下證據。
7. **同時支援 Claude Code 與 Codex** — skill 採 Agent Skills(`SKILL.md`)格式,兩者都能載入。

### Non-Functional

1. **安全** — agent 只能寫負責的 git;不能 push 到 Gerrit 以外;credentials 不進 prompt。
2. **可追溯** — 每一步都在 Jira 留言 + dossier 有紀錄,人可以事後審查。
3. **可中斷** — 任何時候停掉,下一次能從 Jira 狀態 + dossier 繼續(idempotent)。
4. **成本可控** — 有 timeout、最大重試次數、平行數上限。

---

## Constraints

- Android build 很慢、很吃資源 → 平行度受限於 build 機器;要支援增量 build(`m <module>` / `mm`)。
- Jira 可能是公司管理的,不一定能改 workflow → 設計上用 **label** 驅動,不依賴新增狀態。
- 公司網路 / 資安規範可能限制 LLM 能看到的 code(見 Open Questions)。

---

## Success Criteria

1. Phase 1:對 10 張真實 bug 票,Bug Analyst 產出的 root cause 分析,工程師認為「可直接採用或只需小改」的比例 ≥ 50%。
2. Model enablement:對一個有不支援 op 的模型,`model-enable` 產出的 op-gap 分析與改寫方案,工程師認為可直接採用;改寫後通過 unit test 與實機精度門檻。
3. Phase 2:Executor 能把一張分析好的簡單 bug,從 Jira 帶到 Gerrit change(build 通過、unit test 通過),工程師只需要 review。
4. Phase 4:一個新功能從訪談到投影片,全程只有人的「回答問題 / review / 核准」動作。

---

## Open Questions

見 [HANDOFF.md → Open Questions](../HANDOFF.md#open-questions)。回答後更新本文件與 DESIGN。
