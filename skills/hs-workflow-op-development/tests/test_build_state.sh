#!/bin/bash
# Regression tests for build_mslite.sh run identity and stale-state isolation.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_SCRIPT="$(cd "${SCRIPT_DIR}/../scripts" && pwd)/build_mslite.sh"
STATE_DIR=$(mktemp -d /tmp/mslite-build-state-test.XXXXXX)
trap 'rm -rf "${STATE_DIR}"' EXIT
REPO_ROOT="${STATE_DIR}/repo"
mkdir -p "${REPO_ROOT}"
git -C "${REPO_ROOT}" init -q
git -C "${REPO_ROOT}" config user.email build-state-test@example.invalid
git -C "${REPO_ROOT}" config user.name build-state-test
echo baseline > "${REPO_ROOT}/tracked.txt"
git -C "${REPO_ROOT}" add tracked.txt
git -C "${REPO_ROOT}" commit -qm baseline

fingerprint() {
  MSLITE_BUILD_STATE_DIR="${STATE_DIR}/must-not-be-created" \
    bash "${BUILD_SCRIPT}" --source-fingerprint "${REPO_ROOT}"
}

write_record() {
  local run_id="$1" profile="${2:-inference}"
  printf '%s\n' "${run_id}" > "${STATE_DIR}/mslite_build.run_id"
  {
    echo "RUN_ID=${run_id}"
    echo "PROFILE=${profile}"
    echo "STARTED=$(date +%s)"
    echo "ROOT=${REPO_ROOT}"
    echo "SOURCE_FINGERPRINT=$(fingerprint)"
  } > "${STATE_DIR}/mslite_build.start"
  echo "[build_mslite] RUN_ID=${run_id} PROFILE=${profile} test" > "${STATE_DIR}/mslite_build.log"
  rm -f "${STATE_DIR}/mslite_build.result"
}

expect_rc_and_text() {
  local want_rc="$1" want_text="$2"; shift 2
  local output rc
  set +e
  output=$(MSLITE_BUILD_STATE_DIR="${STATE_DIR}" bash "${BUILD_SCRIPT}" "$@" 2>&1)
  rc=$?
  set -u
  if [ "${rc}" -ne "${want_rc}" ] || ! printf '%s' "${output}" | grep -qF "${want_text}"; then
    echo "FAIL: expected rc=${want_rc} text=${want_text}; got rc=${rc}: ${output}" >&2
    exit 1
  fi
}

expect_rc_and_texts() {
  local want_rc="$1"; shift
  local output rc argument
  local -a expected=()
  while [ "$1" != "--" ]; do expected+=("$1"); shift; done
  shift
  set +e
  output=$(MSLITE_BUILD_STATE_DIR="${STATE_DIR}" bash "${BUILD_SCRIPT}" "$@" 2>&1)
  rc=$?
  set -u
  if [ "${rc}" -ne "${want_rc}" ]; then
    echo "FAIL: expected rc=${want_rc}; got rc=${rc}: ${output}" >&2
    exit 1
  fi
  for argument in "${expected[@]}"; do
    if ! printf '%s' "${output}" | grep -qF "${argument}"; then
      echo "FAIL: expected text=${argument}; got: ${output}" >&2
      exit 1
    fi
  done
}

fingerprint >/dev/null
expect_rc_and_text 1 "源码身份计算失败" --source-fingerprint "${STATE_DIR}/package"
if [ -e "${STATE_DIR}/must-not-be-created" ]; then
  echo "FAIL: --source-fingerprint mutated the build state directory" >&2
  exit 1
fi

PKG_FIXTURE="${STATE_DIR}/package"
mkdir -p "${PKG_FIXTURE}/runtime/lib" "${PKG_FIXTURE}/tools/converter/converter"
printf '#!/bin/sh\nexit 0\n' > "${PKG_FIXTURE}/tools/converter/converter/converter_lite"
chmod +x "${PKG_FIXTURE}/tools/converter/converter/converter_lite"
expect_rc_and_text 5 "training profile 缺少非空训练库" --verify-package-profile training "${PKG_FIXTURE}"
printf 'shared' > "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.so"
printf 'static' > "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.a"
expect_rc_and_texts 0 \
  "BUILD_PROFILE=training" \
  "RESOLVED_MSLITE_ENABLE_TRAIN=ON" \
  "TRAIN_PACKAGE_ARTIFACTS=PASS" -- --verify-package-profile training "${PKG_FIXTURE}"
expect_rc_and_text 5 "inference profile 的新鲜工具包意外包含训练库" --verify-package-profile inference "${PKG_FIXTURE}"
rm -f "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.so" \
  "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.a"
expect_rc_and_texts 0 \
  "BUILD_PROFILE=inference" \
  "RESOLVED_MSLITE_ENABLE_TRAIN=OFF" \
  "TRAIN_PACKAGE_ARTIFACTS=ABSENT" -- --verify-package-profile inference "${PKG_FIXTURE}"

write_record old-run
echo "old-run 3" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 NO_CURRENT_BUILD --status
expect_rc_and_text 12 STALE_BUILD_RECORD --status new-run

write_record current-run
rm -f "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 INCOMPLETE_BUILD_RECORD --status current-run

echo "old-run 3" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 STALE_BUILD_RECORD --status current-run

{
  echo "RUN_ID=current-run"
  echo "BUILD_PROFILE=inference"
  echo "RESOLVED_MSLITE_ENABLE_TRAIN=OFF"
  echo "TRAIN_PACKAGE_ARTIFACTS=ABSENT"
  echo "MSLITE_PKG=${PKG_FIXTURE}"
} > "${STATE_DIR}/mslite_build.result"
echo "current-run 0" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_texts 0 \
  "SUCCESS：RUN_ID=current-run" \
  "BUILD_PROFILE=inference" \
  "RESOLVED_MSLITE_ENABLE_TRAIN=OFF" \
  "TRAIN_PACKAGE_ARTIFACTS=ABSENT" \
  "MSLITE_PKG=${PKG_FIXTURE}" -- --status current-run
expect_rc_and_texts 0 \
  "BUILD_PROFILE=inference" \
  "RESOLVED_MSLITE_ENABLE_TRAIN=OFF" \
  "TRAIN_PACKAGE_ARTIFACTS=ABSENT" -- --wait 1 current-run

printf 'unexpected-training-lib' > "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.so"
expect_rc_and_text 12 STALE_BUILD_RECORD --status current-run
rm -f "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.so"

write_record training-run training
printf 'shared' > "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.so"
printf 'static' > "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.a"
{
  echo "RUN_ID=training-run"
  echo "BUILD_PROFILE=training"
  echo "RESOLVED_MSLITE_ENABLE_TRAIN=ON"
  echo "TRAIN_PACKAGE_ARTIFACTS=PASS"
  echo "MSLITE_PKG=${PKG_FIXTURE}"
} > "${STATE_DIR}/mslite_build.result"
echo "training-run 0" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_texts 0 \
  "BUILD_PROFILE=training" \
  "RESOLVED_MSLITE_ENABLE_TRAIN=ON" \
  "TRAIN_PACKAGE_ARTIFACTS=PASS" -- --status training-run
rm -f "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.so" \
  "${PKG_FIXTURE}/runtime/lib/libmindspore-lite-train.a"

write_record current-run
{
  echo "RUN_ID=current-run"
  echo "BUILD_PROFILE=inference"
  echo "RESOLVED_MSLITE_ENABLE_TRAIN=OFF"
  echo "TRAIN_PACKAGE_ARTIFACTS=ABSENT"
  echo "MSLITE_PKG=${PKG_FIXTURE}"
} > "${STATE_DIR}/mslite_build.result"
echo "current-run 0" > "${STATE_DIR}/mslite_build.rc"

rm -f "${STATE_DIR}/mslite_build.result"
expect_rc_and_text 12 INCOMPLETE_BUILD_RECORD --status current-run
{
  echo "RUN_ID=current-run"
  echo "BUILD_PROFILE=inference"
  echo "RESOLVED_MSLITE_ENABLE_TRAIN=OFF"
  echo "TRAIN_PACKAGE_ARTIFACTS=ABSENT"
  echo "MSLITE_PKG=${PKG_FIXTURE}"
} > "${STATE_DIR}/mslite_build.result"

echo changed >> "${REPO_ROOT}/tracked.txt"
expect_rc_and_text 12 STALE_BUILD_RECORD --status current-run

# dirty -> different dirty content must also invalidate the old run.
write_record dirty-run
echo changed-again >> "${REPO_ROOT}/tracked.txt"
echo "dirty-run 0" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 STALE_BUILD_RECORD --status dirty-run

# New untracked operator source must participate in the identity.
write_record untracked-run
echo 'int NewOp(void) { return 0; }' > "${REPO_ROOT}/new_op.c"
echo "untracked-run 0" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 STALE_BUILD_RECORD --status untracked-run

# Direct-submodule worktree changes are intentionally excluded because the
# upstream build applies managed patches there. Advancing its HEAD must still
# invalidate the outer build identity.
SUB_REPO="${STATE_DIR}/subrepo"
mkdir -p "${SUB_REPO}"
git -C "${SUB_REPO}" init -q
git -C "${SUB_REPO}" config user.email build-state-test@example.invalid
git -C "${SUB_REPO}" config user.name build-state-test
echo sub-baseline > "${SUB_REPO}/sub.txt"
git -C "${SUB_REPO}" add sub.txt
git -C "${SUB_REPO}" commit -qm baseline
git -C "${REPO_ROOT}" -c protocol.file.allow=always submodule add -q "${SUB_REPO}" modules/sub
git -C "${REPO_ROOT}" commit -qm 'add test submodule' .gitmodules modules/sub

submodule_fingerprint_before=$(fingerprint)
echo sub-changed >> "${REPO_ROOT}/modules/sub/sub.txt"
printf 'generated\n' > "${REPO_ROOT}/modules/sub/untracked.txt"
submodule_fingerprint_after=$(fingerprint)
if [ "${submodule_fingerprint_before}" != "${submodule_fingerprint_after}" ]; then
  echo "FAIL: direct-submodule worktree dirt changed the HEAD-only identity" >&2
  exit 1
fi

write_record submodule-head-run
git -C "${REPO_ROOT}/modules/sub" add sub.txt
git -C "${REPO_ROOT}/modules/sub" commit -qm 'advance test submodule'
echo "submodule-head-run 0" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 STALE_BUILD_RECORD --status submodule-head-run

# A recorded build-side submodule drift keeps its specialized diagnosis.
write_record drift-run
echo sub-changed-again >> "${REPO_ROOT}/modules/sub/sub.txt"
echo "[SUBMOD-LOCK] test drift" >> "${STATE_DIR}/mslite_build.log"
echo "drift-run 7" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 7 SUBMOD-DRIFT --status drift-run

# --stop must clear startup-stage descendants even before the build PGID file exists.
# Git Bash on Windows does not provide setsid, so retain the identity checks above
# and skip this POSIX process-group assertion there.
if command -v setsid >/dev/null 2>&1; then
  setsid bash -c 'sleep 60 & wait' &
  early_wrapper=$!
  printf '%s\n' "${early_wrapper}" > "${STATE_DIR}/mslite_build.pid"
  rm -f "${STATE_DIR}/mslite_build.pgid"
  expect_rc_and_text 0 STOPPED --stop
  if kill -0 "${early_wrapper}" 2>/dev/null || ps -g "${early_wrapper}" -o pid= 2>/dev/null | grep -q .; then
    echo "FAIL: --stop left startup-stage process-group descendants" >&2
    kill -KILL -- "-${early_wrapper}" 2>/dev/null || true
    exit 1
  fi
else
  echo "SKIP: setsid is unavailable; process-group cleanup assertion requires POSIX setsid"
fi

echo "BUILD_STATE_TEST=PASS"
