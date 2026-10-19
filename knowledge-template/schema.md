# Schema

- Every page starts with YAML frontmatter:
  ```yaml
  ---
  type: op | lesson | repo | concept
  title: ...
  tags: [htp, v75, executorch, ...]
  sources: [NPU-123, https://confluence/..., path/to/file.cc@<rev>]
  updated: YYYY-MM-DD
  reviewed_by: <human or "unreviewed">
  ---
  ```
- Cite every fact in `sources`. Unreviewed agent pages are allowed but marked `reviewed_by: unreviewed`.
- Link related pages with `[[page-name]]`.
- One topic per page. Update an existing page instead of creating a near-duplicate.
- After adding or renaming a page, update `index.md` and append one line to `log.md`.
