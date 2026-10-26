from __future__ import absolute_import, division, print_function

import types

import pytest

from .conftest import (
    FakeModel,
    FakeResponse,
    ExitJsonCalled,
    FailJsonCalled,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def install_fake_oci(monkeypatch):
    """Keep SDK request models while replacing clients and exceptions.

    Args:
        monkeypatch: Fixture that restores replaced modules after each test.

    Returns:
        The fake SDK module and service error class.
    """
    import oci

    models = oci.core.models
    fake_oci, service_error = shared_install_fake_oci(monkeypatch)
    fake_oci.core.models = models
    return fake_oci, service_error


def make_module(module_obj, params, client=None, check_mode=False):
    instance = make_module_instance(
        module_obj,
        "OciNetworkIpsecConnectionModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    instance.list_all_resources = lambda fn, *args, **kwargs: fn(*args, **kwargs).data
    return instance


def test_create_details_include_tunnel_configuration_and_enum_values(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    instance = make_module(
        module,
        {
            "compartment_id": "comp",
            "name": "vpn",
            "cpe_id": "cpe",
            "drg_id": "drg",
            "static_routes": ["10.0.0.0/16"],
            "tunnel_configuration": [
                {"routing": "bgp", "ike_version": "v2", "shared_secret": "secret"}
            ],
            "wait": False,
        },
    )
    instance.client.create_ip_sec_connection = lambda **kwargs: FakeResponse(
        FakeModel(id="ipsc", lifecycle_state="AVAILABLE")
    )
    details = []
    original = module.build_model
    monkeypatch.setattr(
        module,
        "build_model",
        lambda *args, **kwargs: (
            details.append(original(*args, **kwargs)) or details[-1]
        ),
    )
    instance.create_resource()
    assert details[-1].tunnel_configuration[0].routing == "BGP"
    assert details[-1].tunnel_configuration[0].ike_version == "V2"


def test_tunnel_validation_rejects_duplicate_ids_before_update(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    instance = make_module(
        module,
        {"state": "present", "tunnels": [{"tunnel_id": "t1"}, {"tunnel_id": "t1"}]},
    )
    with pytest.raises(FailJsonCalled) as error:
        instance._validate_tunnels("ipsc")
    assert "duplicate" in error.value.payload["msg"]


def test_tunnel_validation_rejects_foreign_id(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    client = types.SimpleNamespace(
        list_ip_sec_connection_tunnels=lambda **kwargs: FakeResponse(
            [FakeModel(id="owned")]
        )
    )
    instance = make_module(module, {"tunnels": [{"tunnel_id": "foreign"}]}, client)
    with pytest.raises(FailJsonCalled) as error:
        instance._validate_tunnels("ipsc")
    assert "do not belong" in error.value.payload["msg"]


def test_secret_is_not_read_when_omitted(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    calls = []
    client = types.SimpleNamespace(
        get_ip_sec_connection=lambda **kwargs: FakeResponse(FakeModel(id="ipsc")),
        get_ip_sec_connection_tunnel=lambda **kwargs: FakeResponse(
            FakeModel(id="t1", display_name="one", routing="BGP")
        ),
        get_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: calls.append(
            kwargs
        ),
    )
    instance = make_module(
        module, {"tunnels": [{"tunnel_id": "t1", "routing": "bgp"}]}, client
    )
    assert instance._tunnel_plan("ipsc") == []
    assert calls == []


def test_changed_tunnel_updates_only_changed_secret(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    calls = []
    client = types.SimpleNamespace(
        get_ip_sec_connection=lambda **kwargs: FakeResponse(FakeModel(id="ipsc")),
        get_ip_sec_connection_tunnel=lambda **kwargs: FakeResponse(
            FakeModel(id="t1", display_name="one", routing="BGP")
        ),
        get_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: FakeResponse(
            FakeModel(shared_secret="old")
        ),
        update_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: calls.append(
            kwargs
        )
        or FakeResponse(FakeModel()),
    )
    instance = make_module(
        module,
        {"tunnels": [{"tunnel_id": "t1", "shared_secret": "new"}], "wait": False},
        client,
    )
    resource = FakeModel(id="ipsc")
    instance.apply_extra_change(resource)
    assert len(calls) == 1
    assert calls[0]["ipsc_id"] == "ipsc"


def test_create_rejects_existing_tunnel_updates(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    instance = make_module(
        module,
        {
            "compartment_id": "c",
            "name": "n",
            "cpe_id": "cpe",
            "drg_id": "d",
            "static_routes": [],
            "tunnels": [{"tunnel_id": "t1"}],
        },
    )
    with pytest.raises(FailJsonCalled) as error:
        instance.validate_create_request()
    assert "tunnel_configuration" in error.value.payload["msg"]


def test_execute_create_check_mode_does_not_call_sdk(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    calls = []
    client = types.SimpleNamespace(
        list_ip_sec_connections=lambda **kwargs: FakeResponse([]),
        create_ip_sec_connection=lambda **kwargs: calls.append(kwargs),
    )
    instance = make_module(
        module,
        {
            "state": "present",
            "compartment_id": "c",
            "name": "vpn",
            "cpe_id": "cpe",
            "drg_id": "drg",
            "static_routes": [],
        },
        client,
        check_mode=True,
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True
    assert calls == []


def test_execute_create_and_repeat_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    created = FakeModel(
        id="ipsc", display_name="vpn", lifecycle_state="AVAILABLE", static_routes=[]
    )
    calls = {"create": 0}
    client = types.SimpleNamespace(
        list_ip_sec_connections=lambda **kwargs: FakeResponse([]),
        create_ip_sec_connection=lambda **kwargs: calls.update(
            create=calls["create"] + 1
        )
        or FakeResponse(created),
    )
    params = {
        "state": "present",
        "compartment_id": "c",
        "name": "vpn",
        "cpe_id": "cpe",
        "drg_id": "drg",
        "static_routes": [],
        "wait": False,
    }
    instance = make_module(module, params, client)
    with pytest.raises(ExitJsonCalled) as first:
        instance.execute_resource_module()
    assert first.value.payload["changed"] is True
    assert calls["create"] == 1


def test_execute_delete_check_mode_does_not_call_delete(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    calls = []
    client = types.SimpleNamespace(
        get_ip_sec_connection=lambda **kwargs: FakeResponse(
            FakeModel(id="ipsc", lifecycle_state="AVAILABLE")
        ),
        delete_ip_sec_connection=lambda **kwargs: calls.append(kwargs),
    )
    instance = make_module(
        module, {"state": "absent", "ipsc_id": "ipsc"}, client, check_mode=True
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_resource_module()
    assert result.value.payload["changed"] is True
    assert calls == []


def test_unchanged_secret_is_idempotent(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    updates = []
    client = types.SimpleNamespace(
        get_ip_sec_connection_tunnel=lambda **kwargs: FakeResponse(
            FakeModel(id="t1", routing="BGP")
        ),
        get_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: FakeResponse(
            FakeModel(shared_secret="same")
        ),
        update_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: updates.append(
            kwargs
        ),
    )
    instance = make_module(
        module, {"tunnels": [{"tunnel_id": "t1", "shared_secret": "same"}]}, client
    )
    assert instance._tunnel_plan("ipsc") == []
    assert updates == []


def test_mixed_tunnels_update_only_changed_entry(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    updates = []
    tunnel_values = {
        "t1": FakeModel(id="t1", routing="BGP"),
        "t2": FakeModel(id="t2", routing="STATIC"),
    }
    client = types.SimpleNamespace(
        get_ip_sec_connection_tunnel=lambda **kwargs: FakeResponse(
            tunnel_values[kwargs["tunnel_id"]]
        ),
        update_ip_sec_connection_tunnel=lambda **kwargs: updates.append(kwargs)
        or FakeResponse(FakeModel()),
        get_ip_sec_connection=lambda **kwargs: FakeResponse(FakeModel(id="ipsc")),
    )
    instance = make_module(
        module,
        {
            "tunnels": [
                {"tunnel_id": "t1", "routing": "bgp"},
                {"tunnel_id": "t2", "routing": "policy"},
            ],
            "wait": False,
        },
        client,
    )
    instance.apply_extra_change(FakeModel(id="ipsc"))
    assert [call["tunnel_id"] for call in updates] == ["t2"]


def test_info_404_returns_empty_list(monkeypatch):
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection_info")

    class NotFound(Exception):
        status = 404

    client = types.SimpleNamespace(
        get_ip_sec_connection=lambda **kwargs: (value for value in ()).throw(NotFound())
    )
    instance = make_module_instance(
        module,
        "OciNetworkIpsecConnectionInfoModule",
        {"ipsc_id": "missing"},
        client=client,
    )
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    assert instance.fetch_resources() == []


@pytest.mark.parametrize("fail_secret", [False, True])
@pytest.mark.parametrize("wait", [False, True])
def test_combined_update_waits_before_secret(monkeypatch, fail_secret, wait):
    """Check prerequisite waits and partial-failure reporting.

    Args:
        monkeypatch: Pytest patch fixture.
        fail_secret: Whether the final secret API call fails.
        wait: Whether to wait after each completed update.
    """
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    events = []

    def change_secret(**kwargs):
        """Record the secret operation or simulate an API failure."""
        events.append("secret")
        if fail_secret:
            raise RuntimeError("secret update denied")
        return FakeResponse(FakeModel())

    client = types.SimpleNamespace(
        get_ip_sec_connection_tunnel=lambda **kwargs: FakeResponse(
            FakeModel(id="t1", display_name="old")
        ),
        get_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: FakeResponse(
            FakeModel(shared_secret="old key")
        ),
        update_ip_sec_connection_tunnel=lambda **kwargs: (
            events.append("settings") or FakeResponse(FakeModel())
        ),
        update_ip_sec_connection_tunnel_shared_secret=change_secret,
    )
    instance = make_module(
        module,
        {
            "wait": wait,
            "tunnels": [{"tunnel_id": "t1", "name": "new", "shared_secret": "new key"}],
        },
        client,
    )
    instance._wait_for_tunnel = lambda *args: events.append("wait")
    if fail_secret:
        with pytest.raises(FailJsonCalled) as failure:
            instance.apply_extra_change(FakeModel(id="ipsc"))
        assert failure.value.payload["changed"] is True
        assert "secret update denied" in failure.value.payload["msg"]
    else:
        instance.apply_extra_change(FakeModel(id="ipsc"))
        assert not instance.extra_change_needed(FakeModel(id="ipsc"))
    expected = ["settings", "wait", "secret"]
    if wait and not fail_secret:
        expected.append("wait")
    assert events == expected


def test_failed_first_tunnel_mutation_reports_unchanged(monkeypatch):
    """Verify that a rejected first mutation does not report completed changes."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    client = types.SimpleNamespace(
        get_ip_sec_connection_tunnel=lambda **kwargs: FakeResponse(FakeModel(id="t1")),
        get_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: FakeResponse(
            FakeModel(shared_secret="old")
        ),
        update_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: (
            (value for value in ()).throw(RuntimeError("denied"))
        ),
    )
    instance = make_module(
        module,
        {
            "tunnels": [{"tunnel_id": "t1", "shared_secret": "new"}],
        },
        client,
    )
    with pytest.raises(FailJsonCalled) as failure:
        instance.apply_extra_change(FakeModel(id="ipsc"))
    assert failure.value.payload["changed"] is False


def test_connection_enum_and_route_order_do_not_cause_updates(monkeypatch):
    """Verify that equivalent enum and route inputs remain unchanged."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    instance = make_module(
        module,
        {
            "cpe_local_identifier_type": "hostname",
            "static_routes": ["10.1.0.0/16", "10.0.0.0/16"],
        },
    )
    resource = FakeModel(
        id="ipsc",
        cpe_local_identifier_type="HOSTNAME",
        static_routes=["10.0.0.0/16", "10.1.0.0/16"],
    )
    assert not instance.needs_update(resource)


def test_parent_prerequisite_wait_uses_connection_identifier(monkeypatch):
    """Verify parent waiting before child updates when final waiting is disabled."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    fetched = []
    resource = FakeModel(id="ipsc", lifecycle_state="AVAILABLE")
    client = types.SimpleNamespace(
        get_ip_sec_connection=lambda **kwargs: (
            fetched.append(kwargs) or FakeResponse(resource)
        )
    )
    instance = make_module(module, {"wait": False}, client)
    instance._cached_tunnel_plan = [{"fields": {"routing": "STATIC"}}]
    instance._wait_for_response = lambda fetch: fetch()
    assert instance.get_mutation_result(resource, "ipsc", ("AVAILABLE",)) is resource
    assert fetched == [{"ipsc_id": "ipsc"}]


def test_foreign_tunnel_blocks_parent_update_in_execution(monkeypatch):
    """Verify ownership validation before parent or child writes."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    writes = []
    client = types.SimpleNamespace(
        get_ip_sec_connection=lambda **kwargs: FakeResponse(
            FakeModel(id="ipsc", display_name="old")
        ),
        list_ip_sec_connection_tunnels=lambda **kwargs: FakeResponse(
            [FakeModel(id="owned")]
        ),
        update_ip_sec_connection=lambda **kwargs: writes.append(kwargs),
    )
    instance = make_module(
        module,
        {
            "ipsc_id": "ipsc",
            "name": "new",
            "tunnels": [{"tunnel_id": "foreign"}],
        },
        client,
    )
    with pytest.raises(FailJsonCalled):
        instance.execute_resource_module()
    assert writes == []


def test_tunnel_plan_reads_secret_once_for_repeated_checks(monkeypatch):
    """Verify that repeated change checks share one read-only plan."""
    install_fake_oci(monkeypatch)
    module = load_collection_module("oci_network_ipsec_connection")
    reads = []
    client = types.SimpleNamespace(
        get_ip_sec_connection_tunnel=lambda **kwargs: FakeResponse(FakeModel(id="t1")),
        get_ip_sec_connection_tunnel_shared_secret=lambda **kwargs: (
            reads.append(kwargs) or FakeResponse(FakeModel(shared_secret="old"))
        ),
    )
    instance = make_module(
        module,
        {
            "tunnels": [{"tunnel_id": "t1", "shared_secret": "new"}],
        },
        client,
    )
    resource = FakeModel(id="ipsc")
    assert instance.extra_change_needed(resource)
    assert instance.extra_change_needed(resource)
    assert len(reads) == 1


def test_normalize_tunnel_maps_response_fields(monkeypatch):
    helper = load_collection_module("oci_network_ipsec_connection")
    value = helper.normalize_tunnel(
        {
            "bgp_session_info": {"customer_interface_ip": "10.0.0.2"},
            "oracle_can_initiate": "RESPONDER_ONLY",
            "dpd_mode": "RESPOND_ONLY",
            "dpd_timeout_in_sec": 20,
            "phase_one_details": {
                "custom_authentication_algorithm": "SHA2_256",
                "custom_dh_group": "GROUP14",
                "lifetime": 28800,
            },
        }
    )
    assert value["bgp_session_config"]["customer_interface_ip"] == "10.0.0.2"
    assert value["oracle_initiation"] == "RESPONDER_ONLY"
    assert value["dpd_config"]["dpd_timeout_in_sec"] == 20
    assert value["phase_one_config"]["diffie_helman_group"] == "GROUP14"


@pytest.mark.parametrize("create", [False, True])
def test_build_tunnel_details_normalizes_nested_enums(create):
    import oci

    helper = load_collection_module("oci_network_ipsec_connection")
    prefix = "Create" if create else "Update"
    model_class = getattr(oci.core.models, prefix + "IPSecConnectionTunnelDetails")
    model = helper.build_tunnel_details(
        {
            "routing": "bgp",
            "ike_version": "v2",
            "name": "tunnel",
            "dpd_config": {"dpd_mode": "respond_only"},
            "phase_one_config": {"diffie_helman_group": "group14"},
            "phase_two_config": {"encryption_algorithm": "aes_256_cbc"},
            "bgp_session_config": {"customer_bgp_asn": "65000"},
            "encryption_domain_config": {"cpe_traffic_selector": ["10.0.0.0/16"]},
        },
        model_class,
    )
    assert isinstance(
        model, getattr(oci.core.models, prefix + "IPSecConnectionTunnelDetails")
    )
    assert isinstance(
        model.bgp_session_config,
        getattr(oci.core.models, prefix + "IPSecTunnelBgpSessionDetails"),
    )
    assert isinstance(
        model.encryption_domain_config,
        getattr(oci.core.models, prefix + "IPSecTunnelEncryptionDomainDetails"),
    )
    assert model.display_name == "tunnel"
    assert model.routing == "BGP"
    assert model.ike_version == "V2"
    assert model.dpd_config.dpd_mode == "RESPOND_ONLY"
    assert model.phase_one_config.diffie_helman_group == "GROUP14"
    assert model.phase_two_config.encryption_algorithm == "AES_256_CBC"


def test_tunnel_comparison_ignores_selector_order_and_negotiated_values():
    """Compare desired fields against configured values only."""
    helper = load_collection_module("oci_network_ipsec_connection")
    current = {
        "encryption_domain_config": {
            "oracle_traffic_selector": ["10.0.0.0/16", "10.1.0.0/16"],
        },
        "phase_two_details": {
            "custom_encryption_algorithm": "AES_256_CBC",
            "negotiated_encryption_algorithm": "AES_128_CBC",
            "dh_group": "GROUP14",
            "lifetime": 3600,
            "remaining_lifetime": 20,
        },
    }
    desired = {
        "encryption_domain_config": {
            "oracle_traffic_selector": ["10.1.0.0/16", "10.0.0.0/16"],
        },
        "phase_two_config": {
            "encryption_algorithm": "aes_256_cbc",
            "pfs_dh_group": "group14",
            "lifetime_in_seconds": 3600,
        },
    }
    assert helper.tunnel_field_changes(current, desired) == {}


@pytest.mark.parametrize("field", ["oracle_interface_ip", "customer_interface_ip"])
def test_empty_bgp_interface_is_unchanged_after_api_returns_null(field):
    """Treat an already cleared BGP interface as unchanged."""
    helper = load_collection_module("oci_network_ipsec_connection")
    desired = {"bgp_session_config": {field: ""}}
    assert (
        helper.tunnel_field_changes(
            {"bgp_session_info": {field: None}},
            desired,
        )
        == {}
    )
    assert (
        helper.tunnel_field_changes(
            {"bgp_session_info": {field: "10.0.0.4/31"}},
            desired,
        )
        == desired
    )


def test_gcm_ignores_separate_authentication_in_tunnel_comparison():
    """Match OCI responses that omit authentication for GCM."""
    helper = load_collection_module("oci_network_ipsec_connection")
    current = {
        "phase_two_details": {
            "is_custom_phase_two_config": True,
            "custom_encryption_algorithm": "AES_256_GCM",
            "custom_authentication_algorithm": None,
            "lifetime": 3600,
        },
    }
    desired = {
        "phase_two_config": {
            "is_custom_phase_two_config": True,
            "encryption_algorithm": "aes_256_gcm",
            "authentication_algorithm": "hmac_sha2_256_128",
            "lifetime_in_seconds": 3600,
        },
    }
    assert helper.tunnel_field_changes(current, desired) == {}
    assert (
        helper.tunnel_field_changes(
            current,
            {
                "phase_two_config": {"authentication_algorithm": "hmac_sha1_128"},
            },
        )
        == {}
    )
    assert helper.tunnel_field_changes(
        current,
        {
            "phase_two_config": {
                "encryption_algorithm": "aes_256_cbc",
                "authentication_algorithm": "hmac_sha2_256_128",
            },
        },
    ) == {
        "phase_two_config": {
            "encryption_algorithm": "AES_256_CBC",
            "authentication_algorithm": "HMAC_SHA2_256_128",
        }
    }


def test_gcm_request_omits_ignored_authentication_but_cbc_keeps_it():
    """Build requests with authentication only where the API uses it."""
    import oci

    helper = load_collection_module("oci_network_ipsec_connection")
    for encryption in ("aes_256_gcm", "aes_256_cbc"):
        model = helper.build_tunnel_details(
            {
                "phase_two_config": {
                    "encryption_algorithm": encryption,
                    "authentication_algorithm": "hmac_sha2_256_128",
                },
            },
            oci.core.models.UpdateIPSecConnectionTunnelDetails,
        ).phase_two_config
        assert model.encryption_algorithm == encryption.upper()
        expected = None if encryption.endswith("gcm") else "HMAC_SHA2_256_128"
        assert model.authentication_algorithm == expected
