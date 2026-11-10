from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def install_fake_oci(monkeypatch):
    """Install the SDK connect model used by connect tests."""
    return shared_install_fake_oci(
        monkeypatch,
        model_names=("ConnectRemotePeeringConnectionsDetails",),
    )


def make_connect_module(module_obj, params, client=None, check_mode=False):
    """Build a connect module instance without creating an OCI client."""
    return make_module_instance(
        module_obj,
        "OciNetworkRemotePeeringConnectionConnectModule",
        params,
        client=client,
        check_mode=check_mode,
    )


def test_connect_needed_is_false_for_same_pending_peer(monkeypatch):
    """Verify an accepted or pending request is idempotent."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    instance = make_connect_module(module_obj, {"peer_id": "peer", "peer_region_name": "region"})

    assert instance.connect_needed(
        FakeModel(peer_id="peer", peer_region_name="region", peering_status="PENDING", lifecycle_state="AVAILABLE")
    ) is False
    assert instance.connect_needed(
        FakeModel(peer_id="peer", peer_region_name="region", peering_status="PEERED", lifecycle_state="AVAILABLE")
    ) is False


def test_connect_needed_is_true_for_new_connection(monkeypatch):
    """Verify a new connection requires the connect operation."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    instance = make_connect_module(module_obj, {"peer_id": "peer", "peer_region_name": "region"})

    assert instance.connect_needed(FakeModel(peering_status="NEW", lifecycle_state="AVAILABLE")) is True


def test_connect_needed_fails_for_conflicting_peer(monkeypatch):
    """Verify a connection cannot be redirected to a different peer."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    instance = make_connect_module(module_obj, {"peer_id": "new-peer", "peer_region_name": "region"})

    try:
        instance.connect_needed(
            FakeModel(peer_id="old-peer", peer_region_name="region", peering_status="PEERED", lifecycle_state="AVAILABLE")
        )
    except FailJsonCalled as exc:
        assert "peer" in exc.payload["msg"]
    else:
        raise AssertionError("connect_needed should fail for a conflicting peer")


def test_execute_connect_posts_then_gets_resource(monkeypatch):
    """Verify normal mode sends the request and returns the refreshed RPC."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    calls = []

    def connect_remote_peering_connections(**kwargs):
        calls.append(("connect", kwargs))
        return FakeResponse(data=None)

    instance = make_connect_module(
        module_obj,
        {"remote_peering_connection_id": "rpc-id", "peer_id": "peer", "peer_region_name": "region"},
        client=types.SimpleNamespace(
            connect_remote_peering_connections=connect_remote_peering_connections,
        ),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    instance.get_resource_response = lambda: FakeResponse(
        data=FakeModel(id="rpc-id", lifecycle_state="AVAILABLE", peering_status="NEW")
    )

    try:
        instance.execute_connect_module()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is True
        assert exc.payload["resource"]["id"] == "rpc-id"
    else:
        raise AssertionError("execute_connect_module should exit")

    assert calls[0][0] == "connect"
    assert calls[0][1]["remote_peering_connection_id"] == "rpc-id"
    assert calls[0][1]["connect_remote_peering_connections_details"].peer_id == "peer"


def test_execute_connect_check_mode_does_not_post(monkeypatch):
    """Verify check mode predicts a change without calling OCI connect."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    calls = []

    instance = make_connect_module(
        module_obj,
        {"remote_peering_connection_id": "rpc-id", "peer_id": "peer", "peer_region_name": "region"},
        client=types.SimpleNamespace(
            connect_remote_peering_connections=lambda **kwargs: calls.append(kwargs),
        ),
        check_mode=True,
    )
    instance.get_resource_response = lambda: FakeResponse(
        data=FakeModel(id="rpc-id", lifecycle_state="AVAILABLE", peering_status="NEW")
    )

    try:
        instance.execute_connect_module()
    except ExitJsonCalled as exc:
        assert exc.payload["changed"] is True
        assert exc.payload["resource"]["id"] == "rpc-id"
    else:
        raise AssertionError("execute_connect_module should exit")
    assert calls == []


def test_main_requires_all_connect_identifiers(monkeypatch):
    """Verify the argument specification requires all connect identifiers."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    captured = {}

    class FakeConnectModule:
        def __init__(self, module):
            self.module = module

        def execute_connect_module(self):
            captured["called"] = True

    def fake_ansible_module(**kwargs):
        captured["spec"] = kwargs["argument_spec"]
        return DummyModule({})

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciNetworkRemotePeeringConnectionConnectModule", FakeConnectModule)
    module_obj.main()

    assert captured["called"] is True
    for name in ("remote_peering_connection_id", "peer_id", "peer_region_name"):
        assert captured["spec"][name]["required"] is True


@pytest.mark.parametrize("status", ["REVOKED", "INVALID", "UNKNOWN_ENUM_VALUE", "BOGUS"])
def test_connect_needed_rejects_non_new_status(monkeypatch, status):
    """Verify non-new peering statuses fail instead of sending a request."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    instance = make_connect_module(module_obj, {"peer_id": "peer", "peer_region_name": "region"})
    with pytest.raises(FailJsonCalled):
        instance.connect_needed(FakeModel(
            peer_id=None,
            peer_region_name=None,
            peering_status=status,
            lifecycle_state="AVAILABLE",
        ))


def test_connect_needed_rejects_non_available_lifecycle(monkeypatch):
    """Verify connections in a non-available lifecycle state fail."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    instance = make_connect_module(module_obj, {"peer_id": "peer", "peer_region_name": "region"})
    with pytest.raises(FailJsonCalled):
        instance.connect_needed(FakeModel(peering_status="NEW", lifecycle_state="PROVISIONING"))


def test_connect_get_404_fails_with_clear_message(monkeypatch):
    """Verify a missing source connection fails clearly."""
    _, service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    instance = make_connect_module(
        module_obj,
        {"remote_peering_connection_id": "missing", "peer_id": "peer", "peer_region_name": "region"},
        client=types.SimpleNamespace(get_remote_peering_connection=lambda **kwargs: (_ for _ in ()).throw(service_error(404))),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    with pytest.raises(FailJsonCalled):
        instance.get_resource_response()


def test_connect_get_non404_error_propagates(monkeypatch):
    """Verify non-404 source lookup errors remain visible to callers."""
    _, service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_remote_peering_connection_connect")
    error = service_error(500)
    instance = make_connect_module(
        module_obj,
        {"remote_peering_connection_id": "rpc-id", "peer_id": "peer", "peer_region_name": "region"},
        client=types.SimpleNamespace(get_remote_peering_connection=lambda **kwargs: (_ for _ in ()).throw(error)),
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    with pytest.raises(service_error) as raised:
        instance.get_resource_response()
    assert raised.value is error
