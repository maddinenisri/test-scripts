#!/usr/bin/env bash
# Generate one manual chat-LLM Markdown prompt per ODM rule file.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="${SOURCE:-${1:-}}"
OUT="${OUT:-${2:-$ROOT/out/rule-prompts}}"
MAX_SOURCE_CHARS="${MAX_SOURCE_CHARS:-20000}"

if [ -z "$SOURCE" ]; then
  echo "usage: SOURCE=/path/to/ruleproject/ClaimProcessing scripts/generate-rule-prompts.sh" >&2
  echo "   or: scripts/generate-rule-prompts.sh /path/to/ruleproject/ClaimProcessing [out-dir]" >&2
  exit 2
fi

PYTHON="${PYTHON:-python3}"
PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" -m odm.generators.rule_prompts "$SOURCE" \
  -o "$OUT" \
  --max-source-chars "$MAX_SOURCE_CHARS"
