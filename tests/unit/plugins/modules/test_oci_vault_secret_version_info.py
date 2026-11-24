from __future__ import absolute_import, division, print_function
__metaclass__ = type

import base64
import types
from datetime import datetime, timezone

import pytest

from .conftest import (
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
)

SECRET_ID = "ocid1.vaultsecret.oc1..example"


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    oci_module.vault = types.SimpleNamespace(
        VaultsClient=type("FakeVaultsClient", (), {}),
        models=types.SimpleNamespace(),
    )
    oci_module.secrets = types.SimpleNamespace(
        SecretsClient=type("FakeSecretsClient", (), {}),
    )
    return oci_module, service_error


def load_module():
    return load_collection_module("oci_vault_secret_version_info")


def b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class NotFound(Exception):
    status = 404


class FakeSecretsClient:
    """Serve secret bundles keyed by version number and record the calls."""

    def __init__(self, bundles):
        self.bundles = bundles
        self.calls = []

    def get_secret_bundle(self, secret_id, **selector):
        self.calls.append((secret_id, selector))
        version_number = selector["version_number"]
        if version_number not in self.bundles:
            raise NotFound()
        return FakeResponse(
            FakeModel(
                secret_bundle_content=FakeModel(content=self.bundles[version_number])
            )
        )


def make_version(version_number=1, name=None, time_of_deletion=None, **overrides):
    fields = dict(
        secret_id=SECRET_ID,
        version_number=version_number,
        name=name,
        stages=["DEPRECATED"],
        time_of_deletion=time_of_deletion,
    )
    fields.update(overrides)
    return FakeModel(**fields)


def make_instance(module_obj, params, client=None, secrets_client=None):
    full_params = {
        "secret_id": SECRET_ID,
        "version_number": None,
        "name": None,
        "include_content": False,
        "content_encoding": "text",
    }
    full_params.update(params)
    instance = make_module_instance(
        module_obj,
        "OciVaultSecretVersionInfoModule",
        full_params,
        client=client,
        _secrets_client=secrets_client,
    )
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    instance.list_all_resources = lambda fn, **kwargs: fn(**kwargs)
    return instance


def run_info(instance):
    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()
    return exc_info.value.payload


def capture_main_kwargs(monkeypatch, module_obj):
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.params = {}

    monkeypatch.setattr(module_obj, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        module_obj,
        "OciVaultSecretVersionInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    return captured


def test_main_argument_spec(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    captured = capture_main_kwargs(monkeypatch, module_obj)
    spec = captured["argument_spec"]

    assert spec["secret_id"] == {"type": "str", "required": True}
    assert spec["version_number"] == {"type": "int"}
    assert spec["name"] == {"type": "str"}
    assert spec["include_content"] == {"type": "bool", "default": False}
    assert spec["content_encoding"] == {
        "type": "str",
        "choices": ["text", "base64"],
        "default": "text",
    }
    assert "auth_type" in spec
    assert captured["supports_check_mode"] is True


def test_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    cls = module_obj.OciVaultSecretVersionInfoModule
    mixin = module_obj.OciSecretContentInfoMixin

    assert cls.__mro__.index(mixin) < cls.__mro__.index(module_obj.OciInfoBase)
    assert cls.client_class.fget(None) is module_obj.oci.vault.VaultsClient
    assert cls.results_key == "secret_versions"
    assert cls.resource_id_param == "version_number"
    assert cls.resource_id_kwarg == "secret_version_number"
    assert cls.resource_get_method == "get_secret_version"
    assert cls.list_resource_method == "list_secret_versions"
    assert cls.list_filter_params == ["secret_id"]
    assert cls.name_filter_param == "name"
    assert cls.name_response_field == "name"


def test_fetch_resources_gets_version_in_its_secret(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    version = make_version(2)
    get_calls = []

    def get_secret_version(secret_id, secret_version_number):
        get_calls.append((secret_id, secret_version_number))
        return FakeResponse(version)

    instance = make_instance(
        module_obj,
        {"version_number": 2, "name": "ignored"},
        client=types.SimpleNamespace(get_secret_version=get_secret_version),
    )

    assert instance.fetch_resources() == [version]
    assert get_calls == [(SECRET_ID, 2)]


def test_fetch_resources_returns_empty_when_version_not_found(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    def missing_version(secret_id, secret_version_number):
        raise NotFound()

    instance = make_instance(
        module_obj,
        {"version_number": 9},
        client=types.SimpleNamespace(get_secret_version=missing_version),
    )

    assert instance.fetch_resources() == []


def test_fetch_resources_reraises_other_service_errors(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    class Forbidden(Exception):
        status = 403

    def forbidden(secret_id, secret_version_number):
        raise Forbidden()

    instance = make_instance(
        module_obj,
        {"version_number": 1},
        client=types.SimpleNamespace(get_secret_version=forbidden),
    )

    with pytest.raises(Forbidden):
        instance.fetch_resources()


def test_fetch_resources_lists_versions_of_the_secret(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    versions = [make_version(1), make_version(2)]
    list_calls = []

    def list_secret_versions(**kwargs):
        list_calls.append(kwargs)
        return versions

    instance = make_instance(
        module_obj,
        {},
        client=types.SimpleNamespace(list_secret_versions=list_secret_versions),
    )

    assert instance.fetch_resources() == versions
    assert list_calls == [{"secret_id": SECRET_ID}]


def test_fetch_resources_filters_listed_versions_by_name(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    wanted = make_version(2, name="wanted")
    other = make_version(1, name="other")
    instance = make_instance(
        module_obj,
        {"name": "wanted"},
        client=types.SimpleNamespace(
            list_secret_versions=lambda **kwargs: [other, wanted]
        ),
    )

    assert instance.fetch_resources() == [wanted]


def test_execute_info_module_serializes_versions_without_content(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    created = datetime(2026, 1, 1, tzinfo=timezone.utc)
    instance = make_instance(
        module_obj,
        {},
        client=types.SimpleNamespace(
            list_secret_versions=lambda **kwargs: [
                make_version(1, name="first", time_created=created)
            ]
        ),
    )
    monkeypatch.setattr(
        type(instance),
        "secrets_client",
        property(lambda self: pytest.fail("the secrets client must not be created")),
    )

    payload = run_info(instance)

    assert payload["changed"] is False
    assert payload["secret_versions"] == [
        {
            "secret_id": SECRET_ID,
            "version_number": 1,
            "name": "first",
            "stages": ["DEPRECATED"],
            "time_of_deletion": None,
            "time_created": created,
        }
    ]


def test_include_content_reads_every_readable_version(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    secrets_client = FakeSecretsClient({1: b64("one"), 2: b64("tw\u00f6")})
    instance = make_instance(
        module_obj,
        {"include_content": True},
        client=types.SimpleNamespace(
            list_secret_versions=lambda **kwargs: [make_version(1), make_version(2)]
        ),
        secrets_client=secrets_client,
    )

    payload = run_info(instance)

    assert [version["content"] for version in payload["secret_versions"]] == [
        "one",
        "tw\u00f6",
    ]
    assert sorted(secrets_client.calls, key=lambda call: call[1]["version_number"]) == [
        (SECRET_ID, {"version_number": 1}),
        (SECRET_ID, {"version_number": 2}),
    ]


def test_include_content_base64_returns_stored_content(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    binary = base64.b64encode(b"\xff\xfe\x00").decode("ascii")
    instance = make_instance(
        module_obj,
        {"version_number": 1, "include_content": True, "content_encoding": "base64"},
        client=types.SimpleNamespace(
            get_secret_version=lambda secret_id, secret_version_number: FakeResponse(
                make_version(1)
            )
        ),
        secrets_client=FakeSecretsClient({1: binary}),
    )

    assert run_info(instance)["secret_versions"][0]["content"] == binary


def test_include_content_text_fails_for_non_utf8_content(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    binary = base64.b64encode(b"\xff\xfe\x00").decode("ascii")
    instance = make_instance(
        module_obj,
        {"version_number": 1, "include_content": True},
        client=types.SimpleNamespace(
            get_secret_version=lambda secret_id, secret_version_number: FakeResponse(
                make_version(1)
            )
        ),
        secrets_client=FakeSecretsClient({1: binary}),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_info_module()

    assert "content_encoding=base64" in exc_info.value.payload["msg"]


def test_include_content_skips_versions_scheduled_for_deletion(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    scheduled = make_version(
        2, time_of_deletion=datetime(2026, 2, 1, tzinfo=timezone.utc)
    )
    secrets_client = FakeSecretsClient({1: b64("one"), 2: b64("never read")})
    instance = make_instance(
        module_obj,
        {"include_content": True},
        client=types.SimpleNamespace(
            list_secret_versions=lambda **kwargs: [make_version(1), scheduled]
        ),
        secrets_client=secrets_client,
    )

    payload = run_info(instance)

    assert [version["content"] for version in payload["secret_versions"]] == [
        "one",
        None,
    ]
    assert secrets_client.calls == [(SECRET_ID, {"version_number": 1})]


def test_include_content_creates_no_client_when_no_version_is_readable(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    scheduled = make_version(
        1, time_of_deletion=datetime(2026, 2, 1, tzinfo=timezone.utc)
    )
    instance = make_instance(
        module_obj,
        {"include_content": True},
        client=types.SimpleNamespace(list_secret_versions=lambda **kwargs: [scheduled]),
    )
    monkeypatch.setattr(
        type(instance),
        "secrets_client",
        property(lambda self: pytest.fail("the secrets client must not be created")),
    )

    assert run_info(instance)["secret_versions"][0]["content"] is None


def test_include_content_is_null_when_bundle_is_missing(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    instance = make_instance(
        module_obj,
        {"include_content": True},
        client=types.SimpleNamespace(
            list_secret_versions=lambda **kwargs: [make_version(1)]
        ),
        secrets_client=FakeSecretsClient({}),
    )

    assert run_info(instance)["secret_versions"][0]["content"] is None
