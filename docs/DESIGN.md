# Design: loop

**Created:** 2026-10-19
**Status:** Draft v2

**Project Docs:** [README](../README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) *(you are here)* | [references](references.md) | [HANDOFF](../HANDOFF.md)

---

## Design Philosophy

1. **Jira 是唯一的真相來源**(來自 autopilot)。Agent 不做沒有票的工作;所有狀態寫回 Jira。
2. **Prompt / skill 才是產品**(來自 autopilot)。Orchestrator 是薄薄的 plumbing;品質取決於每個 skill。
3. **Skill-first,自動化後到**。每個 agent 都是一個 Claude Code skill(`.claude/skills/<name>/SKILL.md`),可以先手動 `/bug-analyze PROJ-123` 跑,信任建立後才交給 orchestrator 排程。這樣 Phase 0 就有價值,不用等整套系統完成。
4. **Dossier 是 agent 之間唯一的交接介面**(來自 docforge 的 HANDOFF 概念)。下一個 agent 只需讀 dossier + Jira,不依賴前一個 agent 的對話紀錄。
5. **證據優先**(來自 pstack bug-fix playbook)。每一行修改都要能追溯到 log / 重現 / 測試的證據;不做「可能有幫助」的修改。
6. **人在關鍵點把關**:需求核准、Gerrit +2、報告送出。Agent 遇到不確定就 `agent:blocked` 並說明缺什麼(autopilot 的 "When in doubt, block")。

---

## Architecture Overview

```
                ┌──────────────────────── Jira (source of truth) ────────────────────────┐
                │  Bug / Story / Task   +  labels: agent:* , 狀態, 留言, 附件(log)         │
                └───────▲──────────────────────┬──────────────────────────────▲──────────┘
                        │ 留言 / label / 狀態    │ JQL poll                       │
                        │                      ▼                                │
                ┌───────┴──────────────── Orchestrator (thin) ──────────────────┴───────┐
                │  依 (issue type, label, 狀態) 查路由表 → 選 skill → 開 workspace slot   │
                │  timeout / 重試上限 / 平行數 / circuit breaker                        │
                └───┬──────────┬──────────┬───────────┬───────────┬───────────┬────────┘
                    ▼          ▼          ▼           ▼           ▼           ▼
                 triage    bug-analyze  implement   feature-   review-     report
                                        model-     spec       prep/respond (open-slide)
                                        enable
                    │          │          │           │           │           │
                    └──────────┴────┬─────┴───────────┴───────────┴───────────┘
                                    ▼
                    ┌──────────── dossier/<JIRA-KEY>/ ────────────┐      ┌──── Knowledge ────┐
                    │ analysis.md  SPEC.md  DESIGN.md  HANDOFF.md │ ◀──▶ │ wiki/ (每個 git)    │
                    │ review-notes.md  deck/  runs/*.log         │      │ lessons/ (root cause)│
                    └─────────────────────────────────────────────┘      └─────────────────────┘
                                    │
                                    ▼
             Android tree (repo sync)  ──  只在負責的 2–3 個 git 開 branch  ──▶  Gerrit (repo upload)
                                                                              │ Verified (CI) / Code-Review
                                                                              ▼
                                                                         Monitor 迴圈
```

---

## Agent 類型與路由

每個 agent = 一個 skill + 明確的輸入 / 輸出 / 權限。

| Agent (skill) | 觸發條件(預設) | 讀 | 寫 | 能改 code? | 完成後 |
|---|---|---|---|---|---|
| `triage` | 新票,沒有 `agent:*` label | Jira、wiki | Jira 留言、label | 否 | `agent:analyze` 或 `agent:needs-info` |
| `bug-analyze` | `agent:analyze` | 附件 log、tree(全部可讀)、wiki、lessons | `analysis.md`、Jira 留言 | 否 | `agent:fix-ready`(人可審) |
| `feature-spec` | Story + `agent:spec` | Jira、Confluence、CodeAtlas | `SPEC.md` `DESIGN.md` `IMPLEMENTATION-GUIDE.md`、Jira sub-task | 否 | **人核准**後 sub-task 進 `agent:ready` |
| `model-enable` | Story + `agent:model` | 模型、converter / partitioner log、`ops/` 知識、SDK op 表 | `SPEC.md`、`op-gap.md`,再交給 `implement` | 階段二才改 | 實機精度 + 效能證據 |
| `implement` (= bug-fix) | `agent:ready` / `agent:fix-ready` | dossier、tree | 負責 git 的 branch、Gerrit change | **是** | `agent:in-review` |
| `review-prep` | change 剛上傳 | diff、dossier | `review-notes.md`、Gerrit change 說明 | 否 | 通知 reviewer |
| `review-respond` / `fixer` | Gerrit 有新 comment / Verified -1 / merge conflict | Gerrit、CI log | 同一個 change 的新 patchset | **是** | 維持 `agent:in-review` 或 `agent:blocked` |
| `report` | 人手動觸發,或 Epic 完成 | dossier、Jira、git log | `deck/`(open-slide) | 否 | 人 review 投影片 |
| `reflect` | 每次 run 結束(成功或失敗) | run log、dossier | `knowledge/lessons/`、wiki 更新 | 否 | — |

### 為什麼 bug-analyze 和 implement 分開?

Android bug 最難的是**找 root cause**,不是改 code。分開之後:
- Phase 1 只開 `bug-analyze`(唯讀),就能先驗證 agent 判斷的品質,風險為零。
- 人可以在分析和修改之間插一個審查點(`agent:fix-ready` 需要人加,或設定成自動)。
- 分析失敗的模式會被 `reflect` 收集,改進 prompt。

---

## Jira 狀態機(label 驅動)

為了不需要 Jira admin 改 workflow,用 label 表示 agent 狀態,原本的 Jira status 只做粗略同步(例如 In Progress / In Review / Resolved,名稱在設定檔對應)。

```
(新票) ──triage──▶ agent:needs-info ──(人補資料, 移除 label)──▶ (重新 triage)
   │
   └──▶ agent:analyze ──bug-analyze──▶ agent:fix-ready ──implement──▶ agent:in-review ──(Gerrit merged)──▶ Resolved
                                │                         │                  │
                                └────────────┬────────────┴──────────────────┘
                                             ▼
                                       agent:blocked(留言說明缺什麼;人處理後換回上一個 label)

Story ──agent:spec──▶ feature-spec(多輪,人回答問題) ──人核准──▶ 拆 sub-task,每個 agent:ready ──▶ implement ...
```

規則:
- 一張票同時只會有一個 `agent:*` label(orchestrator 負責互斥,換 label 是原子操作)。
- 每個 agent 開始時加 `agent:running`,結束時移除;crash 後由 orchestrator 依 timeout 清理(idempotent)。
- 只處理 `assignee = 我` 或特定 component 的票(由 JQL 設定),避免碰到別人的票。

---

## Workspace(Android repo)

autopilot 每個 issue 一個 git worktree;Android tree 太大不能每張票 sync 一份。設計:

```
~/loop/
  mirror/                 # repo init --mirror(可選,省頻寬/硬碟)
  slots/
    slot-1/               # 完整 repo sync 的 tree + out/(增量 build 用)
    slot-2/               # 平行數 = slot 數;起始建議 1
  dossier/<JIRA-KEY>/
  knowledge/
```

- 每個 slot 是一份完整 tree;任務開始時在**負責的 git** 執行 `repo start loop/<JIRA-KEY> <project>`,其他 git 保持 manifest revision。
- 任務結束後 `repo abandon` 回乾淨狀態,slot 歸還;`out/` 保留以加速下一次增量 build。
- 寫入權限:sandbox 只允許寫 `slots/<n>/<負責的 git 路徑>`、`out/`、`dossier/<KEY>/`。其他路徑唯讀。
- Build / test 指令寫在每個 git 的設定(例如 `m <module>`、`atest <test>`),不讓 agent 自己猜整棵 build。
- 唯讀分析(triage、bug-analyze)不需要獨占 slot,可共用一份唯讀 tree,平行度較高。

---

## Gerrit + Jenkins 介接

| autopilot (GitHub) | loop (Gerrit) |
|---|---|
| 開 PR | `repo upload --cbr -t`(topic = JIRA-KEY),初期加 `--wip` 或 private |
| 跨 repo 改動 | 同一個 topic 串多個 change |
| CI checks | Jenkins 投的 Verified label;失敗時從 Jenkins console log 讀錯誤 |
| auto-merge | **不做**;人 +2 + submit |
| fixer 用 `git merge`(不 force push) | Gerrit 用新 patchset(amend + 保留 Change-Id),rebase 用 Gerrit 的 rebase |
| review comments | Gerrit REST API 讀 unresolved comments,回覆後標 resolved |

Commit message 規範:第一行 `[JIRA-KEY] <summary>`,含 `Bug: JIRA-KEY`、`Test:` 欄位(Android 慣例)、`Change-Id`。

---

## Dossier(每張票的交接資料夾)

```
dossier/PROJ-123/
  HANDOFF.md          # 目前狀態、下一步、誰(哪個 agent)最後動過 — 每個 agent 結束都要更新
  analysis.md         # bug-analyze 輸出:現象、證據(log 行號)、root cause、建議修法、信心
  SPEC.md DESIGN.md IMPLEMENTATION-GUIDE.md   # feature-spec / model-enable 輸出(docforge 格式)
  review-notes.md     # review-prep 輸出:改了什麼、為什麼、怎麼驗證、風險
  attachments/        # 從 Jira 下載的 log / bugreport(不進 git)
  deck/               # report 輸出(open-slide)
  runs/               # 每次 agent run 的摘要(給 reflect 用)
```

Dossier 預設放在工作站本機 `$LOOP_DOSSIER`(git-ignore,不外流);需要分享時把摘要貼回 Jira,值得保留的經驗進內部知識 repo。

---

## 知識來源

不重建公司已有的東西,loop 只補「萃取後的經驗」這一層:

| 來源 | 用途 | Agent 怎麼用 |
|---|---|---|
| **CodeAtlas MCP** | code graph、caller/callee、semantic search(取代 TencentDB 的 CodeGraph) | 追 error 字串 → 產生它的 code;改動前做影響分析 |
| **Confluence** | 設計文件、SDK release note、op 支援表 | Atlassian MCP 或 REST(同一組 token);引用頁面 URL |
| **共享資料夾** | 模型、測試資料、舊報告 | 唯讀掛載,引用路徑 |
| **內部 GitHub** | upstream / 其他團隊的 code、知識 repo 本身 | GitHub MCP / git |
| **知識 repo**(新,內部 git) | `ops/` op 改寫配方、`lessons/` bug 經驗、`repos/` 各 git overview | 每個 skill 開始前 grep;結束時提議新增頁面 |

知識 repo 採 Karpathy LLM Wiki / llm_wiki 的格式(`purpose.md`、`schema.md`、`index.md`、`log.md`、frontmatter `sources:`),
範本在 `knowledge-template/`。**公司資料只放內部 git,不放在這個 loop repo。**

TencentDB Memory Hub 先不導入:CodeAtlas 已經涵蓋 CodeGraph,剩下的「經驗萃取」用檔案型知識 repo 就夠;等多人共用、需要權限控管時再評估。

## 實機存取(device skill)

- 裝置清單:`devices.yml`(SoC、Hexagon arch、adb serial 或 ssh host、scratch 目錄)。
- 每台裝置用 `flock` 上鎖,同一時間只有一個 agent 操作。
- 允許:在 `scratch/<KEY>/` push / 執行 / 讀 log;需要人同意:reboot、remount、改 `/vendor` `/dsp` 下的 library;禁止:刷機、wipe。
- 每次執行留下 `device-runs/<時間>-<slug>/`(指令、fingerprint、stdout、logcat、dmesg、結論),可重跑。

## Orchestrator

參考 autopilot 的迴圈結構,但先做最小版:

```
loop:
  for route in config.routes:                       # 依優先順序
    issues = jira.search(route.jql)                 # 例: labels = agent:analyze AND assignee = currentUser()
    for issue in issues not running:
      if route.needs_slot and no free slot: continue
      run_skill(route.skill, issue, slot)           # Claude Agent SDK / `claude -p`,帶 timeout
  monitor_gerrit()                                  # in-review 的 change:Verified -1 / 新 comment / conflict → fixer
  sleep(poll_interval)
```

- 實作語言:Python(stdlib 優先,工作站 / build server 不需另裝環境;`tools/jira.py` 已是 Python)。
- Agent 執行器可切換:`claude -p` 或 `codex exec`,skill 是同一份。
- 從 autopilot 借:circuit breaker、retry、timeout + abort、activity log、prompt template 渲染。

---

## 分階段 Roadmap

| Phase | 內容 | 自動化程度 | 價值 |
|---|---|---|---|
| **0** | `jira.py`、`bug-analyze` / `device` / `model-enable` / `feature-spec` skill、知識 repo 範本;**全部手動執行**(進行中) | 手動 | 立刻能用,驗證 prompt 品質 |
| **1** | Jira 讀取 + `triage` + `bug-analyze` 自動跑(唯讀,只留言) | 唯讀自動 | 零風險驗證判斷力 |
| **2** | `implement`:改 code、build、test、`repo upload` WIP change | 寫入自動 | 第一個「票 → change」 |
| **3** | Gerrit monitor:Verified -1 修正、review comment 回應、rebase | 寫入自動 | 減少 review 往返 |
| **4** | `feature-spec` 串接 Jira sub-task、`report` 產投影片、`review-prep` | 半自動(人回答問題) | 新功能全流程 |
| **5** | `reflect` 定期改進 prompt、(可選)planning 主動開票、Memory Hub | 自我改進 | 長期累積 |
