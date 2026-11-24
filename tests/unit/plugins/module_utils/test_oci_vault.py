from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import types
from datetime import datetime, timedelta, timezone

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


class FakeSecretsClient:
    pass


class FakeServiceError(Exception):
    def __init__(self, status):
        super().__init__(f"status {status}")
        self.status = status


def load_oci_vault_with_secrets(monkeypatch):
    vault = load_oci_vault(monkeypatch)
    sys.modules["oci"].secrets = types.SimpleNamespace(SecretsClient=FakeSecretsClient)
    return vault


@pytest.mark.parametrize("deletion_days", [None, 1, 7, 30])
def test_validate_deletion_days_accepts_values_in_range(monkeypatch, deletion_days):
    vault = load_oci_vault(monkeypatch)

    vault.validate_deletion_days(
        DummyModule({"deletion_days": deletion_days}), 1, 30
    )


@pytest.mark.parametrize(
    "deletion_days, min_days", [(0, 1), (31, 1), (1, 7), (6, 7), (-5, 1)]
)
def test_validate_deletion_days_rejects_values_out_of_range(
    monkeypatch, deletion_days, min_days
):
    vault = load_oci_vault(monkeypatch)

    with pytest.raises(FailJsonCalled) as exc_info:
        vault.validate_deletion_days(
            DummyModule({"deletion_days": deletion_days}), min_days, 30
        )

    assert f"between {min_days} and 30" in exc_info.value.payload["msg"]
    assert str(deletion_days) in exc_info.value.payload["msg"]


def test_build_deletion_schedule_without_days_uses_oci_default(monkeypatch):
    vault = load_oci_vault(monkeypatch)

    assert vault.build_deletion_schedule(None) == {}


def test_build_deletion_schedule_sets_an_aware_time_of_deletion(monkeypatch):
    vault = load_oci_vault(monkeypatch)
    before = datetime.now(timezone.utc)

    schedule = vault.build_deletion_schedule(3)

    after = datetime.now(timezone.utc)
    window = timedelta(days=3) + vault.DELETION_SCHEDULE_MARGIN
    assert set(schedule) == {"time_of_deletion"}
    assert before + window <= schedule["time_of_deletion"] <= after + window
    assert schedule["time_of_deletion"].tzinfo is not None


def test_build_deletion_schedule_caps_the_margin_at_the_maximum(monkeypatch):
    vault = load_oci_vault(monkeypatch)
    before = datetime.now(timezone.utc)

    schedule = vault.build_deletion_schedule(vault.MAX_DELETION_DAYS)

    after = datetime.now(timezone.utc)
    window = timedelta(days=vault.MAX_DELETION_DAYS)
    assert before + window <= schedule["time_of_deletion"] <= after + window


def test_scheduled_deletion_mixin_validates_against_its_own_window(monkeypatch):
    vault = load_oci_vault(monkeypatch)

    class Secrets(vault.OciScheduledDeletionMixin):
        min_deletion_days = vault.SECRET_MIN_DELETION_DAYS

    mixin = object.__new__(Secrets)
    mixin.module = DummyModule({"deletion_days": 1})
    assert vault.OciScheduledDeletionMixin.min_deletion_days == vault.MIN_DELETION_DAYS
    assert vault.OciScheduledDeletionMixin.max_deletion_days == vault.MAX_DELETION_DAYS
    assert mixin.build_deletion_schedule()["time_of_deletion"].tzinfo is not None

    mixin.module = DummyModule({"deletion_days": 0})
    with pytest.raises(FailJsonCalled) as exc_info:
        vault.validate_deletion_days(
            mixin.module, mixin.min_deletion_days, mixin.max_deletion_days
        )

    assert "between 1 and 30" in exc_info.value.payload["msg"]


def test_secret_content_to_bytes(monkeypatch):
    vault = load_oci_vault(monkeypatch)

    assert vault.secret_content_to_bytes("héllo", "text") == "héllo".encode("utf-8")
    assert vault.secret_content_to_bytes("AAEC", "base64") == b"\x00\x01\x02"
    with pytest.raises(ValueError):
        vault.secret_content_to_bytes("abc", "base64")


def test_encode_secret_content_returns_base64_of_the_raw_bytes(monkeypatch):
    vault = load_oci_vault(monkeypatch)

    assert vault.encode_secret_content("hello", "text") == "aGVsbG8="
    assert vault.encode_secret_content("AAEC", "base64") == "AAEC"
    assert vault.encode_secret_content("héllo", "text") == "aMOpbGxv"


def test_decode_secret_content_as_text_and_base64(monkeypatch):
    vault = load_oci_vault(monkeypatch)
    module = DummyModule({})

    assert vault.decode_secret_content(module, "aMOpbGxv", "text") == "héllo"
    assert vault.decode_secret_content(module, "AP8=", "base64") == "AP8="


def test_decode_secret_content_fails_for_non_utf8_text(monkeypatch):
    vault = load_oci_vault(monkeypatch)

    with pytest.raises(FailJsonCalled) as exc_info:
        vault.decode_secret_content(DummyModule({}), "AP8=", "text")

    assert "content_encoding=base64" in exc_info.value.payload["msg"]


def make_bundle_mixin(vault, response=None, error=None):
    calls = []

    def get_secret_bundle(**kwargs):
        calls.append(kwargs)
        if error is not None:
            raise error
        return response

    class Adapter(vault.OciSecretBundleMixin):
        def call_with_retry(self, fn, *args, **kwargs):
            return fn(*args, **kwargs)

    adapter = Adapter()
    adapter.module = DummyModule({})
    adapter._secrets_client = types.SimpleNamespace(get_secret_bundle=get_secret_bundle)
    adapter.calls = calls
    return adapter


def bundle_response(content):
    return FakeResponse(
        types.SimpleNamespace(
            secret_bundle_content=types.SimpleNamespace(content=content)
        )
    )


def test_secret_bundle_mixin_returns_content_for_the_selector(monkeypatch):
    vault = load_oci_vault_with_secrets(monkeypatch)
    adapter = make_bundle_mixin(vault, response=bundle_response("AAEC"))

    assert adapter.get_secret_bundle_content("secret-1", stage="PENDING") == "AAEC"
    assert adapter.get_secret_bundle_content("secret-1", version_number=2) == "AAEC"
    assert adapter.get_secret_bundle_content("secret-1") == "AAEC"
    assert adapter.calls == [
        {"secret_id": "secret-1", "stage": "PENDING"},
        {"secret_id": "secret-1", "version_number": 2},
        {"secret_id": "secret-1"},
    ]


def test_secret_bundle_mixin_returns_none_for_a_missing_version(monkeypatch):
    vault = load_oci_vault_with_secrets(monkeypatch)
    adapter = make_bundle_mixin(vault, error=FakeServiceError(404))

    assert adapter.get_secret_bundle_content("secret-1", stage="PENDING") is None


def test_secret_bundle_mixin_reraises_other_errors(monkeypatch):
    vault = load_oci_vault_with_secrets(monkeypatch)
    adapter = make_bundle_mixin(vault, error=FakeServiceError(403))

    with pytest.raises(FakeServiceError):
        adapter.get_secret_bundle_content("secret-1")


def test_secret_bundle_mixin_creates_its_client_lazily_once(monkeypatch):
    vault = load_oci_vault_with_secrets(monkeypatch)
    created = []

    def create_service_client(module, client_class):
        created.append((module, client_class))
        return types.SimpleNamespace(
            get_secret_bundle=lambda **kwargs: bundle_response("AAEC")
        )

    monkeypatch.setattr(vault, "create_service_client", create_service_client)

    class Adapter(vault.OciSecretBundleMixin):
        def call_with_retry(self, fn, *args, **kwargs):
            return fn(*args, **kwargs)

    adapter = Adapter()
    adapter.module = DummyModule({})

    assert created == []
    assert adapter.get_secret_bundle_content("secret-1") == "AAEC"
    assert adapter.get_secret_bundle_content("secret-1") == "AAEC"
    assert created == [(adapter.module, FakeSecretsClient)]


@pytest.fixture(autouse=True)
def restore_helper_module():
    """Keep the helper rebound to this file's fake SDK from leaking into other tests."""
    module_name = "ansible_collections.ansible.oci.plugins.module_utils.oci_vault"
    saved = sys.modules.get(module_name)
    yield
    if saved is None:
        sys.modules.pop(module_name, None)
    else:
        sys.modules[module_name] = saved
