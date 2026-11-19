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

KEY_ID = "ocid1.key.oc1..example"
COMPARTMENT_ID = "ocid1.compartment.oc1..example"


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.key_management = types.SimpleNamespace(
        KmsManagementClient=type("FakeKmsManagementClient", (), {}),
        KmsVaultClient=type("FakeKmsVaultClient", (), {}),
        models=types.SimpleNamespace(),
    )
    return oci_module, service_error


def capture_main_kwargs(monkeypatch, info_module, params=None):
    """Run ``main`` with a fake AnsibleModule and return its constructor kwargs."""
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.params = params if params is not None else {}

        def deprecate(self, *args, **kwargs):
            raise AssertionError("unexpected deprecation")

    monkeypatch.setattr(info_module, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        info_module,
        "OciVaultKeyInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    info_module.main()
    return captured


def test_main_argument_spec(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")

    captured = capture_main_kwargs(monkeypatch, info_module)
    spec = captured["argument_spec"]

    for name in ("vault_id", "management_endpoint", "compartment_id", "key_id", "name"):
        assert spec[name] == {"type": "str"}
    assert spec["protection_mode"] == {
        "type": "str",
        "choices": ["hsm", "software", "external"],
    }
    assert spec["algorithm"] == {"type": "str", "choices": ["aes", "rsa", "ecdsa"]}
    assert "auth_type" in spec
    assert captured["supports_check_mode"] is True


def test_main_required_one_of_and_mutually_exclusive(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")

    captured = capture_main_kwargs(monkeypatch, info_module)

    assert captured["required_one_of"] == [
        ["compartment_id", "key_id"],
        ["vault_id", "management_endpoint"],
    ]
    assert captured["mutually_exclusive"] == [["vault_id", "management_endpoint"]]


def test_main_normalizes_choices_to_oci_values(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")
    params = {"protection_mode": "software", "algorithm": "ecdsa"}

    capture_main_kwargs(monkeypatch, info_module, params)

    assert params == {"protection_mode": "SOFTWARE", "algorithm": "ECDSA"}


def test_choice_value_maps_are_lowercase_only(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")

    # The OCI SDK values must not be accepted as choices on this new module.
    for value_map in info_module.CHOICE_VALUE_MAPS.values():
        assert all(name == name.lower() for name in value_map)
        assert not set(value_map) & set(value_map.values())


def test_info_module_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")
    cls = info_module.OciVaultKeyInfoModule
    mixin = info_module.OciVaultManagementMixin

    assert issubclass(cls, mixin)
    assert cls.__mro__.index(mixin) < cls.__mro__.index(info_module.OciInfoBase)
    assert cls.results_key == "vault_keys"
    assert cls.resource_id_param == "key_id"
    assert cls.resource_get_method == "get_key"
    assert cls.list_resource_method == "list_keys"
    assert cls.list_filter_params == ["compartment_id", "protection_mode", "algorithm"]
    assert cls.name_filter_param == "name"
    assert cls.name_response_field == "display_name"


def test_fetch_resources_prefers_get_by_id(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")
    get_calls = []
    key = FakeModel(id=KEY_ID, display_name="example-key")

    def get_key(key_id):
        get_calls.append(key_id)
        return types.SimpleNamespace(data=key)

    instance = make_module_instance(
        info_module,
        "OciVaultKeyInfoModule",
        {"key_id": KEY_ID, "compartment_id": COMPARTMENT_ID},
        client=types.SimpleNamespace(get_key=get_key),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == [key]
    assert get_calls == [KEY_ID]


def test_fetch_resources_returns_empty_when_key_not_found(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")

    class NotFound(Exception):
        status = 404

    def missing_key(key_id):
        raise NotFound()

    instance = make_module_instance(
        info_module,
        "OciVaultKeyInfoModule",
        {"key_id": KEY_ID},
        client=types.SimpleNamespace(get_key=missing_key),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    assert instance.fetch_resources() == []


def test_fetch_resources_lists_with_filters(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")
    keys = [FakeModel(id=KEY_ID, display_name="example-key")]
    list_calls = []

    def list_keys(**kwargs):
        list_calls.append(kwargs)
        return keys

    instance = make_module_instance(
        info_module,
        "OciVaultKeyInfoModule",
        {
            "compartment_id": COMPARTMENT_ID,
            "protection_mode": "SOFTWARE",
            "algorithm": "AES",
            "name": None,
            "key_id": None,
        },
        client=types.SimpleNamespace(list_keys=list_keys),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == keys
    assert list_calls == [
        {
            "compartment_id": COMPARTMENT_ID,
            "protection_mode": "SOFTWARE",
            "algorithm": "AES",
        }
    ]


def test_fetch_resources_filters_listed_keys_by_name(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")
    wanted = FakeModel(id=KEY_ID, display_name="wanted")
    other = FakeModel(id="ocid1.key.oc1..other", display_name="other")
    instance = make_module_instance(
        info_module,
        "OciVaultKeyInfoModule",
        {"compartment_id": COMPARTMENT_ID, "name": "wanted"},
        client=types.SimpleNamespace(list_keys=lambda **kwargs: [wanted, other]),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == [wanted]


def test_execute_info_module_exits_with_serialized_keys(monkeypatch):
    install_fake_oci(monkeypatch)
    info_module = load_collection_module("oci_vault_key_info")
    instance = make_module_instance(
        info_module,
        "OciVaultKeyInfoModule",
        {"compartment_id": COMPARTMENT_ID},
    )
    monkeypatch.setattr(
        instance,
        "fetch_resources",
        lambda: [FakeModel(id=KEY_ID, display_name="example-key")],
    )

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    payload = exc_info.value.payload
    assert payload["changed"] is False
    assert payload["vault_keys"] == [{"id": KEY_ID, "name": "example-key"}]
