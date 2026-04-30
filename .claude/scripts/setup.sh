#!/usr/bin/env bash
# AUDIENCE: public
# DMRZL workspace setup — fills template placeholders with your values.
#
# Workflow:
#   ./setup.sh init       # interactive prompts → writes setup.config.env
#   ./setup.sh dry-run    # preview substitutions without writing
#   ./setup.sh apply      # apply substitutions: {{key}} → real value
#   ./setup.sh reset      # reverse: real value → {{key}} (before re-publish)
#
# Placeholders in shipped files use {{snake_case_lower}} format.
# Config keys in setup.config.env use UPPER_SNAKE_CASE matching the placeholder.

set -euo pipefail

# Run from repo root (script lives in .claude/scripts/, repo root is two up).
cd "$(dirname "$0")/../.."

CONFIG_FILE="setup.config.env"
EXAMPLE_FILE=".claude/scripts/setup.config.example.env"

# ── helpers ────────────────────────────────────────────────────────────────

die() { echo "ERROR: $*" >&2; exit 1; }

require_config() {
    [ -f "$CONFIG_FILE" ] || die "missing $CONFIG_FILE — run './setup.sh init' first"
}

list_keys() {
    grep -E "^[A-Z_]+=" "$CONFIG_FILE" | cut -d= -f1
}

placeholder_for() {
    # USER_HANDLE → {{user_handle}}
    echo "{{$(echo "$1" | tr '[:upper:]' '[:lower:]')}}"
}

walk_files() {
    # Files we sanitize: code, docs, configs. Skip binaries, build outputs, dotfiles
    # we don't manage, and the setup tooling itself.
    find . -type f \( -name '*.md' -o -name '*.sh' -o -name '*.py' -o -name '*.json' \
                     -o -name '*.yaml' -o -name '*.yml' -o -name '*.toml' \) \
        -not -path './.git/*' \
        -not -path './_build/*' \
        -not -path './node_modules/*' \
        -not -path './.smart-env/*' \
        -not -name 'setup.config.*' \
        -not -name 'setup.sh' \
        -not -path './.claude/scripts/setup.config.*' \
        -not -path './.claude/scripts/apply-config.*'
}

# ── commands ───────────────────────────────────────────────────────────────

smart_default() {
    # Override generic example defaults with values inferred from the
    # current environment, so consumers don't accidentally accept
    # placeholders like "/Users/you" or "your-handle".
    local key="$1"
    local fallback="$2"
    case "$key" in
        USER_HANDLE)    echo "${USER:-$(whoami 2>/dev/null)}" ;;
        HOME)           echo "$HOME" ;;
        WORKSPACE_ROOT) echo "$PWD" ;;
        WORKSPACE_DIR)  basename "$PWD" ;;
        *)              echo "$fallback" ;;
    esac
}

cmd_init() {
    [ -f "$EXAMPLE_FILE" ] || die "missing example: $EXAMPLE_FILE"
    if [ -f "$CONFIG_FILE" ]; then
        echo "Config exists at $CONFIG_FILE."
        read -r -p "Overwrite? [y/N] " ans
        [[ "$ans" =~ ^[Yy]$ ]] || exit 0
    fi

    cat <<'BANNER'
Interactive setup. Defaults are derived from your environment
(USER_HANDLE from `whoami`, paths from $HOME and $PWD).
Press Enter to accept; type a value to override.

BANNER

    : > "${CONFIG_FILE}.tmp"
    description=""
    section=""

    while IFS= read -r line; do
        if [[ "$line" =~ ^([A-Z_]+)=\"?([^\"]*)\"?$ ]]; then
            # Key prompt.
            key="${BASH_REMATCH[1]}"
            example="${BASH_REMATCH[2]}"
            default="$(smart_default "$key" "$example")"

            if [ -n "$section" ]; then
                printf '\n  ── %s ──\n\n' "$section"
                section=""
            fi
            if [ -n "$description" ]; then
                printf '%b' "$description"
            fi

            # Read from /dev/tty explicitly — outer loop has stdin bound
            # to $EXAMPLE_FILE, so a bare `read` would consume file lines.
            read -r -p "  ${key} [${default}]: " value < /dev/tty
            value="${value:-$default}"
            printf '%s="%s"\n' "$key" "$value" >> "${CONFIG_FILE}.tmp"
            description=""
        elif [[ -z "${line//[[:space:]]/}" ]]; then
            # Blank line — reset description buffer.
            description=""
            printf '%s\n' "$line" >> "${CONFIG_FILE}.tmp"
        elif [[ "$line" == *"──"* ]]; then
            # Section divider line: `# ── Identity ──...`. Extract title.
            section=$(printf '%s' "$line" | sed -e 's/^#[[:space:]]*//' \
                                                 -e 's/─//g' \
                                                 -e 's/^[[:space:]]*//' \
                                                 -e 's/[[:space:]]*$//')
            description=""
            printf '%s\n' "$line" >> "${CONFIG_FILE}.tmp"
        elif [[ "$line" =~ ^#[[:space:]](.+)$ ]]; then
            # Plain comment — accumulate as description.
            description+="    ${BASH_REMATCH[1]}"$'\n'
            printf '%s\n' "$line" >> "${CONFIG_FILE}.tmp"
        else
            printf '%s\n' "$line" >> "${CONFIG_FILE}.tmp"
        fi
    done < "$EXAMPLE_FILE"

    mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    echo
    echo "Wrote $CONFIG_FILE. Review it, then run: ./setup.sh dry-run"
}

cmd_substitute() {
    local mode="$1"
    require_config
    set -a; source "$CONFIG_FILE"; set +a

    local total=0
    local files_changed=0

    while IFS= read -r file; do
        local file_changed=0
        for key in $(list_keys); do
            local value
            value="$(eval echo "\$$key")"
            local ph
            ph="$(placeholder_for "$key")"

            case "$mode" in
                dry-run)
                    if grep -q -F "$ph" "$file" 2>/dev/null; then
                        local count="0"
                        count="$(grep -c -F "$ph" "$file" 2>/dev/null || echo 0)"
                        echo "  $file: $ph -> $value  (count: $count)"
                        total=$((total + count))
                        file_changed=1
                    fi
                    ;;
                apply)
                    if grep -q -F "$ph" "$file" 2>/dev/null; then
                        sed -i.bak "s|${ph}|${value}|g" "$file" && rm -f "${file}.bak"
                        file_changed=1
                    fi
                    ;;
                reset)
                    if [ -n "$value" ] && grep -q -F "$value" "$file" 2>/dev/null; then
                        sed -i.bak "s|${value}|${ph}|g" "$file" && rm -f "${file}.bak"
                        file_changed=1
                    fi
                    ;;
            esac
        done
        [ $file_changed -eq 1 ] && files_changed=$((files_changed + 1)) || true
    done < <(walk_files)

    case "$mode" in
        dry-run) echo; echo "Would replace $total placeholders across $files_changed files." ;;
        apply)
            if [ $files_changed -eq 0 ]; then
                echo "Applied substitutions to 0 files."
                echo
                echo "⚠ No {{placeholders}} found. Possible causes:"
                echo "   • This workspace was already applied with previous values."
                echo "     Run './setup.sh reset' first, then re-apply with the current config."
                echo "   • You're not in the workspace root (run setup.sh from the clone root)."
                echo "   • A 'git checkout -- .' to restore placeholders, then apply, also works."
            else
                echo "Applied substitutions to $files_changed files."
            fi
            ;;
        reset)   echo "Reset $files_changed files back to placeholders." ;;
    esac
}

case "${1:-}" in
    init)    cmd_init ;;
    dry-run) cmd_substitute dry-run ;;
    apply)   cmd_substitute apply ;;
    reset)   cmd_substitute reset ;;
    *)
        cat <<EOF
Usage: $0 {init|dry-run|apply|reset}

  init      Interactive prompts to fill setup.config.env.
  dry-run   Preview substitutions without writing.
  apply     Replace {{placeholders}} with your values.
  reset     Replace your values back with {{placeholders}} (before re-publish).
EOF
        exit 1
        ;;
esac
