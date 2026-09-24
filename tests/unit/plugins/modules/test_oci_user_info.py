from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from .conftest import (
    DummyModule,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)


def load_user_info_module(monkeypatch):
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_user_info")


def test_main_contract_uses_domain_and_scim_filters(monkeypatch):
    module_obj = load_user_info_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciUserInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["domain_id", "domain_url"]]
    assert set(("user_id", "user_name", "name", "active")) <= set(
        captured["argument_spec"]
    )


def test_get_and_combined_list_filters_with_serialization(monkeypatch):
    module_obj = load_user_info_module(monkeypatch)
    user = FakeModel(
        id="user1",
        user_name="alice",
        display_name="Alice",
        name=FakeModel(given_name="Alice", family_name="Example"),
        emails=[FakeModel(value="alice@example.com", type="work", primary=True)],
    )
    client = types.SimpleNamespace(get_user=object(), list_users=object())
    instance = make_module_instance(
        module_obj,
        "OciUserInfoModule",
        {"user_id": "user1"},
        client=client,
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id, method, **kwargs: [user],
    )
    assert instance.fetch_resources() == [user]
    assert instance.serialize_result_resource(user)["email"] == "alice@example.com"
    assert instance.serialize_result_resource(user)["name"] == "Alice"

    instance.module.params = {
        "user_name": 'alice"ops',
        "name": "Alice",
        "active": False,
    }
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [user],
    )
    assert instance.fetch_resources() == [user]
    assert calls[0][1]["filter"] == (
        'userName eq "alice\\"ops" and displayName eq "Alice" and active eq false'
    )


def test_scim_list_envelopes_are_paginated(monkeypatch):
    module_obj = load_user_info_module(monkeypatch)
    instance = make_module_instance(module_obj, "OciUserInfoModule", {})
    responses = iter(
        [
            FakeResponse(FakeModel(resources=["first"]), {"opc-next-page": "page2"}),
            FakeResponse(FakeModel(resources=["second"])),
        ]
    )
    calls = []
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda method, **kwargs: calls.append(kwargs) or next(responses),
    )
    assert instance.list_all_resources(object()) == ["first", "second"]
    assert calls == [{}, {"page": "page2"}]
