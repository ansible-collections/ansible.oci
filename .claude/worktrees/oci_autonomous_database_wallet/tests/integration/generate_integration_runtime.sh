#!/usr/bin/env bash
set -euo pipefail

# Resolve the template/output locations relative to this script.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OCI_CONFIG_TEMPLATE_FILE="${SCRIPT_DIR}/oci_config.tpl"
INTEGRATION_CONFIG_TEMPLATE_FILE="${SCRIPT_DIR}/integration_config.yml.tpl"
INTEGRATION_CONFIG_OUTPUT_FILE="${SCRIPT_DIR}/integration_config.yml"
RUNTIME_DIR="${SCRIPT_DIR}/.runtime"
OCI_RUNTIME_CONFIG_FILE="${RUNTIME_DIR}/config"
OCI_RUNTIME_KEY_FILE="${RUNTIME_DIR}/oci_api_key.pem"
OCI_CONFIG_PROFILE="${OCI_CONFIG_PROFILE:-DEFAULT}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# Fail fast when the workflow did not provide the OCI auth inputs we need.
required_vars=(
    OCI_TEST_COMPARTMENT_ID
    OCI_TENANCY_ID
    OCI_USER_ID
    OCI_REGION
    OCI_USER_FINGERPRINT
    OCI_USER_KEY_CONTENT
)

for var_name in "${required_vars[@]}"; do
    if [[ -z "${!var_name:-}" ]]; then
        echo "Missing required environment variable: ${var_name}" >&2
        exit 1
    fi
done

# Recreate the runtime directory so each run starts with fresh OCI auth files.
# mkdir -p combined with -m only applies the mode to the deepest directory
# (SC2174), so chmod the leaf directory explicitly afterwards.
rm -rf "${RUNTIME_DIR}"
mkdir -p "${RUNTIME_DIR}"
chmod 700 "${RUNTIME_DIR}"
umask 077

# Materialize the OCI private key consumed by the tests.
printf '%s\n' "${OCI_USER_KEY_CONTENT}" > "${OCI_RUNTIME_KEY_FILE}"
# Render both templates with the generated runtime paths and OCI values.
export OCI_RUNTIME_CONFIG_FILE
export OCI_RUNTIME_KEY_FILE
export OCI_CONFIG_PROFILE
export OCI_CONFIG_TEMPLATE_FILE
export INTEGRATION_CONFIG_TEMPLATE_FILE
export INTEGRATION_CONFIG_OUTPUT_FILE

"${PYTHON_BIN}" <<'PY'
from pathlib import Path
from string import Template
import os

for template_key, output_key in (
    ("OCI_CONFIG_TEMPLATE_FILE", "OCI_RUNTIME_CONFIG_FILE"),
    ("INTEGRATION_CONFIG_TEMPLATE_FILE", "INTEGRATION_CONFIG_OUTPUT_FILE"),
):
    template = Path(os.environ[template_key])
    output = Path(os.environ[output_key])
    rendered = Template(template.read_text(encoding="utf-8")).substitute(os.environ)
    output.write_text(rendered, encoding="utf-8")
PY

chmod 600 "${OCI_RUNTIME_KEY_FILE}" "${OCI_RUNTIME_CONFIG_FILE}"
