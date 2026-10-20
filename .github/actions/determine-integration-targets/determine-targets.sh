#!/usr/bin/env bash
set -euo pipefail

collection_path="${1:?collection-path argument is required}"
base_sha="${2:?base-sha argument is required}"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Use a disposable checkout. Keep the base and PR head on separate local branches.
cd "${collection_path}"
git branch -f ci-base "${base_sha}"
git checkout -B ci-head HEAD
merge_base="$(git merge-base ci-base HEAD)"
changed_files="$(git diff --name-only "${merge_base}" HEAD)"

run_all=false
runtime_changed=false
while IFS= read -r file_path; do
  case "${file_path}" in
    Makefile|requirements.txt)
      # Native collection selection ignores these files.
      run_all=true
      ;;
    meta/runtime.yml)
      runtime_changed=true
      ;;
  esac
done <<< "${changed_files}"

# Include renames as deletions. The old utility imports are absent from the PR head.
deleted_utils="$(git diff --name-only --no-renames --diff-filter=D \
  "${merge_base}" HEAD -- plugins/module_utils/)"
if [[ -n "${deleted_utils}" ]]; then
  run_all=true
fi

selection_args=(--changed --base-branch ci-base)
if [[ "${run_all}" == true ]]; then
  echo "Shared infrastructure or a removed utility requires all integration targets."
  selection_args=()
elif [[ "${runtime_changed}" == true ]]; then
  filtered_files="$(printf '%s\n' "${changed_files}" |
    python3 "${script_dir}/filter_changed_paths.py" "${merge_base}")"
  if [[ "${filtered_files}" != "${changed_files}" ]]; then
    changed_paths_file="$(mktemp)"
    trap 'rm -f -- "${changed_paths_file}"' EXIT
    printf '%s\n' "${filtered_files}" > "${changed_paths_file}"
    selection_args=(--changed-from "${changed_paths_file}")
  else
    selection_args=()
  fi
fi

selected="$(ansible-test integration --list-targets --allow-destructive "${selection_args[@]}")"
targets=()
if [[ -n "${selected}" ]]; then
  selected="$(printf '%s\n' "${selected}" | LC_ALL=C sort -u)"
  while IFS= read -r target; do
    # Target names enter a shell command in the integration execution job.
    if [[ ! "${target}" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$ ]]; then
      echo "Invalid integration target: ${target}" >&2
      exit 1
    fi
    targets+=("${target}")
  done <<< "${selected}"
fi

run_integration=false
if [[ "${#targets[@]}" -gt 0 ]]; then
  run_integration=true
  printf 'Selected integration target: %s\n' "${targets[@]}"
else
  echo "No integration targets selected."
fi

{
  echo "run-integration=${run_integration}"
  echo "targets=${targets[*]}"
} >> "${GITHUB_OUTPUT:?GITHUB_OUTPUT must be set}"
