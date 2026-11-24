from __future__ import absolute_import, division, print_function
__metaclass__ = type

import base64
import types

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
OTHER_SECRET_ID = "ocid1.vaultsecret.oc1..other"
COMPARTMENT_ID = "ocid1.compartment.oc1..example"
VAULT_ID = "ocid1.vault.oc1..example"


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
    return load_collection_module("oci_vault_secret_info")


def b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class NotFound(Exception):
    status = 404


class FakeSecretsClient:
    """Serve secret bundles keyed by (secret_id, stage) and record the calls."""

    def __init__(self, bundles):
        self.bundles = bundles
        self.calls = []

    def get_secret_bundle(self, secret_id, **selector):
        self.calls.append((secret_id, selector))
        key = (secret_id, selector.get("stage"))
        if key not in self.bundles:
            raise NotFound()
        return FakeResponse(
            FakeModel(secret_bundle_content=FakeModel(content=self.bundles[key]))
        )


def make_secret(secret_id=SECRET_ID, state="ACTIVE", **overrides):
    fields = dict(
        id=secret_id,
        secret_name="example-secret",
        compartment_id=COMPARTMENT_ID,
        vault_id=VAULT_ID,
        lifecycle_state=state,
    )
    fields.update(overrides)
    return FakeModel(**fields)


def make_instance(module_obj, params, client=None, secrets_client=None):
    full_params = {
        "secret_id": None,
        "compartment_id": None,
        "vault_id": None,
        "name": None,
        "lifecycle_state": None,
        "include_content": False,
        "content_encoding": "text",
        "content_stage": "CURRENT",
    }
    full_params.update(params)
    instance = make_module_instance(
        module_obj,
        "OciVaultSecretInfoModule",
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


def capture_main_kwargs(monkeypatch, module_obj, params=None):
    captured = {}

    class FakeAnsibleModule:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.params = params if params is not None else {}

        def deprecate(self, *args, **kwargs):
            raise AssertionError("unexpected deprecation")

    monkeypatch.setattr(module_obj, "AnsibleModule", FakeAnsibleModule)
    monkeypatch.setattr(
        module_obj,
        "OciVaultSecretInfoModule",
        lambda module: types.SimpleNamespace(execute_info_module=lambda: None),
    )
    module_obj.main()
    return captured


def test_main_argument_spec(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    captured = capture_main_kwargs(monkeypatch, module_obj)
    spec = captured["argument_spec"]

    for name in ("secret_id", "compartment_id", "vault_id", "name"):
        assert spec[name] == {"type": "str"}
    assert spec["lifecycle_state"] == {
        "type": "str",
        "choices": [
            "creating",
            "active",
            "updating",
            "deleting",
            "deleted",
            "scheduling_deletion",
            "pending_deletion",
            "cancelling_deletion",
            "failed",
        ],
    }
    assert spec["include_content"] == {"type": "bool", "default": False}
    assert spec["content_encoding"] == {
        "type": "str",
        "choices": ["text", "base64"],
        "default": "text",
    }
    assert spec["content_stage"] == {
        "type": "str",
        "choices": ["current", "pending", "latest", "previous", "deprecated"],
        "default": "current",
    }
    assert "auth_type" in spec
    assert captured["supports_check_mode"] is True
    assert captured["required_one_of"] == [["compartment_id", "secret_id"]]


def test_main_normalizes_choices_to_oci_values(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    params = {
        "lifecycle_state": "pending_deletion",
        "content_stage": "previous",
        "content_encoding": "base64",
    }

    capture_main_kwargs(monkeypatch, module_obj, params)

    assert params == {
        "lifecycle_state": "PENDING_DELETION",
        "content_stage": "PREVIOUS",
        "content_encoding": "base64",
    }


def test_choice_value_maps_are_lowercase_only(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    for value_map in module_obj.CHOICE_VALUE_MAPS.values():
        assert all(name == name.lower() for name in value_map)
        assert not set(value_map) & set(value_map.values())


def test_class_metadata(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    cls = module_obj.OciVaultSecretInfoModule
    mixin = module_obj.OciSecretContentInfoMixin

    assert cls.__mro__.index(mixin) < cls.__mro__.index(module_obj.OciInfoBase)
    assert cls.client_class.fget(None) is module_obj.oci.vault.VaultsClient
    assert cls.results_key == "vault_secrets"
    assert cls.resource_id_param == "secret_id"
    assert cls.resource_get_method == "get_secret"
    assert cls.list_resource_method == "list_secrets"
    assert cls.list_filter_params == ["compartment_id", "vault_id", "lifecycle_state"]
    assert cls.name_response_field == "secret_name"
    assert cls.field_param_aliases == {"secret_name": "name"}


def test_fetch_resources_gets_secret_by_id(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    secret = make_secret()
    get_calls = []

    def get_secret(secret_id):
        get_calls.append(secret_id)
        return FakeResponse(secret)

    instance = make_instance(
        module_obj,
        {"secret_id": SECRET_ID, "compartment_id": COMPARTMENT_ID},
        client=types.SimpleNamespace(get_secret=get_secret),
    )

    assert instance.fetch_resources() == [secret]
    assert get_calls == [SECRET_ID]


def test_fetch_resources_returns_empty_when_secret_not_found(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    def missing_secret(secret_id):
        raise NotFound()

    instance = make_instance(
        module_obj,
        {"secret_id": SECRET_ID},
        client=types.SimpleNamespace(get_secret=missing_secret),
    )

    assert instance.fetch_resources() == []


def test_fetch_resources_reraises_other_service_errors(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    class Forbidden(Exception):
        status = 403

    def forbidden(secret_id):
        raise Forbidden()

    instance = make_instance(
        module_obj,
        {"secret_id": SECRET_ID},
        client=types.SimpleNamespace(get_secret=forbidden),
    )

    with pytest.raises(Forbidden):
        instance.fetch_resources()


def test_fetch_resources_lists_with_filters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    secrets = [make_secret()]
    list_calls = []

    def list_secrets(**kwargs):
        list_calls.append(kwargs)
        return secrets

    instance = make_instance(
        module_obj,
        {
            "compartment_id": COMPARTMENT_ID,
            "vault_id": VAULT_ID,
            "lifecycle_state": "ACTIVE",
        },
        client=types.SimpleNamespace(list_secrets=list_secrets),
    )

    assert instance.fetch_resources() == secrets
    assert list_calls == [
        {
            "compartment_id": COMPARTMENT_ID,
            "vault_id": VAULT_ID,
            "lifecycle_state": "ACTIVE",
        }
    ]


def test_fetch_resources_omits_unset_list_filters(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    list_calls = []

    def list_secrets(**kwargs):
        list_calls.append(kwargs)
        return []

    instance = make_instance(
        module_obj,
        {"compartment_id": COMPARTMENT_ID},
        client=types.SimpleNamespace(list_secrets=list_secrets),
    )

    assert instance.fetch_resources() == []
    assert list_calls == [{"compartment_id": COMPARTMENT_ID}]


def test_fetch_resources_filters_listed_secrets_by_name(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    wanted = make_secret(secret_name="wanted")
    other = make_secret(OTHER_SECRET_ID, secret_name="other")
    instance = make_instance(
        module_obj,
        {"compartment_id": COMPARTMENT_ID, "name": "wanted"},
        client=types.SimpleNamespace(list_secrets=lambda **kwargs: [wanted, other]),
    )

    assert instance.fetch_resources() == [wanted]


def test_execute_info_module_renames_name_and_skips_content_by_default(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    instance = make_instance(
        module_obj,
        {"compartment_id": COMPARTMENT_ID},
        client=types.SimpleNamespace(list_secrets=lambda **kwargs: [make_secret()]),
    )
    monkeypatch.setattr(
        type(instance),
        "secrets_client",
        property(lambda self: pytest.fail("the secrets client must not be created")),
    )

    payload = run_info(instance)

    assert payload["changed"] is False
    assert payload["vault_secrets"] == [
        {
            "id": SECRET_ID,
            "name": "example-secret",
            "compartment_id": COMPARTMENT_ID,
            "vault_id": VAULT_ID,
            "lifecycle_state": "ACTIVE",
        }
    ]


def test_execute_info_module_returns_empty_list_without_matches(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    instance = make_instance(
        module_obj,
        {"include_content": True, "compartment_id": COMPARTMENT_ID},
        client=types.SimpleNamespace(list_secrets=lambda **kwargs: []),
    )

    assert run_info(instance)["vault_secrets"] == []


def test_include_content_returns_decoded_text_of_current_stage(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    secrets_client = FakeSecretsClient({(SECRET_ID, "CURRENT"): b64("pässword")})
    instance = make_instance(
        module_obj,
        {"secret_id": SECRET_ID, "include_content": True},
        client=types.SimpleNamespace(
            get_secret=lambda secret_id: FakeResponse(make_secret())
        ),
        secrets_client=secrets_client,
    )

    payload = run_info(instance)

    assert payload["vault_secrets"][0]["content"] == "pässword"
    assert secrets_client.calls == [(SECRET_ID, {"stage": "CURRENT"})]


def test_include_content_base64_returns_stored_content(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    binary = base64.b64encode(b"\xff\xfe\x00").decode("ascii")
    secrets_client = FakeSecretsClient({(SECRET_ID, "PENDING"): binary})
    instance = make_instance(
        module_obj,
        {
            "secret_id": SECRET_ID,
            "include_content": True,
            "content_encoding": "base64",
            "content_stage": "PENDING",
        },
        client=types.SimpleNamespace(
            get_secret=lambda secret_id: FakeResponse(make_secret())
        ),
        secrets_client=secrets_client,
    )

    payload = run_info(instance)

    assert payload["vault_secrets"][0]["content"] == binary
    assert secrets_client.calls == [(SECRET_ID, {"stage": "PENDING"})]


def test_include_content_text_fails_for_non_utf8_content(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    binary = base64.b64encode(b"\xff\xfe\x00").decode("ascii")
    instance = make_instance(
        module_obj,
        {"secret_id": SECRET_ID, "include_content": True},
        client=types.SimpleNamespace(
            get_secret=lambda secret_id: FakeResponse(make_secret())
        ),
        secrets_client=FakeSecretsClient({(SECRET_ID, "CURRENT"): binary}),
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        instance.execute_info_module()

    assert "content_encoding=base64" in exc_info.value.payload["msg"]


def test_include_content_only_reads_active_secrets(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    secrets = [
        make_secret(SECRET_ID, secret_name="active"),
        make_secret(OTHER_SECRET_ID, state="PENDING_DELETION", secret_name="pending"),
        make_secret("ocid1.vaultsecret.oc1..third", secret_name="third"),
    ]
    secrets_client = FakeSecretsClient(
        {
            (SECRET_ID, "CURRENT"): b64("one"),
            ("ocid1.vaultsecret.oc1..third", "CURRENT"): b64("three"),
            (OTHER_SECRET_ID, "CURRENT"): b64("never read"),
        }
    )
    instance = make_instance(
        module_obj,
        {"compartment_id": COMPARTMENT_ID, "include_content": True},
        client=types.SimpleNamespace(list_secrets=lambda **kwargs: secrets),
        secrets_client=secrets_client,
    )

    payload = run_info(instance)

    assert [secret["content"] for secret in payload["vault_secrets"]] == [
        "one",
        None,
        "three",
    ]
    assert sorted(call[0] for call in secrets_client.calls) == sorted(
        [SECRET_ID, "ocid1.vaultsecret.oc1..third"]
    )


def test_include_content_is_null_when_stage_has_no_version(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    instance = make_instance(
        module_obj,
        {"secret_id": SECRET_ID, "include_content": True, "content_stage": "PENDING"},
        client=types.SimpleNamespace(
            get_secret=lambda secret_id: FakeResponse(make_secret())
        ),
        secrets_client=FakeSecretsClient({(SECRET_ID, "CURRENT"): b64("one")}),
    )

    assert run_info(instance)["vault_secrets"][0]["content"] is None


def test_include_content_creates_no_client_when_no_secret_is_active(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    instance = make_instance(
        module_obj,
        {"compartment_id": COMPARTMENT_ID, "include_content": True},
        client=types.SimpleNamespace(
            list_secrets=lambda **kwargs: [make_secret(state="PENDING_DELETION")]
        ),
    )
    monkeypatch.setattr(
        type(instance),
        "secrets_client",
        property(lambda self: pytest.fail("the secrets client must not be created")),
    )

    assert run_info(instance)["vault_secrets"][0]["content"] is None


def test_include_content_propagates_non_404_errors(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()

    class Forbidden(Exception):
        status = 403

    class DeniedSecretsClient:
        def get_secret_bundle(self, secret_id, **selector):
            raise Forbidden()

    instance = make_instance(
        module_obj,
        {"secret_id": SECRET_ID, "include_content": True},
        client=types.SimpleNamespace(
            get_secret=lambda secret_id: FakeResponse(make_secret())
        ),
        secrets_client=DeniedSecretsClient(),
    )

    with pytest.raises(Forbidden):
        instance.execute_info_module()
