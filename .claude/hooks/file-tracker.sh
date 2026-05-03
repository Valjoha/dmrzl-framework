#!/bin/bash
# AUDIENCE: public
# Unified file-tracker — PostToolUse / AfterTool on file-touching tools.
# Cross-platform: handles Claude Code names (Read/Edit/Write/mcp__obsidian__*)
# AND Gemini CLI names (read_file/write_file/replace) via single case statement.
#
# Replaces vault-access-tracker.sh, vault-write-tracker.sh, vault-tool-tracker.sh,
# code-tool-tracker.sh — single hook with namespace tagging instead of N hooks
# with path filters.
#
# Subagents inherit hooks: when a subagent fires Read/Edit/Write, this hook
# runs in the subagent's process. The session_id will differ from the parent
# but session-map resolves to the same session number via .current-session.
#
# Token-efficient: no stdout, path-only inspection, single line per event.
# Schema: {ts}\t[{namespace}]\tS{N}\t{op}\t{method}\t{filename}\t{folder}

INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
LOG_DIR="${SCRIPT_DIR}/../feedback-loops"
LOG_FILE="${LOG_DIR}/session-activity.log"
SESSION_FILE="${LOG_DIR}/.current-session"
SESSION_MAP="${LOG_DIR}/.session-map"
WORKSPACE="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd)"
VAULT_ROOT="${WORKSPACE}/vault"
CODE_ROOT="{{project_root}}/Assets"

[ -d "$LOG_DIR" ] || mkdir -p "$LOG_DIR"
[ -z "$INPUT" ] && exit 0

# Parse fields. Different tools place the path in different field names —
# Read/Edit/Write use file_path; Obsidian MCP uses filename + folder.
PARSED=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    sid = d.get('session_id', '')
    tool = d.get('tool_name', d.get('toolName', ''))
    # Claude Code uses 'tool_input', Gemini may use 'params' or top-level fields
    ti = d.get('tool_input', d.get('params', d))
    # Path: file_path (CC), absolute_path/path (Gemini), filename (Obsidian MCP)
    fpath = (ti.get('file_path') or ti.get('absolute_path')
             or ti.get('path') or '')
    fname = ti.get('filename', '')
    folder = ti.get('folder', '')
    print(sid + '\t' + tool + '\t' + fpath + '\t' + fname + '\t' + folder)
except:
    print('\t\t\t\t')
" 2>/dev/null)

session_id=$(echo "$PARSED" | cut -f1)
tool_name=$(echo "$PARSED" | cut -f2)
file_path=$(echo "$PARSED" | cut -f3)
mcp_filename=$(echo "$PARSED" | cut -f4)
mcp_folder=$(echo "$PARSED" | cut -f5)

# Method + op derive from tool_name. Cross-platform — handles Claude Code names
# AND Gemini CLI names side-by-side. Skip unknown tools.
case "$tool_name" in
  # --- Claude Code ---
  Read)                            op="R"; method="read" ;;
  Edit)                            op="W"; method="edit" ;;
  Write)                           op="W"; method="write" ;;
  mcp__obsidian__read-note)        op="R"; method="obsidian_read" ;;
  mcp__obsidian__edit-note)        op="W"; method="obsidian_edit" ;;
  mcp__obsidian__create-note)      op="W"; method="obsidian_create" ;;
  # --- Gemini CLI ---
  read_file)                       op="R"; method="gemini_read" ;;
  write_file)                      op="W"; method="gemini_write" ;;
  replace)                         op="W"; method="gemini_replace" ;;
  *) exit 0 ;;
esac

# Resolve absolute path. Standard tools provide it; Obsidian MCP gives
# vault-relative folder + filename, which we expand against VAULT_ROOT.
if [ -n "$file_path" ]; then
    abs_path="$file_path"
elif [ -n "$mcp_filename" ]; then
    if [ -n "$mcp_folder" ]; then
        abs_path="${VAULT_ROOT}/${mcp_folder}/${mcp_filename}"
    else
        abs_path="${VAULT_ROOT}/${mcp_filename}"
    fi
else
    exit 0
fi

# Namespace classification — fast, mutually exclusive, path-prefix only.
namespace="other"
if [[ "$abs_path" == "${VAULT_ROOT}/"* ]]; then
    namespace="vault"
    rel="${abs_path#${VAULT_ROOT}/}"
elif [[ "$abs_path" == "${CODE_ROOT}/"* ]]; then
    namespace="code"
    rel="Assets/${abs_path#${CODE_ROOT}/}"
elif [[ "$abs_path" == "${WORKSPACE}/.claude/scripts/"* ]] || [[ "$abs_path" == "${WORKSPACE}/.claude/hooks/"* ]]; then
    namespace="script"
    rel="${abs_path#${WORKSPACE}/}"
elif [[ "$abs_path" == "${WORKSPACE}/.claude/"*.json ]] || [[ "$abs_path" == "${WORKSPACE}/.claude/"*.env ]] || [[ "$abs_path" == "${WORKSPACE}/CLAUDE.md" ]]; then
    namespace="config"
    rel="${abs_path#${WORKSPACE}/}"
elif [[ "$abs_path" == "${HOME}/Projects/dmrzl-framework/"* ]] || [[ "$abs_path" == "${HOME}/Projects/dmrzl-skills/"* ]] || [[ "$abs_path" == "${HOME}/Projects/dmrzl-memory/"* ]]; then
    namespace="dist"
    rel="${abs_path#${HOME}/Projects/}"
else
    rel="$abs_path"
fi

# Skip noise files even outside namespace logic. .meta files are Unity-managed
# and never carry meaningful information; binaries are opaque.
case "$abs_path" in
  *.meta|*.png|*.jpg|*.tga|*.psd|*.fbx|*.obj|*.wav|*.mp3|*.ogg|*.dll|*.so|*.dylib) exit 0 ;;
esac

# Split rel → folder + filename for the log schema.
filename="${rel##*/}"
if [[ "$rel" == *"/"* ]]; then
    folder="${rel%/*}"
else
    folder=""
fi

# Resolve session number. Session-map cache makes this parallel-safe.
session="?"
if [ -n "$session_id" ] && [ -f "$SESSION_MAP" ]; then
  mapped=$(grep "^${session_id}	" "$SESSION_MAP" 2>/dev/null | head -1 | cut -f2)
  [ -n "$mapped" ] && session="$mapped"
fi
if [ "$session" = "?" ] && [ -n "$session_id" ]; then
  current=$(cat "$SESSION_FILE" 2>/dev/null || echo "?")
  if [ "$current" != "?" ]; then
    echo -e "${session_id}\t${current}\t$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$SESSION_MAP"
    session="$current"
  fi
fi
[ "$session" = "?" ] && session=$(cat "$SESSION_FILE" 2>/dev/null || echo "?")

echo -e "$(date -u +%Y-%m-%dT%H:%M:%SZ)\t[${namespace}]\tS${session}\t${op}\t${method}\t${filename}\t${folder}" >> "$LOG_FILE"

# Rotation policy — single across the log.
LINE_COUNT=$(wc -l < "$LOG_FILE" 2>/dev/null || echo 0)
if [ "$LINE_COUNT" -ge 1000 ]; then
  HIST_FILE="${LOG_DIR}/session-activity-historical.log"
  cat "$LOG_FILE" >> "$HIST_FILE"
  : > "$LOG_FILE"
fi
exit 0
