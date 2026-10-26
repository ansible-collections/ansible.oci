from __future__ import absolute_import, division, print_function

import types

from .conftest import (
    FakeModel,
    FakeResponse,
    load_collection_module,
    make_module_instance,
    install_fake_oci,
)


def test_info_includes_tunnels_and_secret_only_when_requested(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection_info")
    secret_calls = []
    client = types.SimpleNamespace(
        get_ip_sec_connection=lambda **kwargs: FakeResponse(
            FakeModel(id="ipsc", display_name="vpn")
        ),
        list_ip_sec_connection_tunnels=lambda **kwargs: FakeResponse(
            [FakeModel(id="t1", display_name="tunnel")]
        ),
        get_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: secret_calls.append(
            kwargs
        )
        or FakeResponse(FakeModel(shared_secret="s")),
    )
    instance = make_module_instance(
        module,
        "OciNetworkIpsecConnectionInfoModule",
        {
            "ipsc_id": "ipsc",
            "include_tunnels": True,
            "include_shared_secret": True,
        },
        client=client,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.list_all_resources = lambda fn, *args, **kwargs: fn(*args, **kwargs).data
    values = instance.fetch_resources()
    result = instance.serialize_result_resource(values[0])
    assert result["tunnels"][0]["shared_secret"] == "s"
    assert secret_calls[0]["tunnel_id"] == "t1"


def test_info_does_not_fetch_tunnels_by_default(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection_info")
    client = types.SimpleNamespace(
        get_ip_sec_connection=lambda **kwargs: FakeResponse(
            FakeModel(id="ipsc", display_name="vpn")
        ),
        list_ip_sec_connection_tunnels=lambda **kwargs: (value for value in ()).throw(
            AssertionError("unexpected")
        ),
    )
    instance = make_module_instance(
        module,
        "OciNetworkIpsecConnectionInfoModule",
        {
            "ipsc_id": "ipsc",
            "include_tunnels": False,
            "include_shared_secret": False,
        },
        client=client,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    assert len(instance.fetch_resources()) == 1
