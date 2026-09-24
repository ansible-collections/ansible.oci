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


def load_group_info_module(monkeypatch):
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_group_info")


def test_main_contract_and_get_list_behaviour(monkeypatch):
    module_obj = load_group_info_module(monkeypatch)
    module_class = module_obj.OciGroupInfoModule
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciGroupInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [["domain_id", "domain_url"]]
    monkeypatch.setattr(module_obj, "OciGroupInfoModule", module_class)

    group = FakeModel(
        id="group1",
        ocid="ocid1.group.example",
        domain_ocid="ocid1.domain.example",
        display_name="admins",
        meta=FakeModel(created="created", last_modified="modified"),
        urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=FakeModel(
            freeform_tags=[FakeModel(key="team", value="iam")],
            defined_tags=[
                FakeModel(namespace="Operations", key="CostCenter", value="42")
            ],
        ),
    )
    client = types.SimpleNamespace(get_group=object(), list_groups=object())
    instance = make_module_instance(
        module_obj,
        "OciGroupInfoModule",
        {"group_id": "group1"},
        client=client,
    )
    monkeypatch.setattr(
        instance,
        "get_resource_by_id",
        lambda resource_id, method, **kwargs: [group],
    )
    assert instance.fetch_resources() == [group]
    serialized = instance.serialize_result_resource(group)
    assert serialized == {
        "id": "group1",
        "ocid": "ocid1.group.example",
        "domain_id": "ocid1.domain.example",
        "display_name": "admins",
        "freeform_tags": {"team": "iam"},
        "defined_tags": {"Operations": {"CostCenter": "42"}},
        "time_created": "created",
        "time_modified": "modified",
    }

    instance.module.params = {"display_name": 'admin"ops'}
    calls = []
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda method, **kwargs: calls.append((method, kwargs)) or [group],
    )
    assert instance.fetch_resources() == [group]
    assert calls == [
        (client.list_groups, {"filter": 'displayName eq "admin\\"ops"'})
    ]


def test_scim_list_envelopes_are_paginated(monkeypatch):
    module_obj = load_group_info_module(monkeypatch)
    instance = make_module_instance(module_obj, "OciGroupInfoModule", {})
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
