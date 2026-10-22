from __future__ import absolute_import, division, print_function
__metaclass__ = type

from copy import deepcopy
import json
import types

import pytest
import yaml

from ansible.module_utils import basic

from .conftest import load_collection_module


FIELDS = [
    ("oci_bastion", ("dns_proxy_status",), [("enabled", "ENABLED"), ("disabled", "DISABLED")]),
    ("oci_blockstorage_volume", ("source_details", "type"), [("volume_backup", "volumeBackup"), ("volume", "volume")]),
    ("oci_boot_volume", ("source_details", "type"), [("boot_volume_backup", "bootVolumeBackup")]),
    ("oci_network_route_table", ("route_rules", 0, "destination_type"), [
        ("cidr_block", "CIDR_BLOCK"), ("service_cidr_block", "SERVICE_CIDR_BLOCK"),
    ]),
    ("oci_network_security_list", ("ingress_security_rules", 0, "source_type"), [
        ("cidr_block", "CIDR_BLOCK"), ("service_cidr_block", "SERVICE_CIDR_BLOCK"),
        ("network_security_group", "NETWORK_SECURITY_GROUP"),
    ]),
    ("oci_network_security_list", ("egress_security_rules", 0, "destination_type"), [
        ("cidr_block", "CIDR_BLOCK"), ("service_cidr_block", "SERVICE_CIDR_BLOCK"),
        ("network_security_group", "NETWORK_SECURITY_GROUP"),
    ]),
    ("oci_object_storage_bucket", ("public_access_type",), [
        ("no_public_access", "NoPublicAccess"), ("object_read", "ObjectRead"),
        ("object_read_without_list", "ObjectReadWithoutList"),
    ]),
    ("oci_object_storage_bucket", ("storage_tier",), [("standard", "Standard"), ("archive", "Archive")]),
    ("oci_object_storage_bucket", ("auto_tiering",), [("disabled", "Disabled"), ("infrequent_access", "InfrequentAccess")]),
    ("oci_object_storage_bucket", ("versioning",), [("disabled", "Disabled"), ("enabled", "Enabled"), ("suspended", "Suspended")]),
    ("oci_oke_node_pool_options_info", ("node_pool_os_type",), [("ol7", "OL7"), ("ol8", "OL8"), ("ubuntu", "UBUNTU")]),
    ("oci_oke_node_pool_options_info", ("node_pool_os_arch",), [("x86_64", "X86_64"), ("aarch64", "AARCH64")]),
]
CASES = [(module, path, name, value) for module, path, values in FIELDS for name, value in values]
MODULES = sorted({field[0] for field in FIELDS})


def parameters_for(path, value):
    params = {"name": "ExampleResource"}
    if path[0] == "source_details":
        params["source_details"] = {"id": "ocid1.backup.oc1..Example"}
    elif path[0] == "route_rules":
        params["route_rules"] = [{"destination": "0.0.0.0/0", "network_entity_id": "ocid1.gateway.oc1..Example"}]
    elif path[0] == "ingress_security_rules":
        params["ingress_security_rules"] = [{"source": "0.0.0.0/0", "protocol": "6"}]
    elif path[0] == "egress_security_rules":
        params["egress_security_rules"] = [{"destination": "0.0.0.0/0", "protocol": "6"}]
    container = params
    for key in path[:-1]:
        container = container[key]
    container[path[-1]] = value
    return params


def run_main(monkeypatch, module_name, params, check_mode=False, record_warning=True):
    module_obj = load_collection_module(module_name)
    adapter_name = next(
        name for name, value in vars(module_obj).items()
        if name.startswith("Oci") and getattr(value, "__module__", None) == module_obj.__name__
    )
    captured = {"warnings": [], "adapter_class": getattr(module_obj, adapter_name)}
    supplied = deepcopy(params)
    if module_name == "oci_oke_node_pool_options_info":
        supplied.pop("name", None)
    supplied["_ansible_check_mode"] = check_mode
    monkeypatch.setattr(basic, "_ANSIBLE_ARGS", json.dumps({"ANSIBLE_MODULE_ARGS": supplied}).encode())
    monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy", raising=False)
    monkeypatch.setattr(basic, "_PARSED_MODULE_ARGS", deepcopy(supplied), raising=False)
    if record_warning:
        monkeypatch.setattr(
            basic.AnsibleModule, "deprecate",
            lambda self, msg, **kwargs: captured["warnings"].append(dict(msg=msg, **kwargs)),
        )

    def capture_adapter(module):
        captured["module"] = module
        return types.SimpleNamespace(execute_resource_module=lambda: None, execute_info_module=lambda: None)

    monkeypatch.setattr(module_obj, adapter_name, capture_adapter)
    module_obj.main()
    return module_obj, captured


@pytest.mark.parametrize("module_name,path,lowercase,sdk_value", CASES)
@pytest.mark.parametrize("legacy", [False, True])
@pytest.mark.parametrize("check_mode", [False, True])
def test_choice_validation_conversion_and_warnings(monkeypatch, module_name, path, lowercase, sdk_value, legacy, check_mode):
    supplied = sdk_value if legacy else lowercase
    unused_module, captured = run_main(monkeypatch, module_name, parameters_for(path, supplied), check_mode)
    value = captured["module"].params
    for key in path:
        value = value[key]
    assert value == sdk_value
    assert captured["module"].check_mode == check_mode
    if legacy and lowercase != sdk_value:
        field = ".".join(key for key in path if isinstance(key, str))
        assert captured["warnings"] == [{
            "msg": "The choice '%s' for '%s' is deprecated. Use '%s' instead." % (sdk_value, field, lowercase),
            "version": "2.0.0",
            "collection_name": "ansible.oci",
        }]
    else:
        assert captured["warnings"] == []


@pytest.mark.parametrize("module_name,path,values", FIELDS)
@pytest.mark.parametrize("invalid", ["invalid_choice", "CiDr_BlOcK"])
def test_invalid_choices_fail_before_resource_operations(monkeypatch, capsys, module_name, path, values, invalid):
    with pytest.raises(SystemExit) as result:
        run_main(monkeypatch, module_name, parameters_for(path, invalid))
    assert result.value.code == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["failed"] is True
    assert invalid in payload["msg"]


@pytest.mark.parametrize("module_name", MODULES)
def test_omitted_choices_do_not_warn(monkeypatch, module_name):
    unused_module, captured = run_main(monkeypatch, module_name, {"name": "ExampleResource"})
    assert captured["warnings"] == []


@pytest.mark.parametrize("module_name,path,values", FIELDS)
def test_documented_choices_match_validation(monkeypatch, module_name, path, values):
    module_obj, captured = run_main(monkeypatch, module_name, parameters_for(path, values[0][0]))
    doc = yaml.safe_load(module_obj.DOCUMENTATION)["options"]
    spec = captured["module"].argument_spec
    keys = [key for key in path if isinstance(key, str)]
    for index, key in enumerate(keys):
        doc = doc[key]
        spec = spec[key]
        if index < len(keys) - 1:
            doc = doc["suboptions"]
            spec = spec["options"]
    assert doc["choices"] == spec["choices"]
    assert doc.get("default") == spec.get("default")


@pytest.mark.parametrize("module_name,path", [
    ("oci_network_route_table", ("route_rules", 0, "destination_type")),
    ("oci_network_security_list", ("ingress_security_rules", 0, "source_type")),
    ("oci_network_security_list", ("egress_security_rules", 0, "destination_type")),
])
def test_nested_defaults_and_mixed_spelling_lists(monkeypatch, module_name, path):
    params = parameters_for(path, "cidr_block")
    rule = params[path[0]][0]
    rule.pop(path[-1])
    params[path[0]].extend([
        dict(rule, **{path[-1]: value}) for value in ("CIDR_BLOCK", "cidr_block", "CIDR_BLOCK")
    ])
    params["freeform_tags"] = {"destination_type": "MixedCase", "source_type": "CIDR_BLOCK"}
    unused_module, captured = run_main(monkeypatch, module_name, params)
    assert [item[path[-1]] for item in captured["module"].params[path[0]]] == ["CIDR_BLOCK"] * 4
    assert len(captured["warnings"]) == 1
    assert captured["module"].params["freeform_tags"] == params["freeform_tags"]


@pytest.mark.parametrize("module_name,path", [
    ("oci_network_route_table", ("route_rules", 0, "destination_type")),
    ("oci_network_security_list", ("ingress_security_rules", 0, "source_type")),
    ("oci_network_security_list", ("egress_security_rules", 0, "destination_type")),
])
def test_omitted_nested_defaults_and_empty_lists_do_not_warn(monkeypatch, module_name, path):
    params = parameters_for(path, "cidr_block")
    params[path[0]][0].pop(path[-1])
    unused_module, captured = run_main(monkeypatch, module_name, params)
    assert captured["module"].params[path[0]][0][path[-1]] == "CIDR_BLOCK"
    assert captured["warnings"] == []
    params[path[0]] = []
    unused_module, captured = run_main(monkeypatch, module_name, params)
    assert captured["module"].params[path[0]] == []
    assert captured["warnings"] == []


def test_ansible_result_contains_choice_deprecation(monkeypatch, capsys):
    unused_module, captured = run_main(
        monkeypatch, "oci_object_storage_bucket",
        {"name": "ExampleResource", "storage_tier": "Standard"}, record_warning=False,
    )
    with pytest.raises(SystemExit):
        captured["module"].exit_json(changed=False)
    result = json.loads(capsys.readouterr().out)
    assert "storage_tier" in str(result["deprecations"])
    assert "standard" in str(result["deprecations"])
    assert "2.0.0" in str(result["deprecations"])
    assert "ansible.oci" in str(result["deprecations"])


@pytest.mark.parametrize("check_mode", [False, True])
def test_lowercase_bucket_choices_preserve_idempotency(monkeypatch, check_mode):
    unused_module, captured = run_main(monkeypatch, "oci_object_storage_bucket", {
        "name": "ExampleResource", "storage_tier": "standard", "public_access_type": "no_public_access",
        "auto_tiering": "infrequent_access", "versioning": "enabled",
    }, check_mode)
    adapter = object.__new__(captured["adapter_class"])
    adapter.module = captured["module"]
    adapter.check_mode = check_mode
    resource = types.SimpleNamespace(
        name="ExampleResource", storage_tier="Standard", public_access_type="NoPublicAccess",
        auto_tiering="InfrequentAccess", versioning="Enabled",
    )
    assert not adapter.build_update_plan(resource)["update_needed"]


def test_lowercase_bucket_versioning_keeps_creation_restriction(monkeypatch, capsys):
    unused_module, captured = run_main(monkeypatch, "oci_object_storage_bucket", {
        "name": "ExampleResource", "compartment_id": "compartment", "versioning": "suspended",
    })
    adapter = object.__new__(captured["adapter_class"])
    adapter.module = captured["module"]
    with pytest.raises(SystemExit):
        adapter.validate_create_request()
    assert "versioning=suspended" in json.loads(capsys.readouterr().out)["msg"]
