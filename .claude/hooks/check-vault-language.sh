#!/bin/bash
# AUDIENCE: public
# Block writes that put non-ASCII Cyrillic content into vault/ files.
# Enforces CORE.md § 1: "Documentation & code comments: English only."
# This is the safety net that survives prompt-instruction failure on any platform.
#
# Hook event: PreToolUse / BeforeTool on file-write tools.
# Compatible with both Claude Code (Edit, Write) and Gemini CLI (write_file, replace).
# Reads JSON on stdin from the harness.
#
# Bypass for legitimate non-English vault notes (e.g. multilingual personal notes):
#   export DMRZL_ALLOW_VAULT_LANG=1   # disables the check entirely
# Or scope a single edit:
#   DMRZL_ALLOW_VAULT_LANG=1 ./your-command
#
# Exit codes:
#   0 — write allowed
#   2 — write blocked (Cyrillic in vault path)

[ "${DMRZL_ALLOW_VAULT_LANG:-0}" = "1" ] && exit 0

INPUT=$(cat)
[ -z "$INPUT" ] && exit 0

PARSED=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', d.get('params', d))
    # Try every field name a write-style tool might use across platforms
    fpath = (ti.get('file_path') or ti.get('path')
             or ti.get('absolute_path') or ti.get('filepath') or '')
    # Content fields: Claude Code Write uses 'content', Edit uses 'new_string';
    # Gemini write_file uses 'content', replace uses 'new_string'.
    content = (ti.get('content') or ti.get('new_string')
               or ti.get('text') or ti.get('body') or '')
    print(fpath + '\t' + content)
except Exception:
    print('\t')
" 2>/dev/null)

FILE_PATH=$(echo "$PARSED" | cut -f1)
CONTENT=$(echo "$PARSED" | cut -f2-)

# Only enforce on vault/ paths. Non-vault writes pass through untouched.
case "$FILE_PATH" in
  */vault/*|vault/*) ;;
  *) exit 0 ;;
esac

# Detect Cyrillic Unicode block (U+0400–U+04FF) anywhere in content.
# Python check is safer than grep for Unicode ranges across BSD/GNU.
if echo "$CONTENT" | python3 -c "
import sys, re
text = sys.stdin.read()
if re.search(r'[Ѐ-ӿ]', text):
    sys.exit(1)
" 2>/dev/null; then
    exit 0  # no Cyrillic, allow
fi

# Block. Send actionable error on stderr (Claude Code + Gemini both surface this).
cat >&2 <<EOF
BLOCKED: Cyrillic content detected in vault file: $FILE_PATH

Vault documentation must be English only (CORE.md § 1).
User-facing chat may use the configured language; vault files always English.

If this is a legitimate non-English personal note, bypass with:
  DMRZL_ALLOW_VAULT_LANG=1 <your command>
Or set the env var globally in your shell to disable this check.
EOF
exit 2
