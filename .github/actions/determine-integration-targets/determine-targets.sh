#!/usr/bin/env bash
set -euo pipefail

pr_number="${1:?pr-number argument is required}"
repo="${2:?repository argument is required}"
changed_files_override="${CHANGED_FILES_OVERRIDE:-}"

declare -A selected_targets=()
run_all=false

add_target() {
  local target_name="$1"

  if [[ -n "${target_name}" ]]; then
    selected_targets["${target_name}"]=1
  fi
}

classify_file() {
  local file_path="$1"
  local file_name target_name

  case "${file_path}" in
    plugins/module_utils/*)
      run_all=true
      ;;
    plugins/modules/oci_*_info.py)
      file_name="$(basename "${file_path}" .py)"
      add_target "${file_name%_info}"
      ;;
    plugins/modules/oci_*.py)
      file_name="$(basename "${file_path}" .py)"
      add_target "${file_name}"
      ;;
    tests/integration/targets/oci_*/*)
      target_name="${file_path#tests/integration/targets/}"
      add_target "${target_name%%/*}"
      ;;
    plugins/doc_fragments/*)
      ;;
    *)
      run_all=true
      ;;
  esac
}

emit_outputs() {
  local targets

  if [[ "${run_all}" == true ]]; then
    {
      echo "run-integration=true"
      echo "targets="
    } >> "${GITHUB_OUTPUT}"
    return
  fi

  if [[ "${#selected_targets[@]}" -gt 0 ]]; then
    targets="$(
      printf '%s\n' "${!selected_targets[@]}" | sort -u | paste -sd' ' -
    )"
    {
      echo "run-integration=true"
      echo "targets=${targets}"
    } >> "${GITHUB_OUTPUT}"
    return
  fi

  {
    echo "run-integration=false"
    echo "targets="
  } >> "${GITHUB_OUTPUT}"
}

if [[ -n "${changed_files_override}" ]]; then
  changed_files="${changed_files_override}"
else
  changed_files="$(gh pr diff "${pr_number}" --name-only --repo "${repo}")"
fi

while IFS= read -r file_path; do
  [[ -z "${file_path}" ]] && continue
  classify_file "${file_path}"
done <<< "${changed_files}"

emit_outputs
