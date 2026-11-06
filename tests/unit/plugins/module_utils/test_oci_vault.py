from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import types

import pytest

from .conftest import load_collection_module

ENDPOINT = "https://abc-management.kms.us-ashburn-1.oraclecloud.com"
VAULT_ID = "ocid1.vault.oc1..example"


class FakeKmsManagementClient:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class FakeKmsVaultClient:
    pass


class FailJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class FakeResponse:
    def __init__(self, data):
        self.data = data


class DummyModule:
    def __init__(self, params):
        self.params = params

    def fail_json(self, **kwargs):
        raise FailJsonCalled(kwargs)


def load_oci_vault(monkeypatch):
    oci_module = types.ModuleType("oci")
    oci_module.exceptions = types.ModuleType("oci.exceptions")
    oci_module.retry = types.SimpleNamespace(
        DEFAULT_RETRY_STRATEGY=types.SimpleNamespace(
            make_retrying_call=lambda fn, *args, **kwargs: fn(*args, **kwargs)
        )
    )
    oci_module.key_management = types.SimpleNamespace(
        KmsManagementClient=FakeKmsManagementClient,
        KmsVaultClient=FakeKmsVaultClient,
    )
    monkeypatch.setitem(sys.modules, "oci", oci_module)
    monkeypatch.setitem(sys.modules, "oci.exceptions", oci_module.exceptions)
    return load_collection_module("oci_vault")


def forbid_service_client(*args, **kwargs):
    raise AssertionError("a vault client must not be created")


def test_endpoint_args_and_constraints(monkeypatch):
    vault = load_oci_vault(monkeypatch)

    assert vault.OCI_VAULT_ENDPOINT_ARGS == {
        "vault_id": {"type": "str"},
        "management_endpoint": {"type": "str"},
    }
    assert vault.OCI_VAULT_ENDPOINT_REQUIRED_ONE_OF == [["vault_id", "management_endpoint"]]
    assert vault.OCI_VAULT_ENDPOINT_MUTUALLY_EXCLUSIVE == [["vault_id", "management_endpoint"]]


def test_resolve_explicit_endpoint_strips_trailing_slash(monkeypatch):
    vault = load_oci_vault(monkeypatch)
    monkeypatch.setattr(vault, "create_service_client", forbid_service_client)
    module = DummyModule({"management_endpoint": ENDPOINT + "/", "vault_id": None})

    assert vault.resolve_management_endpoint(module) == ENDPOINT


def test_resolve_endpoint_from_vault_id(monkeypatch):
    vault = load_oci_vault(monkeypatch)
    get_calls = []
    created = []

    def get_vault(vault_id):
        get_calls.append(vault_id)
        return FakeResponse(types.SimpleNamespace(management_endpoint=ENDPOINT + "/"))

    def create_service_client(module, client_class):
        created.append(client_class)
        return types.SimpleNamespace(get_vault=get_vault)

    monkeypatch.setattr(vault, "create_service_client", create_service_client)
    module = DummyModule({"management_endpoint": None, "vault_id": VAULT_ID})

    assert vault.resolve_management_endpoint(module) == ENDPOINT
    assert get_calls == [VAULT_ID]
    assert created == [FakeKmsVaultClient]


def test_resolve_endpoint_fails_when_vault_has_no_endpoint(monkeypatch):
    vault = load_oci_vault(monkeypatch)
    monkeypatch.setattr(
        vault,
        "create_service_client",
        lambda module, client_class: types.SimpleNamespace(
            get_vault=lambda vault_id: FakeResponse(
                types.SimpleNamespace(management_endpoint=None)
            )
        ),
    )
    module = DummyModule({"management_endpoint": None, "vault_id": VAULT_ID})

    with pytest.raises(FailJsonCalled) as exc_info:
        vault.resolve_management_endpoint(module)

    assert VAULT_ID in exc_info.value.payload["msg"]
    assert "management endpoint" in exc_info.value.payload["msg"]


def test_mixin_binds_client_class_to_resolved_endpoint(monkeypatch):
    vault = load_oci_vault(monkeypatch)
    monkeypatch.setattr(vault, "create_service_client", forbid_service_client)
    seen = {}

    class Base:
        def __init__(self, module):
            seen["module"] = module

    class Adapter(vault.OciVaultManagementMixin, Base):
        pass

    module = DummyModule({"management_endpoint": ENDPOINT})
    adapter = Adapter(module)

    assert seen["module"] is module
    assert adapter.management_endpoint == ENDPOINT
    client = adapter.client_class(config={}, signer=None)
    assert isinstance(client, FakeKmsManagementClient)
    assert client.kwargs == {"config": {}, "signer": None, "service_endpoint": ENDPOINT}


def test_mixin_fails_without_sdk(monkeypatch):
    vault = load_oci_vault(monkeypatch)
    monkeypatch.setattr(vault, "HAS_OCI_SDK", False)

    class Adapter(vault.OciVaultManagementMixin):
        pass

    with pytest.raises(FailJsonCalled) as exc_info:
        Adapter(DummyModule({"management_endpoint": ENDPOINT}))

    assert "oci" in exc_info.value.payload["msg"]
