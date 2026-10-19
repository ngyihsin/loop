#!/usr/bin/env bash
# Symlink loop skills into Claude Code and Codex user skill folders.
# Usage: scripts/install-skills.sh [claude] [codex]   (default: both)
set -euo pipefail
LOOP_HOME="$(cd "$(dirname "$0")/.." && pwd)"
targets=("$@"); [ ${#targets[@]} -eq 0 ] && targets=(claude codex)
for t in "${targets[@]}"; do
  case "$t" in
    claude) dest="$HOME/.claude/skills" ;;
    codex)  dest="${CODEX_HOME:-$HOME/.codex}/skills" ;;
    *) echo "unknown target: $t" >&2; exit 1 ;;
  esac
  mkdir -p "$dest"
  for skill in "$LOOP_HOME"/skills/*/; do
    name="$(basename "$skill")"
    ln -sfn "${skill%/}" "$dest/$name"
    echo "$t: $dest/$name -> ${skill%/}"
  done
done
echo "Set LOOP_HOME=$LOOP_HOME (and LOOP_KNOWLEDGE, LOOP_OWNED, JIRA_*) in your shell profile."
