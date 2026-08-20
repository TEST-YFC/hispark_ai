#!/bin/bash
set -eu

SKILL_ROOT=$(cd "$(dirname "$0")/.." && pwd)
CONVERT_SCRIPT="$SKILL_ROOT/scripts/convert_model.sh"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

PKG="$TMP/pkg"
CONVERTER="$PKG/tools/converter/converter/converter_lite"
mkdir -p "$(dirname "$CONVERTER")" "$PKG/tools/converter/lib" "$PKG/runtime/lib"
: > "$PKG/tools/converter/lib/libmindspore_converter.so"
MODEL="$TMP/model.onnx"
: > "$MODEL"

cat > "$CONVERTER" <<'EOF'
#!/bin/bash
if [ "${1:-}" = "--help" ]; then
  [ -z "${FAKE_ENV_LOG:-}" ] || printf '%s\n' "$LD_LIBRARY_PATH" > "$FAKE_ENV_LOG"
  printf '%s\n' "${FAKE_HELP:-}"
  exit "${FAKE_HELP_RC:-0}"
fi
printf '%s\n' "$@" > "$FAKE_ARGS_LOG"
out=""
for arg in "$@"; do
  case "$arg" in --outputFile=*) out=${arg#--outputFile=};; esac
done
mkdir -p "$out/src"
: > "$out/src/net.cmake"
echo "CONVERT RESULT SUCCESS:0"
EOF
chmod +x "$CONVERTER"

run_case() {
  local name=$1 help=$2
  local output="$TMP/$name/micro" args="$TMP/$name/args.txt" env_log="$TMP/$name/env.txt"
  mkdir -p "$(dirname "$output")"
  FAKE_HELP="$help" FAKE_HELP_RC=0 FAKE_ARGS_LOG="$args" FAKE_ENV_LOG="$env_log" \
    LD_LIBRARY_PATH="$TMP/old/tools/converter/lib:$TMP/custom/lib" MSLITE_PKG="$PKG" \
    bash "$CONVERT_SCRIPT" "$MODEL" "$output" >/dev/null
  grep -q "$PKG/tools/converter/lib" "$env_log"
  grep -q "$TMP/custom/lib" "$env_log"
  ! grep -q "$TMP/old/tools/converter/lib" "$env_log"
  printf '%s\n' "$args"
}

supported_args=$(run_case supported 'options: --encryption=<bool>')
grep -qx -- '--encryption=false' "$supported_args"

unsupported_args=$(run_case unsupported 'Usage: converter_lite --fmk --modelFile')
if grep -q -- '--encryption' "$unsupported_args"; then
  echo "unexpected encryption argument for unsupported converter" >&2
  exit 1
fi

set +e
FAKE_HELP='broken' FAKE_HELP_RC=127 FAKE_ARGS_LOG="$TMP/failed-args.txt" MSLITE_PKG="$PKG" \
  bash "$CONVERT_SCRIPT" "$MODEL" "$TMP/failed/micro" >/dev/null 2>&1
rc=$?
set -e
test "$rc" -ne 0
test ! -e "$TMP/failed-args.txt"

echo "CONVERT_ENCRYPTION_COMPAT=PASS"
