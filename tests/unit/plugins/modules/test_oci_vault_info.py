from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from .conftest import (
    ExitJsonCalled,
    FakeModel,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)

VAULT_ID = "ocid1.vault.oc1..example"
COMPARTMENT_ID = "ocid1.compartment.oc1..example"


class FakeKmsVaultClientClass:
    pass


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.key_management = types.SimpleNamespace(
        KmsVaultClient=FakeKmsVaultClientClass,
        models=types.SimpleNamespace(),
    )
    return oci_module, service_error


def load_module():
    return load_collection_module("oci_vault_info")


def test_main_argument_spec(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_module()
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.params = {}

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciVaultInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    info_module.main()

    spec = captured["argument_spec"]
    for name in ("compartment_id", "vault_id", "name"):
        assert spec[name] == {"type": "str"}
    assert "auth_type" in spec
    assert captured["supports_check_mode"] is True
    assert captured["required_one_of"] == [["compartment_id", "vault_id"]]


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_module()
    cls = info_module.OciVaultInfoModule
    instance = make_module_instance(info_module, "OciVaultInfoModule", {})

    assert instance.client_class is FakeKmsVaultClientClass
    assert cls.results_key == "vaults"
    assert cls.resource_id_param == "vault_id"
    assert cls.resource_get_method == "get_vault"
    assert cls.list_resource_method == "list_vaults"
    assert cls.list_filter_params == ["compartment_id"]
    assert cls.name_filter_param == "name"


def test_fetch_resources_prefers_get_by_id(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_module()
    get_calls = []
    vault = FakeModel(id=VAULT_ID, display_name="example-vault")

    def get_vault(vault_id):
        get_calls.append(vault_id)
        return types.SimpleNamespace(data=vault)

    instance = make_module_instance(
        info_module,
        "OciVaultInfoModule",
        {"vault_id": VAULT_ID, "compartment_id": COMPARTMENT_ID},
        client=types.SimpleNamespace(get_vault=get_vault),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [vault]
    assert get_calls == [VAULT_ID]


def test_fetch_resources_returns_empty_when_vault_not_found(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_module()

    class NotFound(Exception):
        status = 404

    def missing_vault(vault_id):
        raise NotFound()

    instance = make_module_instance(
        info_module,
        "OciVaultInfoModule",
        {"vault_id": VAULT_ID},
        client=types.SimpleNamespace(get_vault=missing_vault),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == []


def test_fetch_resources_lists_and_filters_by_name(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_module()
    wanted = FakeModel(id=VAULT_ID, display_name="wanted")
    other = FakeModel(id="ocid1.vault.oc1..other", display_name="other")
    list_calls = []

    def list_vaults(**kwargs):
        list_calls.append(kwargs)
        return [wanted, other]

    instance = make_module_instance(
        info_module,
        "OciVaultInfoModule",
        {"compartment_id": COMPARTMENT_ID, "name": "wanted", "vault_id": None},
        client=types.SimpleNamespace(list_vaults=list_vaults),
    )
    monkeypatch.setattr(instance, "list_all_resources", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [wanted]
    assert list_calls == [{"compartment_id": COMPARTMENT_ID}]


def test_execute_info_module_exits_with_serialized_vaults(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_module()
    instance = make_module_instance(
        info_module,
        "OciVaultInfoModule",
        {"compartment_id": COMPARTMENT_ID},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(id=VAULT_ID, display_name="example-vault")],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    payload = exc_info.value.payload
    assert payload["changed"] is False
    assert payload["vaults"] == [{"id": VAULT_ID, "name": "example-vault"}]
