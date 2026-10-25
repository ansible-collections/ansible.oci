from __future__ import absolute_import, division, print_function

__metaclass__ = type

from .conftest import install_fake_oci, load_collection_module, make_module_instance


def test_info_metadata(monkeypatch):
    """Verify info metadata."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_firewall_info")
    instance = make_module_instance(
        module,
        "OciNetworkFirewallInfoModule",
        {"compartment_id": "c", "lifecycle_state": "active"},
    )
    assert instance.results_key == "network_firewalls"
    assert instance.list_filter_params == ["compartment_id", "lifecycle_state"]
