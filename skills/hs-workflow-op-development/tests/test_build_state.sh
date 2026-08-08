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
  # Ask the production script to compute it by starting a deliberately invalid
  # build would mutate state, so mirror its payload here for this tiny repo.
  {
    echo "ROOT_HEAD=$(git -C "${REPO_ROOT}" rev-parse HEAD)"
    git -C "${REPO_ROOT}" diff --no-ext-diff --binary HEAD --
    while IFS= read -r -d '' file; do
      printf 'UNTRACKED:%s:' "${file}"
      sha256sum "${REPO_ROOT}/${file}"
    done < <(git -C "${REPO_ROOT}" ls-files --others --exclude-standard -z)
    while read -r path; do
      [ -n "${path}" ] || continue
      echo "SUBMODULE:${path}:HEAD=$(git -C "${REPO_ROOT}/${path}" rev-parse HEAD)"
      git -C "${REPO_ROOT}/${path}" diff --no-ext-diff --binary HEAD --
      while IFS= read -r -d '' file; do
        printf 'SUBMODULE_UNTRACKED:%s/%s:' "${path}" "${file}"
        sha256sum "${REPO_ROOT}/${path}/${file}"
      done < <(git -C "${REPO_ROOT}/${path}" ls-files --others --exclude-standard -z)
    done < <(git -C "${REPO_ROOT}" submodule status --recursive 2>/dev/null | awk '{print $2}')
  } | sha256sum | awk '{print $1}'
}

write_record() {
  local run_id="$1"
  printf '%s\n' "${run_id}" > "${STATE_DIR}/mslite_build.run_id"
  {
    echo "RUN_ID=${run_id}"
    echo "STARTED=$(date +%s)"
    echo "ROOT=${REPO_ROOT}"
    echo "SOURCE_FINGERPRINT=$(fingerprint)"
  } > "${STATE_DIR}/mslite_build.start"
  echo "[build_mslite] RUN_ID=${run_id} test" > "${STATE_DIR}/mslite_build.log"
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

write_record old-run
echo "old-run 3" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 NO_CURRENT_BUILD --status
expect_rc_and_text 12 STALE_BUILD_RECORD --status new-run

write_record current-run
rm -f "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 INCOMPLETE_BUILD_RECORD --status current-run

echo "old-run 3" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 STALE_BUILD_RECORD --status current-run

echo "MSLITE_PKG=/tmp/fake-package" >> "${STATE_DIR}/mslite_build.log"
echo "current-run 0" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 0 "SUCCESS：RUN_ID=current-run" --status current-run

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

# Changes inside a nested submodule must change the outer build identity too.
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

write_record submodule-run
echo sub-changed >> "${REPO_ROOT}/modules/sub/sub.txt"
echo "submodule-run 0" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 12 STALE_BUILD_RECORD --status submodule-run

# A real build-side submodule drift exit keeps its specialized diagnosis even
# though the repository fingerprint necessarily changed.
write_record drift-run
echo sub-changed-again >> "${REPO_ROOT}/modules/sub/sub.txt"
echo "[SUBMOD-LOCK] test drift" >> "${STATE_DIR}/mslite_build.log"
echo "drift-run 7" > "${STATE_DIR}/mslite_build.rc"
expect_rc_and_text 7 SUBMOD-DRIFT --status drift-run

echo "BUILD_STATE_TEST=PASS"
