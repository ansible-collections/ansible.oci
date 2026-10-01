from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
import sys

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def load_membership_info_module(monkeypatch):
    install_fake_oci(monkeypatch)
    return load_collection_module("oci_identity_user_group_membership_info")


def test_main_requires_domain_and_at_least_one_side(monkeypatch):
    module_obj = load_membership_info_module(monkeypatch)
    captured = {}
    monkeypatch.setattr(
        module_obj,
        "AnsibleModule",
        lambda **kwargs: captured.update(kwargs) or DummyModule({}),
    )
    monkeypatch.setattr(
        module_obj,
        "OciIdentityUserGroupMembershipInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    assert captured["required_one_of"] == [
        ["domain_id", "domain_url"],
        ["user_id", "group_id"],
    ]
    assert captured["mutually_exclusive"] == [["domain_id", "domain_url"]]


def test_missing_oci_sdk_fails_before_domain_lookup(monkeypatch):
    module_obj = load_membership_info_module(monkeypatch)
    helper = sys.modules[module_obj.OciIdentityDomainsMixin.__module__]
    monkeypatch.setattr(helper, "HAS_OCI_SDK", False)
    monkeypatch.setattr(
        helper, "resolve_domain_url", lambda module: pytest.fail("unexpected lookup")
    )
    with pytest.raises(FailJsonCalled) as failure:
        module_obj.OciIdentityUserGroupMembershipInfoModule(DummyModule({"domain_id": "domain1"}))
    assert "oci" in failure.value.payload["msg"]


def test_group_and_pair_queries_include_members_and_handle_404(monkeypatch):
    module_obj = load_membership_info_module(monkeypatch)
    members = [FakeModel(value="user1"), FakeModel(value="user2")]
    calls = []
    client = types.SimpleNamespace(
        get_group=lambda **kwargs: calls.append(kwargs)
        or FakeResponse(FakeModel(members=members))
    )
    instance = make_module_instance(
        module_obj,
        "OciIdentityUserGroupMembershipInfoModule",
        {"group_id": "group1", "user_id": None},
        client=client,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    assert instance.fetch_resources() == members
    assert calls == [{"group_id": "group1", "attributes": "members"}]
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    assert [
        item["user_id"] for item in result.value.payload["user_group_memberships"]
    ] == ["user1", "user2"]

    instance.module.params["user_id"] = "user2"
    assert instance.fetch_resources() == [members[1]]
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    assert result.value.payload == {
        "changed": False,
        "user_group_memberships": [
            {
                "group_id": "group1",
                "user_id": "user2",
                "membership_ocid": None,
                "user_ocid": None,
                "display_name": None,
                "type": None,
                "date_added": None,
            }
        ],
    }

    error = RuntimeError("missing")
    error.status = 404
    client.get_group = raising(error)
    assert instance.fetch_resources() == []


def test_user_query_returns_direct_groups_and_info_output(monkeypatch):
    module_obj = load_membership_info_module(monkeypatch)
    groups = [
        FakeModel(
            value="group1",
            ocid="ocid1.group.example",
            type="direct",
            membership_ocid="membership1",
        ),
        FakeModel(value="group2", type="indirect", membership_ocid="membership2"),
    ]
    client = types.SimpleNamespace(
        get_user=lambda **kwargs: FakeResponse(FakeModel(groups=groups))
    )
    instance = make_module_instance(
        module_obj,
        "OciIdentityUserGroupMembershipInfoModule",
        {"user_id": "user1", "group_id": None},
        client=client,
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))
    assert instance.fetch_resources() == [groups[0]]
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_info_module()
    assert result.value.payload == {
        "changed": False,
        "user_group_memberships": [
            {
                "group_id": "group1",
                "user_id": "user1",
                "group_ocid": "ocid1.group.example",
                "membership_ocid": "membership1",
                "display_name": None,
                "type": "direct",
                "date_added": None,
            }
        ],
    }

    error = RuntimeError("missing")
    error.status = 404
    client.get_user = raising(error)
    assert instance.fetch_resources() == []
