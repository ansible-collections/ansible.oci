from __future__ import absolute_import, division, print_function

import types

from .conftest import load_collection_module, make_module_instance


def test_info_converts_scalar_lifecycle_state_to_sdk_list():
    """Verify info converts scalar lifecycle state to sdk list."""
    module_obj = load_collection_module("oci_waf_web_app_firewall_policy_info")
    instance = make_module_instance(
        module_obj,
        "OciWafWebAppFirewallPolicyInfoModule",
        {"compartment_id": "compartment1", "lifecycle_state": "active"},
        client=types.SimpleNamespace(),
    )
    assert instance.collect_list_filters(instance.list_filter_params) == {
        "compartment_id": "compartment1",
        "lifecycle_state": ["ACTIVE"],
    }
