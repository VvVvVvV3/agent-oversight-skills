#!/usr/bin/env bash
# check_map.sh - wrapper used by the Claude Code Stop and SubagentStop hooks. Nothing else
# calls it; CI runs verify_map.py directly.
#
# What it catches, and what it does not. The verifier compares the commit recorded in the
# map with HEAD, so this blocks a clean finish when committed code has drifted from the
# map. It does not block on uncommitted edits, which the check cannot see. When the
# verifier passes this script prints nothing, so the verifier's warning about uncommitted
# edits is not shown by the Stop hook; run verify_map.py directly or read the CI log.
#
# Behaviour:
#   no map in this repo            -> exit 0, silent. Unmapped repos are not punished.
#   stop_hook_active on stdin      -> exit 0. A Stop hook has already blocked this turn,
#                                     so stand down rather than nudging forever.
#   map is current                 -> exit 0
#   map has drifted or is broken   -> exit 2 with the verifier's report on stderr. Claude
#                                     Code keeps the agent working and hands it that text
#                                     as the reason it may not finish yet.
#
# Needs python3 or python on the PATH; if neither is found it says so on stderr and
# exits 0.
#
# Install:
#   cp assets/check_map.sh        .claude/scripts/check_map.sh
#   cp scripts/verify_map.py      .claude/scripts/verify_map.py
#   chmod +x .claude/scripts/check_map.sh

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
MAP="${SYSTEM_MAP:-$REPO_ROOT/docs/system-map/system-map.json}"

# Stop hooks receive their payload as JSON on stdin. If we are already inside a
# stop-hook continuation, stand down rather than blocking forever.
if [ ! -t 0 ]; then
  PAYLOAD="$(cat || true)"
  case "$PAYLOAD" in
    *'"stop_hook_active":true'*|*'"stop_hook_active": true'*) exit 0 ;;
  esac
fi

[ -f "$MAP" ] || exit 0

VERIFY="$(dirname "$0")/verify_map.py"
[ -f "$VERIFY" ] || VERIFY="$REPO_ROOT/scripts/verify_map.py"
[ -f "$VERIFY" ] || exit 0

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "system map check skipped: Python was not found (looked for python3 and python)." >&2
  exit 0
fi

OUT="$("$PY" "$VERIFY" "$MAP" --repo "$REPO_ROOT" 2>&1)"
STATUS=$?

if [ $STATUS -ne 0 ]; then
  {
    echo "The system map no longer describes this code, so this session is not finished."
    echo ""
    echo "$OUT"
    echo ""
    echo "The code is already committed, so update the map for it as a commit of its own:"
    echo "  1. Edit docs/system-map/system-map.json for the nodes listed above."
    echo "  2. Set \"commit\" to the short SHA of that code commit and \"generated\" to today."
    echo "  3. python3 scripts/render_map.py docs/system-map/system-map.json"
    echo "  4. python3 scripts/verify_map.py docs/system-map/system-map.json --repo ."
    echo "  5. Commit the map files on their own: git add docs/system-map && git commit docs/system-map"
    echo "Update the map incrementally. Do not regenerate it from scratch."
  } >&2
  exit 2
fi

exit 0
