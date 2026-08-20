#!/bin/bash
# Source this file to bind converter_lite to the shared libraries in this run's MSLITE_PKG.
# The change is process-local; it never edits /etc/ld.so.conf, ~/.bashrc, or another package.

_converter_runtime_fail() {
  echo "CONVERTER_RUNTIME_GATE=FAIL reason=$*" >&2
  return 1 2>/dev/null || exit 1
}

[ -n "${MSLITE_PKG:-}" ] || _converter_runtime_fail "MSLITE_PKG_not_set" || return 1
[ -d "$MSLITE_PKG" ] || _converter_runtime_fail "MSLITE_PKG_not_found:$MSLITE_PKG" || return 1

_mslite_pkg_real=$(realpath "$MSLITE_PKG") || _converter_runtime_fail "MSLITE_PKG_realpath_failed:$MSLITE_PKG" || return 1
_converter_lib_files=$(find "$_mslite_pkg_real" -name 'libmindspore_converter.so*' \( -type f -o -type l \) -print 2>/dev/null)
[ -n "$_converter_lib_files" ] || _converter_runtime_fail "libmindspore_converter.so_not_found_under_MSLITE_PKG:$_mslite_pkg_real" || return 1
while IFS= read -r _library; do
  [ -e "$_library" ] || _converter_runtime_fail "broken_converter_library:$_library" || return 1
  _library_real=$(realpath "$_library") || _converter_runtime_fail "converter_library_realpath_failed:$_library" || return 1
  case "$_library_real" in
    "$_mslite_pkg_real"/*) ;;
    *) _converter_runtime_fail "converter_library_identity_conflict_outside_MSLITE_PKG:$_library_real" || return 1 ;;
  esac
done <<EOF
$_converter_lib_files
EOF

_converter_lib_dirs=""
for _candidate in \
  "$_mslite_pkg_real/tools/converter/lib" \
  "$_mslite_pkg_real/runtime/lib"
do
  [ -d "$_candidate" ] || continue
  case ":$_converter_lib_dirs:" in *":$_candidate:"*) ;; *) _converter_lib_dirs="${_converter_lib_dirs:+$_converter_lib_dirs:}$_candidate" ;; esac
done
while IFS= read -r _library; do
  _candidate=$(dirname "$_library")
  case ":$_converter_lib_dirs:" in *":$_candidate:"*) ;; *) _converter_lib_dirs="${_converter_lib_dirs:+$_converter_lib_dirs:}$_candidate" ;; esac
done <<EOF
$_converter_lib_files
EOF

# Retain unrelated caller paths, but do not let another MSLite package override this run.
_kept_library_path=""
_old_ifs=$IFS
IFS=:
for _candidate in ${LD_LIBRARY_PATH:-}; do
  [ -n "$_candidate" ] || continue
  case "$_candidate" in
    "$_mslite_pkg_real"/*) _keep=yes ;;
    */tools/converter/lib|*/runtime/lib) _keep=no ;;
    *)
      if [ -e "$_candidate/libmindspore_converter.so" ]; then _keep=no; else _keep=yes; fi
      ;;
  esac
  if [ "$_keep" = yes ]; then
    case ":$_kept_library_path:" in *":$_candidate:"*) ;; *) _kept_library_path="${_kept_library_path:+$_kept_library_path:}$_candidate" ;; esac
  fi
done
IFS=$_old_ifs

export MSLITE_PKG="$_mslite_pkg_real"
export LD_LIBRARY_PATH="$_converter_lib_dirs${_kept_library_path:+:$_kept_library_path}"
export CONVERTER_RUNTIME_LIBRARY_DIRS="$_converter_lib_dirs"
unset _converter_lib_files _converter_lib_dirs _kept_library_path _old_ifs _candidate _library _library_real _keep _mslite_pkg_real
