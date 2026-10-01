"""Run integration task control flow through Ansible with OCI requests stubbed."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest
import yaml


ROOT = Path(__file__).parents[2]
TARGETS = ROOT / "tests/integration/targets"
IDENTITY_TARGETS = (
    "oci_identity_group",
    "oci_identity_user",
    "oci_identity_user_group_membership",
)


def tasks_in(document):
    for task in document:
        yield task
        for section in ("block", "rescue", "always"):
            yield from tasks_in(task.get(section, []))


def cleanup_tasks(target):
    data = yaml.safe_load((TARGETS / target / "tasks/cleanup.yml").read_text())
    return [task for task in tasks_in(data) if any(key.startswith("ansible.oci.") for key in task)]


CLEANUP_TARGETS = sorted(
    path.parent.parent.name for path in TARGETS.glob("*/tasks/cleanup.yml")
    if len(cleanup_tasks(path.parent.parent.name)) > 1
)


OCI_ACTION = '''import json
from pathlib import Path
from ansible.plugins.action import ActionBase

class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        result = super().run(tmp, task_vars)
        log = Path(task_vars['request_log'])
        calls = json.loads(log.read_text()) if log.exists() else []
        calls.append({'task': self._task.name, 'args': self._task.args})
        log.write_text(json.dumps(calls))
        attempt = sum(call['task'] == self._task.name and call['args'] == self._task.args for call in calls)
        result.update(changed=False)
        failures = task_vars.get('cleanup_failures', 0) if self._task.args.get('state') == 'absent' else task_vars.get('probe_failures', 0)
        if attempt <= failures:
            return dict(result, failed=True, msg=task_vars.get('api_error', 'NameResolutionError: failed DNS lookup'))
        return dict(result, groups=[], users=[])
'''


@pytest.fixture
def run_tasks(tmp_path):
    collection = tmp_path / "collections/ansible_collections/ansible/oci"
    (collection / "plugins/action").mkdir(parents=True)
    for directory in ("modules", "module_utils", "doc_fragments"):
        (collection / "plugins" / directory).symlink_to(ROOT / "plugins" / directory, target_is_directory=True)
    (collection / "meta").symlink_to(ROOT / "meta", target_is_directory=True)
    for module in (ROOT / "plugins/modules").glob("oci_*.py"):
        (collection / "plugins/action" / module.name).write_text(OCI_ACTION)
    environment = dict(os.environ, ANSIBLE_COLLECTIONS_PATH=str(tmp_path / "collections"),
                       ANSIBLE_LOCAL_TEMP=str(tmp_path / "local"), ANSIBLE_REMOTE_TEMP=str(tmp_path / "remote"),
                       ANSIBLE_NOCOLOR="1", ANSIBLE_HOST_KEY_CHECKING="False")

    # The OCI action stubs run on the controller and never connect to OCI.
    def run(document, variables):
        log = tmp_path / "requests.json"
        variables = dict(variables, request_log=str(log), oci_integration_config_file_location="/unused/config",
                         oci_integration_config_profile_name="DEFAULT")
        for task in tasks_in(document):
            if "retries" in task:
                task["delay"] = 0  # Exercise the actual retry count without network delays.
        playbook = tmp_path / "playbook.yml"
        playbook.write_text(yaml.safe_dump([{"hosts": "localhost", "gather_facts": False,
                                            "vars": variables, "tasks": document}], sort_keys=False))
        result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", "-c", "local", "-v", str(playbook)],
                                env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        return result.returncode, result.stdout, json.loads(log.read_text()) if log.exists() else []
    return run


def populated_cleanup_variables(tasks):
    variables = {}
    for task in tasks:
        for match in re.findall(r"\boci_[a-z0-9_]+(?:\.[a-z0-9_]+)*", str(task)):
            parts = match.split(".")
            parent = variables
            for part in parts[:-1]:
                parent = parent.setdefault(part, {})
            parent[parts[-1]] = "id-" + parts[-1]
    variables.update(oci_membership_added=True, oci_volume_group_integration_volume_ids=["volume-a", "volume-b"])
    return variables


@pytest.mark.parametrize("target", CLEANUP_TARGETS)
@pytest.mark.parametrize("original_failure, failures", [(False, 0), (False, 2), (False, 100), (True, 0), (True, 100)])
def test_cleanup_retries_and_attempts_every_deletion(run_tasks, target, original_failure, failures):
    document = yaml.safe_load((TARGETS / target / "tasks/cleanup.yml").read_text())
    deletes = cleanup_tasks(target)
    variables = populated_cleanup_variables(deletes)
    variables["cleanup_failures"] = failures
    lifecycle = [{"name": "Test lifecycle", "block": [
        {"name": "Original test result", "ansible.builtin.assert": {"that": [not original_failure], "fail_msg": "ORIGINAL_TEST_FAILURE"}},
    ], "always": document}]
    code, output, calls = run_tasks(lifecycle, variables)
    assert code == (2 if original_failure or failures > 3 else 0), output
    expected = [task["name"] for task in deletes if "when no ID" not in task["name"]]
    assert list(dict.fromkeys(call["task"] for call in calls)) == expected, output
    attempts = min(failures + 1, 4)
    for name in expected:
        items = 2 if name == "Delete leaked member volumes during cleanup" else 1
        assert sum(call["task"] == name for call in calls) == attempts * items, output
    if original_failure:
        assert "ORIGINAL_TEST_FAILURE" in output
    if failures > 3:
        assert "Resource cleanup failed after 3 retries" in output
        assert "NameResolutionError" in output
    if target == "oci_compute_inventory":
        for marker in ("instance", "subnet", "vcn"):
            cleared = f'"oci_compute_inventory_{marker}_id": ""' in output
            assert cleared == (failures <= 3), output


@pytest.mark.parametrize("target", IDENTITY_TARGETS)
@pytest.mark.parametrize("failures, error", [
    (0, ""), (2, "NameResolutionError: failed DNS lookup"),
    (100, "NameResolutionError: failed DNS lookup"),
    (100, "ServiceError: {'status': 401, 'code': 'NotAuthenticated'}"),
    (100, "ServiceError: {'status': 403, 'code': 'NotAuthorized'}"),
])
def test_domain_readiness_retries_without_hiding_failures(run_tasks, target, failures, error):
    document = yaml.safe_load((TARGETS / target / "tasks/main.yml").read_text())
    preceding = []
    for task in tasks_in(document):
        if any(key in task for key in ("ansible.oci.oci_identity_group", "ansible.oci.oci_identity_user")):
            break
        preceding.append(task)
    wait = next(task for task in preceding if task["name"] == "Wait for the temporary identity domain API")
    assert next(task for task in tasks_in([wait]) if "until" in task) in preceding
    variables = {"probe_failures": failures, "api_error": error}
    for task in tasks_in([wait]):
        for value in task.values():
            for name in re.findall(r"\boci_[a-z0-9_]+", str(value)):
                if name.endswith("_url"):
                    variables[name] = "https://identity.example.invalid"
                elif name.endswith("_name"):
                    variables[name] = "readiness-probe"
    code, output, calls = run_tasks([wait], variables)
    assert code == (2 if failures > 12 else 0), output
    assert len(calls) == min(failures + 1, 13), output
    assert all("domain_url" in call["args"] and "state" not in call["args"] for call in calls)
    if failures > 12:
        assert "readiness retry limit reached" in output
        assert error in output
