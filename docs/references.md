# 參考專案:借什麼、不借什麼

**Project Docs:** [README](../README.md) | [SPEC](SPEC.md) | [DESIGN](DESIGN.md) | [references](references.md) *(you are here)* | [HANDOFF](../HANDOFF.md)

## autopilot — pavlov-net/autopilot(主骨架)

Linear + Claude Agent SDK 的全自動開發迴圈:Executor(Ready → PR)、Monitor(CI 失敗 / conflict / review → fixer)、Planning(CTO + PM + Scout… 自己開票)、Projects(project owner 拆票)、Reviewer(分析 agent run 記錄,開改進票)。

**借用**
- Issue tracker 狀態驅動一切;「prompt 才是產品,TypeScript 只是 plumbing」。
- Executor prompt 的階段:Understand → Plan → Implement → Validate(最多 3 次)→ Simplify → Commit/Push → 更新 tracker;"When in doubt, block"。
- Fixer 規則:只修失敗、不重構、不改測試讓它過、不 force push、只碰自己建立的 branch(`autopilot-*` 前綴 → 我們用 `loop/*`)。
- Reviewer agent 分析 run transcript 找失敗模式 → 對應我們的 `reflect`。
- 工程細節:平行 slot、timeout + AbortController、circuit breaker、retry、sandbox(bubblewrap)。

**不借 / 要改**
- Linear SDK → Jira REST / JQL;Linear 狀態 → Jira label(避免改 workflow)。
- GitHub PR / Actions / auto-merge → Gerrit change / Verified / 人工 submit。
- 每 issue 一個 git worktree → Android tree 用固定 slot + `repo start`。
- Planning(CTO 團隊自己開票)延後到 Phase 5;先消化既有的票。
- Dashboard 先不做。

## pstack — backnotprop/pstack(工程紀律 skill)

poteto(React core)的一組 Agent Skills:`poteto-mode` + 各種 playbook(bug-fix、feature、investigation、babysit、autopilot-full…)+ `principle-*` 原則 + `reflect` / `recall` / `tdd` / `unslop` 等。

**借用**
- **bug-fix playbook**:先重現 → 二分法排除假設 → 用 runtime 證據確認機制 → 再修;每一行都要追溯到證據;失敗的 repro 測試先於修正 commit。直接改寫成 `bug-analyze` / `implement` 的方法論(Android 版:「重現」= 從 log/bugreport 找到觸發條件,能寫 unit test 就寫)。
- **autopilot-full**:「寫 code 的 agent 不能自己判定通過」→ 驗證由另一個沒寫 code 的 agent 做(對應 `review-prep` 用獨立 agent)。
- `reflect`(多個 reviewer 角度 + synthesizer)、`show-me-your-work`(決策軌跡)→ 對應 dossier `runs/` 與 `reflect`。
- 原則:Laziness Protocol(最小 diff)、Fix Root Causes、Prove It Works。

**不借**:Cursor 專屬多模型分工、Graphite 堆疊 PR 流程。

## docforge — ThinkerYzu/docforge(新功能訪談)

`AGENT-warm-up.md` 為每次 session 入口;SPEC → DESIGN → IMPLEMENTATION-GUIDE → HANDOFF + session log;「Ask, don't tell」、「Discuss first, code later」。

**借用**
- 整個流程成為 `spec-interview` skill,輸出放在 `dossier/<KEY>/`。
- HANDOFF.md 的品質標準(「新成員讀完能不問問題就接手」)→ 每個 agent 結束時更新 dossier HANDOFF.md。
- 本 repo 的文件也用 docforge 結構。

**要改**:IMPLEMENTATION-GUIDE 的 phase/milestone 要能轉成 Jira sub-task(每個 sub-task 一個可獨立驗證的 change)。

## llm_wiki — nashsu/llm_wiki(知識庫模式)

Karpathy LLM Wiki 模式的桌面 app:raw sources(不可變)→ LLM 維護的 wiki → schema;Ingest / Query / Lint;`purpose.md`;兩步驟 ingest(先分析再生成);frontmatter `sources:` 可追溯;有 MCP server。

**借用**:檔案型 wiki 結構(`purpose.md`、`schema.md`、`index.md`、`log.md`、`[[wikilink]]`)、兩步驟 ingest、source 可追溯。Phase 0 先用純 markdown,不需要裝 app;之後若想要圖譜/搜尋 UI,可以直接拿 llm_wiki 開同一個資料夾(Obsidian 相容)。

## TencentDB Agent Memory(團隊記憶,後期選項)

Memory Hub:Chat Memory(L0→L3 分層萃取)、Skill library(有版本、可分享)、Wiki、CodeGraph(symbol / caller / 影響分析);Proxy 方式接 Claude Code(改 base URL)。

**借用(概念)**:「任何能讓下一個 agent 少走冤枉路的資訊都要存」;skill 有版本與驗證規則;CodeGraph 做修改前影響分析。

**延後**:需要部署三個服務 + LLM 端點,也要確認公司資安是否允許 proxy。先用檔案型 wiki,等團隊共享需求出現再評估。

## open-slide — open-slide/open-slide(報告)

給 agent 用的 React 投影片框架(1920×1080),內建 `create-slide`、`slide-authoring`、`apply-comments`、`create-theme` skill;可匯出 HTML / PDF / PPTX;瀏覽器內留 comment → `/apply-comments`。

**借用**:`report` agent 讀 dossier(SPEC / DESIGN / analysis / review-notes)+ Jira + git log,用 `create-slide` 產生 deck;公司模板做成一個 `theme`;人用 inspector 留 comment → agent 修改;匯出 PPTX 交付。
