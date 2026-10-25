from __future__ import absolute_import, division, print_function

__metaclass__ = type
from .conftest import (
    DummyModule,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def make_info(module_obj, params):
    """Return a module instance without OCI authentication."""
    return make_module_instance(
        module_obj, "OciNetworkFirewallPolicyInfoModule", params
    )


def test_info_filters_and_result_key(monkeypatch):
    """Verify info filters and result key."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall_policy_info")
    captured = {}

    def fake_ansible_module(**kw):
        """Capture the argument specification for validation."""
        captured.update(kw)
        return DummyModule({})

    monkeypatch.setattr(module, "AnsibleModule", fake_ansible_module)

    class FakeInfoModule:
        def __init__(self, module):
            """Store the test module instance."""
            self.module = module

        def execute_info_module(self):
            """Complete the fake info operation."""
            pass

    monkeypatch.setattr(module, "OciNetworkFirewallPolicyInfoModule", FakeInfoModule)
    module.main()
    assert captured["required_one_of"] == [
        ["compartment_id", "network_firewall_policy_id"]
    ]
    monkeypatch.undo()
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall_policy_info")
    instance = make_info(module, {"compartment_id": "c", "lifecycle_state": "active"})
    calls = []
    instance.client = type("C", (), {"list_network_firewall_policies": "list"})()
    monkeypatch.setattr(
        instance, "list_all_resources", lambda fn, **kw: calls.append((fn, kw)) or []
    )
    assert instance.fetch_resources() == []
    assert calls[0][1] == {"compartment_id": "c", "lifecycle_state": "ACTIVE"}
