#!/bin/bash
# AUDIENCE: public
# Block direct edits to Unity .meta files
# Unity auto-generates these — manual edits cause GUID mismatches
# Input: JSON on stdin with tool_input.file_path

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

if echo "$FILE_PATH" | grep -q '\.meta'; then
  echo "BLOCKED: Never edit .meta files directly — Unity manages these automatically." >&2
  echo "If you need to change asset settings, use the Unity Editor or UnityMCP tools." >&2
  exit 2
fi

exit 0
