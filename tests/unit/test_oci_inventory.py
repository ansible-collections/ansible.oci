import hashlib
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, call

import pytest


PLUGIN_PATH = Path(__file__).parents[2] / "plugins/inventory/oci_inventory.py"


@pytest.fixture
def inventory_module(monkeypatch):
    auth = ModuleType("oci_auth")
    auth.create_service_client_from_options = Mock()
    auth.get_oci_config_from_options = lambda options: {"region": "us-ashburn-1"}
    common = ModuleType("oci_common")
    common.import_oci_sdk = lambda: (
        SimpleNamespace(
            core=SimpleNamespace(ComputeClient=object, VirtualNetworkClient=object)
        ),
        True,
    )
    common.serialize_oci_model = lambda value: value.__dict__.copy()

    monkeypatch.setitem(
        __import__("sys").modules,
        "ansible_collections.ansible.oci.plugins.module_utils.oci_auth",
        auth,
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "ansible_collections.ansible.oci.plugins.module_utils.oci_common",
        common,
    )
    spec = spec_from_file_location("oci_inventory_under_test", PLUGIN_PATH)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_discovery_filters_tags_and_resolves_primary_vnic(inventory_module):
    plugin = inventory_module.InventoryModule()
    options = {
        "compartments": ["compartment-a"],
        "regions": ["us-ashburn-1"],
        "lifecycle_states": ["RUNNING"],
        "freeform_tags": {"role": "web"},
        "defined_tags": {"operations": {"environment": "prod"}},
        "auth_type": "api_key",
        "config_file_location": "~/.oci/config",
        "config_profile_name": "DEFAULT",
        "tenancy": None,
        "region": None,
        "api_user": None,
        "api_user_fingerprint": None,
        "api_user_key_file": None,
        "api_user_key_pass_phrase": None,
    }
    plugin.get_option = options.__getitem__

    matching = SimpleNamespace(
        id="instance-a",
        compartment_id="compartment-a",
        display_name="web-a",
        availability_domain="AD-1",
        shape="VM.Standard",
        lifecycle_state="RUNNING",
        image_id="image-a",
        freeform_tags={"role": "web"},
        defined_tags={"operations": {"environment": "prod"}},
    )
    excluded = SimpleNamespace(
        id="instance-b", freeform_tags={"role": "db"}, defined_tags={}
    )
    attachment = SimpleNamespace(nic_index=0, vnic_id="vnic-a")
    vnic = SimpleNamespace(
        id="vnic-a",
        private_ip="10.0.0.10",
        public_ip="203.0.113.10",
        hostname_label="web-a",
        subnet_id="subnet-a",
    )
    compute = SimpleNamespace(
        list_instances=Mock(return_value=SimpleNamespace(data=[matching, excluded], headers={})),
        list_vnic_attachments=Mock(return_value=SimpleNamespace(data=[attachment], headers={})),
    )
    network = SimpleNamespace(
        get_vnic=Mock(return_value=SimpleNamespace(data=vnic))
    )
    inventory_module.create_service_client_from_options.side_effect = [compute, network]

    records = plugin._discover_records()

    assert len(records) == 1
    assert records[0]["instance_id"] == "instance-a"
    assert records[0]["name_with_id"] == "web-a_%s" % (
        hashlib.sha256(b"instance-a").hexdigest()[:8]
    )
    assert records[0]["private_ip"] == "10.0.0.10"
    assert records[0]["defined_tags"]["operations"]["environment"] == "prod"
    compute.list_instances.assert_called_once_with(
        compartment_id="compartment-a", lifecycle_state="RUNNING"
    )


def test_cache_and_readable_hostname_precedence(inventory_module):
    plugin = inventory_module.InventoryModule()
    options = {"cache": True, "hostnames": ["name_with_id", "id"]}
    plugin.get_option = options.__getitem__
    plugin.get_cache_key = lambda path: "cache-key"
    plugin._cache = {}
    plugin._discover_records = Mock(return_value=[{"id": "instance-a"}])

    assert plugin._get_records("inventory.oci_inventory.yml", True) == [{"id": "instance-a"}]
    assert plugin._get_records("inventory.oci_inventory.yml", True) == [{"id": "instance-a"}]
    plugin._discover_records.assert_called_once()
    assert plugin._hostname(
        {"id": "instance-a", "name_with_id": "web-a_63c6a1a2"}
    ) == "web-a_63c6a1a2"

    options["hostnames"] = ["display_name"]
    assert plugin._hostname({"id": "instance-a", "display_name": "web-a"}) == "web-a"

    options["hostnames"] = ["unsupported"]
    with pytest.raises(inventory_module.AnsibleParserError):
        plugin._hostname({"id": "instance-a"})


def test_default_groups_include_instance_metadata_and_tags(inventory_module):
    plugin = inventory_module.InventoryModule()
    added = []
    plugin.inventory = SimpleNamespace(
        add_group=lambda name: name,
        add_child=lambda group, host: added.append((group, host)),
    )

    plugin._add_default_groups(
        "instance-a",
        {
            "region": "us-ashburn-1",
            "compartment_id": "compartment-a",
            "availability_domain": "AD-1",
            "shape": "VM.Standard",
            "lifecycle_state": "RUNNING",
            "freeform_tags": {"role": "web"},
            "defined_tags": {"operations": {"environment": "prod"}},
        },
    )
    plugin._add_default_groups(
        "instance-b",
        {
            "region": "us-ashburn-1",
            "compartment_id": "compartment-a",
            "availability_domain": "AD-1",
            "shape": "VM.Standard",
            "lifecycle_state": "RUNNING",
            "freeform_tags": {"role": "database"},
            "defined_tags": {},
        },
    )

    assert ("oci_region_us_ashburn_1", "instance-a") in added
    assert ("oci_region_us_ashburn_1", "instance-b") in added
    assert ("oci_tag_role_web", "instance-a") in added
    assert ("oci_tag_role_database", "instance-b") in added
    assert ("oci_tag_operations_environment_prod", "instance-a") in added


def test_verify_file_and_region_fallbacks(inventory_module, monkeypatch):
    plugin = inventory_module.InventoryModule()
    monkeypatch.setattr(
        inventory_module.BaseInventoryPlugin, "verify_file", lambda self, path: True
    )
    assert plugin.verify_file("inventory.oci_inventory.yml") is True
    assert plugin.verify_file("inventory.yml") is False

    options = {"regions": [], "region": None}
    plugin.get_option = options.__getitem__
    assert plugin._regions({}) == ["us-ashburn-1"]

    inventory_module.get_oci_config_from_options = lambda value: {}
    with pytest.raises(inventory_module.AnsibleParserError):
        plugin._regions({})


def test_pagination_lifecycle_and_tag_filters(inventory_module):
    plugin = inventory_module.InventoryModule()
    first = SimpleNamespace(data=["first"], headers={"opc-next-page": "next"})
    second = SimpleNamespace(data=["second"], headers={})
    method = Mock(side_effect=[first, second])

    assert plugin._list_all(method, compartment_id="compartment-a") == [
        "first",
        "second",
    ]
    method.assert_has_calls(
        [
            call(compartment_id="compartment-a"),
            call(page="next", compartment_id="compartment-a"),
        ]
    )

    plugin.get_option = {"lifecycle_states": ["RUNNING", "STOPPED"]}.__getitem__
    compute = SimpleNamespace(
        list_instances=Mock(return_value=SimpleNamespace(data=[], headers={}))
    )
    assert plugin._list_instances(compute, "compartment-a") == []
    assert compute.list_instances.call_count == 2

    plugin.get_option = {
        "freeform_tags": {"role": "web"},
        "defined_tags": {"operations": {"environment": "prod"}},
    }.__getitem__
    assert plugin._matches_tags(SimpleNamespace(freeform_tags={"role": "db"})) is False
    assert plugin._matches_tags(
        SimpleNamespace(freeform_tags={"role": "web"}, defined_tags={})
    ) is False
    assert plugin._matches_tags(
        SimpleNamespace(
            freeform_tags={"role": "web"},
            defined_tags={"operations": {"environment": "prod"}},
        )
    ) is True


def test_record_skips_unreachable_instances_and_uses_id_when_unnamed(inventory_module):
    plugin = inventory_module.InventoryModule()
    plugin.display = SimpleNamespace(warning=Mock())
    instance = SimpleNamespace(id="instance-a")
    compute = SimpleNamespace(
        list_vnic_attachments=Mock(
            return_value=SimpleNamespace(data=[SimpleNamespace(nic_index=1)], headers={})
        )
    )
    assert (
        plugin._record_for_instance(
            compute, Mock(), instance, "compartment-a", "region-a"
        )
        is None
    )

    attachment = SimpleNamespace(nic_index=0, vnic_id="vnic-a")
    compute.list_vnic_attachments.return_value = SimpleNamespace(
        data=[attachment], headers={}
    )
    network = SimpleNamespace(
        get_vnic=Mock(return_value=SimpleNamespace(data=SimpleNamespace(id="vnic-a")))
    )
    assert (
        plugin._record_for_instance(
            compute, network, instance, "compartment-a", "region-a"
        )
        is None
    )

    vnic = SimpleNamespace(id="vnic-a", private_ip="10.0.0.10")
    network.get_vnic.return_value = SimpleNamespace(data=vnic)
    record = plugin._record_for_instance(
        compute, network, instance, "compartment-a", "region-a"
    )
    assert record["name_with_id"] == "instance-a"
    assert record["compartment_id"] == "compartment-a"
    assert record["public_ip"] is None


def test_cache_disabled_and_add_record_paths(inventory_module):
    plugin = inventory_module.InventoryModule()
    options = {
        "cache": False,
        "hostnames": ["name_with_id"],
        "strict": False,
        "compose": {},
        "groups": {},
        "keyed_groups": [],
    }
    plugin.get_option = options.__getitem__
    plugin._discover_records = Mock(return_value=[{"id": "instance-a"}])
    assert plugin._get_records("inventory.oci_inventory.yml", True) == [
        {"id": "instance-a"}
    ]
    assert plugin._get_records("inventory.oci_inventory.yml", True) == [
        {"id": "instance-a"}
    ]
    assert plugin._discover_records.call_count == 2

    set_variable = Mock()
    plugin.inventory = SimpleNamespace(
        get_host=lambda hostname: None,
        add_host=Mock(),
        set_variable=set_variable,
    )
    plugin._add_default_groups = Mock()
    plugin._set_composite_vars = Mock()
    plugin._add_host_to_composed_groups = Mock()
    plugin._add_host_to_keyed_groups = Mock()
    record = {
        "instance_id": "instance-a",
        "name_with_id": "web-a",
        "private_ip": "10.0.0.10",
    }
    plugin._add_record(record)
    plugin.inventory.add_host.assert_called_once_with("web-a")
    set_variable.assert_any_call("web-a", "ansible_host", "10.0.0.10")

    plugin.inventory.get_host = lambda hostname: SimpleNamespace(
        get_vars=lambda: {"instance_id": "different-instance"}
    )
    with pytest.raises(inventory_module.AnsibleParserError, match="hostname collision"):
        plugin._add_record(record)
