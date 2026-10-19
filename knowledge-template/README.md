# Knowledge repo template

Copy this folder into an **internal** git repo (company GitHub / Gerrit), not into this public-facing loop repo,
and point `LOOP_KNOWLEDGE` at the checkout. It follows the LLM-Wiki pattern (Karpathy / llm_wiki): raw sources
stay where they are (Confluence, shared folder, code via CodeAtlas); this repo holds only distilled, agent-written,
human-reviewed pages. It opens as an Obsidian vault or in llm_wiki.

| Path | Holds | Written by |
|---|---|---|
| `purpose.md` | why this exists, the questions it must answer | human |
| `schema.md` | page rules (frontmatter, links, citations) | human |
| `index.md` | catalog; agents read it first | agents, on every add |
| `log.md` | append-only change log | agents |
| `ops/<op>.md` | per-op HTP support notes and rewrite recipes | model-enable |
| `lessons/<KEY>.md` | error signature → root cause → fix → how to find it faster | bug-analyze / reflect |
| `repos/<git>/overview.md` | module map, entry points, build/test commands, pitfalls | human + agents |
