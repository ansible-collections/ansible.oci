from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    DummyModule,
    FailJsonCalled,
    FakeModel,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def load_tag_info_module(monkeypatch):
    """Load the tag info module with fake OCI SDK models.

    Args:
        monkeypatch: Pytest fixture for temporary SDK module setup.

    Returns:
        The imported tag info module.
    """
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_identity_tag_info")


def test_main_declares_info_contract(monkeypatch):
    """Test main declares info contract behavior."""
    module_obj = load_tag_info_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityTagInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    spec = captured["argument_spec"]
    assert spec["tag_namespace_id"] == {"type": "str", "required": True}
    assert spec["lifecycle_state"]["choices"] == ["active", "inactive", "deleting", "deleted"]


def test_get_by_name_uses_namespace_and_preserves_name(monkeypatch):
    """Test get by name uses namespace and preserves name behavior."""
    module_obj = load_tag_info_module(monkeypatch)
    info = make_module_instance(
        module_obj,
        "OciIdentityTagInfoModule",
        {"tag_namespace_id": "ns1", "name": "MixedCase"},
        client=types.SimpleNamespace(get_tag=object()),
    )
    calls = []
    tag = FakeModel(name="MixedCase", validator=FakeModel(validator_type="ENUM", values=["A"]))
    monkeypatch.setattr(
        info,
        "get_resource_by_id",
        lambda name, method, **kwargs: calls.append((name, method, kwargs)) or [tag],
    )
    assert info.fetch_resources() == [tag]
    assert calls == [
        ("MixedCase", info.client.get_tag, {"tag_namespace_id": "ns1", "tag_name": "MixedCase"})
    ]
    assert info.serialize_result_resource(tag)["validator"]["values"] == ["A"]


def test_list_delegates_with_namespace_and_state_filters(monkeypatch):
    """Pass namespace and state filters to the shared list helper."""
    module_obj = load_tag_info_module(monkeypatch)
    client = types.SimpleNamespace(list_tags=object())
    info = make_module_instance(
        module_obj,
        "OciIdentityTagInfoModule",
        {"tag_namespace_id": "ns1", "lifecycle_state": "inactive"},
        client=client,
    )
    tags = [FakeModel(name="A"), FakeModel(name="B")]
    calls = []
    monkeypatch.setattr(
        info,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or tags,
    )
    assert info.fetch_resources() == tags
    assert calls == [(client.list_tags, {"tag_namespace_id": "ns1", "lifecycle_state": "INACTIVE"})]


def test_list_summaries_serialize_without_validator(monkeypatch):
    """Test list summaries serialize without validator behavior."""
    module_obj = load_tag_info_module(monkeypatch)
    info = make_module_instance(module_obj, "OciIdentityTagInfoModule", {})
    summary = FakeModel(name="Environment", lifecycle_state="ACTIVE", is_retired=False)
    result = info.serialize_result_resource(summary)
    assert result["name"] == "Environment"
    assert "validator" not in result


def test_get_404_returns_no_tags(monkeypatch):
    """Test get 404 returns no tags behavior."""
    module_obj, service_error = install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_identity_tag_info")
    client = types.SimpleNamespace(
        get_tag=lambda **kwargs: (item for item in ()).throw(service_error(404))
    )
    info = make_module_instance(
        module_obj,
        "OciIdentityTagInfoModule",
        {"tag_namespace_id": "ns1", "name": "Missing"},
        client=client,
    )
    info.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    assert info.fetch_resources() == []


def test_empty_name_fails_before_sdk_lookup(monkeypatch):
    """Reject an empty tag name before an SDK get operation."""
    module_obj = load_tag_info_module(monkeypatch)
    info = make_module_instance(
        module_obj,
        "OciIdentityTagInfoModule",
        {"tag_namespace_id": "ns1", "name": ""},
        client=types.SimpleNamespace(),
    )
    with pytest.raises(FailJsonCalled) as result:
        info.fetch_resources()
    assert result.value.payload["msg"] == "name must be nonempty"
