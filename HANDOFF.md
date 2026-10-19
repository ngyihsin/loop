# Handoff: loop

**Started:** 2026-10-19

**Project Docs:** [README](README.md) | [SPEC](docs/SPEC.md) | [DESIGN](docs/DESIGN.md) | [references](docs/references.md) | HANDOFF *(you are here)*

---

## Current Status

**Phase:** Phase 0 — 第一批 skill 可手動試用
**Progress:** 環境已確認(Gerrit + Jenkins、Jira token、工作站 / build server 上跑 Claude Code / Codex、adb / ssh 實機、CodeAtlas + Confluence)。
完成 `tools/jira.py`(含測試)與 `bug-analyze`、`device`、`model-enable`、`feature-spec` 四個 skill,以及知識 repo 範本。
**Next Milestone:** 用真實歷史票評估 `bug-analyze` 與 `model-enable`,再寫 `implement` skill(Gerrit WIP upload)。
**Blockers:** 下面 Open Questions 的 1、5、6

> - ✅ 參考專案分析
> - ✅ Spec / Design v2(納入第一輪回答)
> - ✅ `tools/jira.py`:show / search / fetch(附件)/ comment / label,寫入預設 dry-run
> - ✅ Skills:`bug-analyze`、`device`、`model-enable`、`feature-spec`(+ API/FastRPC checklist)
> - ✅ 知識 repo 範本(ops / lessons / repos)
> - ⬜ 評估:3–5 張已解決的 bug + 1 個 model enablement 案例
> - ⬜ `implement` skill:owned git、`repo start loop/<KEY>`、build/test、`repo upload --wip`、topic
> - ⬜ `report` skill(open-slide)、`review-prep` skill
> - ⬜ Phase 1:orchestrator 自動跑 triage / bug-analyze(唯讀)
> - ⬜ Phase 3:Gerrit / Jenkins monitor(Verified -1 修正、review comment 回應)

---

## Open Questions

1. **你負責的 2–3 個 git 是哪幾個?** 請給 repo 路徑,以及各自的增量 build 指令、host 端 unit test 指令、實機測試指令。這些會寫進 `knowledge/repos/<git>/overview.md` 和 `LOOP_OWNED`。
2. **Jira 是 Cloud 還是 Data Center?** `jira.py` 兩種都支援,差在認證:Cloud 要設 `JIRA_EMAIL`,DC 用 PAT。
3. **CodeAtlas MCP 在 Codex 也能用嗎?** Confluence 是走 Atlassian MCP 還是 REST?skill 目前只寫「用 CodeAtlas」,如果你給我 tool 名稱,我可以寫得更精準。
4. **實機種類:** adb 的是手機平台,ssh 的是車用 / IoT Linux 平台嗎?主要的 SoC / Hexagon arch 有哪些?
5. **評估案例:** 請挑 3–5 張已解決的 bug(最好分屬不同層:converter、finalize、FastRPC、精度、效能)和 1 個做過的 model enablement 票。用 skill 跑一次,再和實際修法比對。
6. **這個 repo 在 GitHub(ngyihsin/loop)上。** 我把它設計成只放通用框架,公司資料(dossier、devices.yml、知識內容)都 git-ignore 或放內部 repo。這樣可以嗎?還是整個 loop 應該搬到內部 GitHub?
7. **Jira 留言語言:** 英文還是中文?

## Next Actions

1. 在工作站:`scripts/install-skills.sh`,設好環境變數,`python3 tools/jira.py show <KEY>` 確認連線。
2. 把 `knowledge-template/` 複製成內部 git repo,先讓 agent 為每個負責的 git 起草 `repos/<git>/overview.md`,你再修改。
3. 用 Open Question 5 的案例跑 `/bug-analyze`、`/model-enable`,把結果和缺點貼回來,我依此調整 skill。

## Session Logs

- **Session 1(2026-10-19):** 閱讀 6 個參考專案;起草 SPEC / DESIGN / references / 設定檔。
- **Session 2(2026-10-19):** 納入環境回答;新增 `tools/jira.py`(5 個測試通過)、4 個 skill、知識 repo 範本、裝置清單範本、安裝腳本;更新 SPEC / DESIGN。
