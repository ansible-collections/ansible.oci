from __future__ import absolute_import, division, print_function
__metaclass__ = type

import base64
import sys
import types
from datetime import datetime, timedelta, timezone

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci as shared_install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


VAULT_ID = "ocid1.vault.oc1..example"
KEY_ID = "ocid1.key.oc1..example"
SECRET_ID = "ocid1.vaultsecret.oc1..example"
COMPARTMENT_ID = "ocid1.compartment.oc1..example"
SECRET_NAME = "example-secret"
HELPER_MODULE = "ansible_collections.ansible.oci.plugins.module_utils.oci_vault"

PLAIN_MODEL_NAMES = (
    "CreateSecretDetails",
    "UpdateSecretDetails",
    "Base64SecretContentDetails",
    "ScheduleSecretDeletionDetails",
)
STRICT_MODELS = {
    "SecretExpiryRule": (
        ("rule_type", "secret_version_expiry_interval", "time_of_absolute_expiry",
         "is_secret_content_retrieval_blocked_on_expiry"),
        {"rule_type": "SECRET_EXPIRY_RULE"},
    ),
    "SecretReuseRule": (
        ("rule_type", "is_enforced_on_deleted_secret_versions"),
        {"rule_type": "SECRET_REUSE_RULE"},
    ),
    "RotationConfig": (
        ("rotation_interval", "target_system_details", "is_scheduled_rotation_enabled"),
        {},
    ),
    "AdbTargetSystemDetails": (
        ("target_system_type", "adb_id"),
        {"target_system_type": "ADB"},
    ),
    "FunctionTargetSystemDetails": (
        ("target_system_type", "function_id"),
        {"target_system_type": "FUNCTION"},
    ),
    "ReplicationConfig": (("replication_targets", "is_write_forward_enabled"), {}),
    "ReplicationTarget": (("target_key_id", "target_region", "target_vault_id"), {}),
    "PassphraseGenerationContext": (
        ("generation_type", "secret_template", "generation_template", "passphrase_length"),
        {"generation_type": "PASSPHRASE"},
    ),
    "SshKeyGenerationContext": (
        ("generation_type", "secret_template", "generation_template"),
        {"generation_type": "SSH_KEY"},
    ),
    "BytesGenerationContext": (
        ("generation_type", "secret_template", "generation_template"),
        {"generation_type": "BYTES"},
    ),
}


def make_model_class(name, fields=None, defaults=None):
    """Return a fake SDK model class that rejects unknown fields like the real SDK."""
    attrs = dict(defaults or {})
    if fields is not None:
        attrs["swagger_types"] = dict.fromkeys(fields, "str")

        def init(self, **kwargs):
            unknown = sorted(set(kwargs) - set(fields))
            if unknown:
                raise TypeError("Unrecognized keyword arguments: " + ", ".join(unknown))
            FakeModel.__init__(self, **kwargs)

        attrs["__init__"] = init
    return type(name, (FakeModel,), attrs)


def install_fake_oci(monkeypatch):
    oci_module, service_error = shared_install_fake_oci(monkeypatch)
    models = {name: make_model_class(name) for name in PLAIN_MODEL_NAMES}
    models.update(
        {
            name: make_model_class(name, fields, defaults)
            for name, (fields, defaults) in STRICT_MODELS.items()
        }
    )
    oci_module.vault = types.SimpleNamespace(
        VaultsClient=type("FakeVaultsClient", (), {}),
        models=types.SimpleNamespace(**models),
    )
    oci_module.secrets = types.SimpleNamespace(
        SecretsClient=type("FakeSecretsClient", (), {})
    )
    oci_module.retry.RetryStrategyBuilder = lambda **kwargs: types.SimpleNamespace(
        get_retry_strategy=lambda: oci_module.retry.DEFAULT_RETRY_STRATEGY
    )

    def fake_wait_until(wait_client, response, *args, **kwargs):
        evaluate_response = kwargs["evaluate_response"]
        fetch_func = kwargs["fetch_func"]
        while not evaluate_response(response):
            response = fetch_func(response=response)
        return response

    oci_module.wait_until = fake_wait_until
    return oci_module, service_error


def load_module():
    sys.modules.pop(HELPER_MODULE, None)
    return load_collection_module("oci_vault_secret")


@pytest.fixture(autouse=True)
def restore_helper_module():
    """Keep the helper rebound to this file's fake SDK from leaking into other tests."""
    saved = sys.modules.get(HELPER_MODULE)
    yield
    if saved is None:
        sys.modules.pop(HELPER_MODULE, None)
    else:
        sys.modules[HELPER_MODULE] = saved


@pytest.fixture
def module_obj(monkeypatch):
    install_fake_oci(monkeypatch)
    return load_module()


def make_secret(state="ACTIVE", **overrides):
    fields = dict(
        id=SECRET_ID,
        secret_name=SECRET_NAME,
        compartment_id=COMPARTMENT_ID,
        vault_id=VAULT_ID,
        key_id=KEY_ID,
        description="a secret",
        lifecycle_state=state,
        current_version_number=1,
        metadata={},
        secret_rules=[],
        rotation_config=None,
        rotation_status="NOT_ENABLED",
        replication_config=None,
        is_replica=False,
        is_auto_generation_enabled=False,
        secret_generation_context=None,
        freeform_tags={},
        defined_tags={},
    )
    fields.update(overrides)
    return FakeModel(**fields)


def b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


class FakeVaultsClient:
    """Record vault calls and serve a mutable secret."""

    def __init__(self, secret=None, restored_state="ACTIVE", updating_after_update=False):
        self.secret = secret
        self.restored_state = restored_state
        self.updating_after_update = updating_after_update
        self.calls = []
        self.rotating_polls = 0
        self.rotation_started = False
        self.fail_rotation = False

    def list_secrets(self, **kwargs):
        raise AssertionError("list_secrets is served by the list_all_resources stub")

    def get_secret(self, secret_id):
        self.calls.append(("get_secret", secret_id))
        if self.secret.lifecycle_state == "CANCELLING_DELETION":
            self.secret.lifecycle_state = self.restored_state
        elif self.secret.lifecycle_state == "UPDATING":
            self.secret.lifecycle_state = "ACTIVE"
        if self.rotation_started:
            if self.fail_rotation:
                self.secret.lifecycle_state = "FAILED"
            elif self.rotating_polls > 0:
                self.rotating_polls -= 1
            else:
                self.rotation_started = False
                self.secret.current_version_number += 1
                self.secret.rotation_status = "NOT_ENABLED"
        return FakeResponse(self.secret)

    def create_secret(self, create_secret_details):
        self.calls.append(("create_secret", create_secret_details))
        self.secret = make_secret()
        return FakeResponse(self.secret)

    def update_secret(self, secret_id, update_secret_details):
        self.calls.append(("update_secret", secret_id, update_secret_details))
        assert self.secret.lifecycle_state == "ACTIVE"
        details = update_secret_details
        exclusive = ("secret_content", "current_version_number", "secret_rules")
        assert sum(hasattr(details, name) for name in exclusive) <= 1
        if self.updating_after_update:
            self.secret.lifecycle_state = "UPDATING"
        return FakeResponse(self.secret)

    def schedule_secret_deletion(self, secret_id, schedule_secret_deletion_details):
        self.calls.append(
            ("schedule_secret_deletion", secret_id, schedule_secret_deletion_details)
        )
        self.secret.lifecycle_state = "PENDING_DELETION"
        return FakeResponse(None)

    def cancel_secret_deletion(self, secret_id):
        self.calls.append(("cancel_secret_deletion", secret_id))
        self.secret.lifecycle_state = "CANCELLING_DELETION"
        return FakeResponse(None)

    def rotate_secret(self, secret_id):
        self.calls.append(("rotate_secret", secret_id))
        assert self.secret.lifecycle_state == "ACTIVE"
        self.secret.rotation_status = "IN_PROGRESS"
        self.rotation_started = True
        return FakeResponse(None)

    def call_names(self):
        return [call[0] for call in self.calls if call[0] != "get_secret"]

    def calls_named(self, name):
        return [call for call in self.calls if call[0] == name]


class FakeSecretsClient:
    """Serve secret bundles by stage, answering 404 for a missing stage."""

    def __init__(self, service_error, bundles=None):
        self.service_error = service_error
        self.bundles = bundles or {}
        self.calls = []

    def get_secret_bundle(self, secret_id, **selector):
        self.calls.append((secret_id, selector))
        stage = selector["stage"]
        if stage not in self.bundles:
            raise self.service_error(404)
        content = types.SimpleNamespace(content=self.bundles[stage])
        return FakeResponse(types.SimpleNamespace(secret_bundle_content=content))


class ForbiddenSecretsClient:
    def get_secret_bundle(self, *args, **kwargs):
        raise AssertionError("the secret content must not be read")


def make_instance(module_obj, params, client, check_mode=False, secrets=None):
    full_params = {
        "state": "present",
        "secret_id": SECRET_ID,
        "wait": False,
        "rotate": False,
        "content_encoding": "text",
        "content_stage": "CURRENT",
        "update_content": "when_changed",
    }
    full_params.update(params)
    instance = make_module_instance(
        module_obj,
        "OciVaultSecretModule",
        full_params,
        client=client,
        check_mode=check_mode,
    )
    instance._update_plan_cache = None
    instance.call_with_retry = lambda fn, *args, **kwargs: fn(*args, **kwargs)
    if secrets is not None:
        instance._secrets_client = secrets
    return instance


def run_module(module_obj, params, client, check_mode=False, secrets=None):
    instance = make_instance(module_obj, params, client, check_mode, secrets)
    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()
    return excinfo.value.payload


def run_module_failure(module_obj, params, client, check_mode=False, secrets=None):
    instance = make_instance(module_obj, params, client, check_mode, secrets)
    with pytest.raises(FailJsonCalled) as excinfo:
        instance.execute_resource_module()
    return excinfo.value.payload["msg"]


def make_create_instance(module_obj, params, client, check_mode=False):
    base = {
        "secret_id": None,
        "compartment_id": COMPARTMENT_ID,
        "vault_id": VAULT_ID,
        "key_id": KEY_ID,
        "name": SECRET_NAME,
    }
    base.update(params)
    instance = make_instance(module_obj, base, client, check_mode)
    instance.resolve_resource_by_name = lambda: None
    return instance


def run_create(module_obj, params, client, check_mode=False):
    instance = make_create_instance(module_obj, params, client, check_mode)
    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()
    return excinfo.value.payload


def run_create_failure(module_obj, params, client):
    instance = make_create_instance(module_obj, params, client)
    with pytest.raises(FailJsonCalled) as excinfo:
        instance.execute_resource_module()
    return excinfo.value.payload["msg"]


def rule(rule_type, **fields):
    full = dict.fromkeys(
        (
            "secret_version_expiry_interval",
            "time_of_absolute_expiry",
            "is_secret_content_retrieval_blocked_on_expiry",
            "is_enforced_on_deleted_secret_versions",
        )
    )
    full.update(fields, rule_type=rule_type)
    return full


# main and option handling


def test_main_wires_argument_spec_and_runs_module(monkeypatch):
    install_fake_oci(monkeypatch)
    module_obj = load_module()
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeSecretModule:
        def __init__(self, module):
            self.module = module

        def execute_resource_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciVaultSecretModule", FakeSecretModule)

    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert captured["mutually_exclusive"] == [["content", "current_version_number"]]
    assert spec["state"]["default"] == "present"
    assert spec["content"] == {"type": "str", "no_log": True}
    assert spec["content_encoding"]["choices"] == ["text", "base64"]
    assert spec["content_stage"]["choices"] == ["current", "pending"]
    assert spec["content_stage"]["default"] == "current"
    assert spec["update_content"]["choices"] == ["when_changed", "on_create"]
    assert spec["update_content"]["default"] == "when_changed"
    assert spec["rotate"] == {"type": "bool", "default": False}
    assert spec["deletion_days"] == {"type": "int"}
    assert spec["secret_rules"]["options"]["rule_type"]["required"] is True
    assert spec["secret_generation_context"]["options"]["generation_type"]["choices"] == [
        "passphrase",
        "ssh_key",
        "bytes",
    ]
    assert spec["rotation_config"]["options"]["target_system_details"]["options"][
        "target_system_type"
    ]["choices"] == ["adb", "function"]
    assert spec["replication_config"]["options"]["replication_targets"]["options"][
        "target_region"
    ] == {"type": "str", "required": True}
    for name in ("name", "compartment_id", "freeform_tags", "defined_tags", "wait"):
        assert name in spec
    assert "display_name" not in spec


def test_choices_are_normalized_to_oci_values(module_obj):
    module = DummyModule(
        {
            "content_stage": "pending",
            "secret_rules": [{"rule_type": "secret_reuse_rule"}],
            "secret_generation_context": {
                "generation_type": "ssh_key",
                "generation_template": "rsa_2048",
            },
            "rotation_config": {"target_system_details": {"target_system_type": "adb"}},
        }
    )
    module_obj.normalize_choice_parameters(module, module_obj.CHOICE_VALUE_MAPS)

    assert module.params["content_stage"] == "PENDING"
    assert module.params["secret_rules"][0]["rule_type"] == "SECRET_REUSE_RULE"
    assert module.params["secret_generation_context"]["generation_type"] == "SSH_KEY"
    assert module.params["secret_generation_context"]["generation_template"] == "RSA_2048"
    assert (
        module.params["rotation_config"]["target_system_details"]["target_system_type"]
        == "ADB"
    )


def test_validate_options_accepts_valid_input(module_obj):
    module_obj.validate_options(
        DummyModule(
            {
                "content": "AAEC",
                "content_encoding": "base64",
                "enable_auto_generation": False,
                "secret_rules": [
                    rule(
                        "SECRET_EXPIRY_RULE",
                        secret_version_expiry_interval="P30D",
                        time_of_absolute_expiry="2030-01-01T00:00:00Z",
                    ),
                    rule("SECRET_REUSE_RULE", is_enforced_on_deleted_secret_versions=True),
                ],
                "secret_generation_context": {
                    "generation_type": "PASSPHRASE",
                    "passphrase_length": 12,
                    "generation_template": None,
                },
                "rotation_config": {
                    "rotation_interval": "P30D",
                    "target_system_details": {
                        "target_system_type": "ADB",
                        "adb_id": "adb-1",
                        "function_id": None,
                    },
                },
            }
        )
    )


def test_validate_options_rejects_content_with_auto_generation(module_obj):
    with pytest.raises(FailJsonCalled) as excinfo:
        module_obj.validate_options(
            DummyModule({"content": "x", "enable_auto_generation": True})
        )

    assert "enable_auto_generation" in excinfo.value.payload["msg"]


def test_validate_options_rejects_invalid_base64(module_obj):
    with pytest.raises(FailJsonCalled) as excinfo:
        module_obj.validate_options(
            DummyModule({"content": "abc", "content_encoding": "base64"})
        )

    assert "base64" in excinfo.value.payload["msg"]


def test_validate_options_rejects_invalid_timestamp(module_obj):
    with pytest.raises(FailJsonCalled) as excinfo:
        module_obj.validate_options(
            DummyModule(
                {
                    "secret_rules": [
                        rule("SECRET_EXPIRY_RULE", time_of_absolute_expiry="tomorrow")
                    ]
                }
            )
        )

    assert "tomorrow" in excinfo.value.payload["msg"]


@pytest.mark.parametrize(
    "params, unsupported",
    [
        (
            {
                "secret_rules": [
                    rule("SECRET_REUSE_RULE", secret_version_expiry_interval="P1D")
                ]
            },
            "secret_version_expiry_interval",
        ),
        (
            {
                "secret_generation_context": {
                    "generation_type": "SSH_KEY",
                    "passphrase_length": 8,
                }
            },
            "passphrase_length",
        ),
        (
            {
                "rotation_config": {
                    "target_system_details": {
                        "target_system_type": "FUNCTION",
                        "adb_id": "adb-1",
                    }
                }
            },
            "adb_id",
        ),
    ],
)
def test_validate_options_rejects_options_the_selected_type_does_not_support(
    module_obj, params, unsupported
):
    with pytest.raises(FailJsonCalled) as excinfo:
        module_obj.validate_options(DummyModule(params))

    assert unsupported in excinfo.value.payload["msg"]


def test_parse_timestamp_normalizes_to_aware_datetimes(module_obj):
    expected = datetime(2030, 1, 1, tzinfo=timezone.utc)

    assert module_obj.parse_timestamp("2030-01-01T00:00:00Z") == expected
    assert module_obj.parse_timestamp("2030-01-01T00:00:00") == expected
    assert module_obj.parse_timestamp("2030-01-01T02:00:00+02:00") == expected
    assert module_obj.parse_timestamp(datetime(2030, 1, 1)) == expected


def test_dead_states_depend_on_state(module_obj):
    present = make_module_instance(module_obj, "OciVaultSecretModule", {"state": "present"})
    absent = make_module_instance(module_obj, "OciVaultSecretModule", {"state": "absent"})

    assert present.dead_states == {"DELETED", "DELETING"}
    assert "PENDING_DELETION" in absent.dead_states


# create


def test_create_text_secret(module_obj):
    client = FakeVaultsClient()

    payload = run_create(
        module_obj,
        {
            "description": "a secret",
            "metadata": {"owner": "team"},
            "content": "s3cr3t",
            "content_name": "first",
            "freeform_tags": {"env": "dev"},
            "rotate": True,
        },
        client,
    )

    assert payload["changed"] is True
    assert payload["resource"]["id"] == SECRET_ID
    assert payload["resource"]["name"] == SECRET_NAME
    assert "secret_name" not in payload["resource"]
    assert "content" not in payload["resource"]
    # rotate is ignored for a secret created by the same task.
    assert client.call_names() == ["create_secret"]
    details = client.calls_named("create_secret")[0][1]
    assert details.secret_name == SECRET_NAME
    assert details.compartment_id == COMPARTMENT_ID
    assert details.vault_id == VAULT_ID
    assert details.key_id == KEY_ID
    assert details.description == "a secret"
    assert details.metadata == {"owner": "team"}
    assert details.freeform_tags == {"env": "dev"}
    assert details.secret_content.content == b64("s3cr3t")
    assert details.secret_content.name == "first"
    assert details.secret_content.stage == "CURRENT"
    assert not hasattr(details, "enable_auto_generation")
    assert not hasattr(details, "defined_tags")


def test_create_base64_secret_sends_the_decoded_bytes_encoded_once(module_obj):
    client = FakeVaultsClient()

    run_create(
        module_obj, {"content": "AAECAwQ=", "content_encoding": "base64"}, client
    )

    details = client.calls_named("create_secret")[0][1]
    assert details.secret_content.content == "AAECAwQ="


def test_create_secret_with_nested_models(module_obj):
    client = FakeVaultsClient()

    run_create(
        module_obj,
        {
            "content": "x",
            "secret_rules": [
                rule(
                    "SECRET_EXPIRY_RULE",
                    secret_version_expiry_interval="P30D",
                    time_of_absolute_expiry="2030-01-01T00:00:00Z",
                    is_secret_content_retrieval_blocked_on_expiry=True,
                ),
                rule("SECRET_REUSE_RULE", is_enforced_on_deleted_secret_versions=True),
            ],
            "rotation_config": {
                "rotation_interval": "P30D",
                "is_scheduled_rotation_enabled": True,
                "target_system_details": {
                    "target_system_type": "ADB",
                    "adb_id": "adb-1",
                    "function_id": None,
                },
            },
            "replication_config": {
                "replication_targets": [
                    {
                        "target_region": "us-phoenix-1",
                        "target_vault_id": "vault-2",
                        "target_key_id": "key-2",
                    }
                ],
                "is_write_forward_enabled": None,
            },
        },
        client,
    )

    details = client.calls_named("create_secret")[0][1]
    expiry, reuse = details.secret_rules
    assert type(expiry).__name__ == "SecretExpiryRule"
    assert expiry.secret_version_expiry_interval == "P30D"
    assert expiry.time_of_absolute_expiry == datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert expiry.is_secret_content_retrieval_blocked_on_expiry is True
    assert type(reuse).__name__ == "SecretReuseRule"
    assert reuse.is_enforced_on_deleted_secret_versions is True
    rotation = details.rotation_config
    assert rotation.rotation_interval == "P30D"
    assert rotation.is_scheduled_rotation_enabled is True
    assert type(rotation.target_system_details).__name__ == "AdbTargetSystemDetails"
    assert rotation.target_system_details.adb_id == "adb-1"
    replication = details.replication_config
    assert type(replication.replication_targets[0]).__name__ == "ReplicationTarget"
    assert replication.replication_targets[0].target_region == "us-phoenix-1"
    assert not hasattr(replication, "is_write_forward_enabled")


def test_create_auto_generated_secret(module_obj):
    client = FakeVaultsClient()

    run_create(
        module_obj,
        {
            "enable_auto_generation": True,
            "secret_generation_context": {
                "generation_type": "PASSPHRASE",
                "generation_template": "SECRETS_DEFAULT_PASSWORD",
                "passphrase_length": 16,
                "secret_template": None,
            },
        },
        client,
    )

    details = client.calls_named("create_secret")[0][1]
    assert details.enable_auto_generation is True
    assert type(details.secret_generation_context).__name__ == "PassphraseGenerationContext"
    assert details.secret_generation_context.passphrase_length == 16
    assert not hasattr(details.secret_generation_context, "secret_template")
    assert not hasattr(details, "secret_content")


def test_create_check_mode_does_not_call_oci(module_obj):
    client = FakeVaultsClient()

    payload = run_create(module_obj, {"content": "x"}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.calls == []


@pytest.mark.parametrize("missing", ["compartment_id", "vault_id", "key_id", "name"])
def test_create_requires_identity_fields(module_obj, missing):
    msg = run_create_failure(module_obj, {"content": "x", missing: None}, FakeVaultsClient())

    assert missing in msg


def test_create_requires_content_unless_auto_generating(module_obj):
    client = FakeVaultsClient()

    msg = run_create_failure(module_obj, {}, client)

    assert "content" in msg
    assert client.calls == []


def test_create_with_auto_generation_requires_generation_context(module_obj):
    msg = run_create_failure(
        module_obj, {"enable_auto_generation": True}, FakeVaultsClient()
    )

    assert "secret_generation_context" in msg


def test_create_rejects_pending_content_stage(module_obj):
    msg = run_create_failure(
        module_obj, {"content": "x", "content_stage": "PENDING"}, FakeVaultsClient()
    )

    assert "content_stage=current" in msg


def test_create_with_missing_secret_id_fails(module_obj):
    client = FakeVaultsClient()
    client.get_secret = raising(sys.modules["oci"].exceptions.ServiceError(404))

    msg = run_module_failure(module_obj, {"content": "x"}, client)

    assert SECRET_ID in msg


# idempotency


FULL_DESIRED = {
    "name": SECRET_NAME,
    "compartment_id": COMPARTMENT_ID,
    "vault_id": VAULT_ID,
    "key_id": KEY_ID,
    "description": "a secret",
    "metadata": {"owner": "team"},
    "freeform_tags": {"env": "dev"},
    "defined_tags": {"ns": {"k": "v"}},
    "current_version_number": 3,
    "enable_auto_generation": True,
    "secret_rules": [
        rule("SECRET_EXPIRY_RULE", secret_version_expiry_interval="P30D"),
        rule("SECRET_REUSE_RULE", is_enforced_on_deleted_secret_versions=True),
    ],
    "secret_generation_context": {
        "generation_type": "PASSPHRASE",
        "generation_template": "SECRETS_DEFAULT_PASSWORD",
        "passphrase_length": 12,
        "secret_template": None,
    },
    "rotation_config": {
        "rotation_interval": "P30D",
        "is_scheduled_rotation_enabled": True,
        "target_system_details": {
            "target_system_type": "FUNCTION",
            "function_id": "fn-1",
            "adb_id": None,
        },
    },
    "replication_config": {
        "replication_targets": [
            {
                "target_region": "us-phoenix-1",
                "target_vault_id": "vault-2",
                "target_key_id": "key-2",
            }
        ],
        "is_write_forward_enabled": True,
    },
}


def make_converged_secret(module_obj, **overrides):
    models = sys.modules["oci"].vault.models
    fields = dict(
        metadata={"owner": "team"},
        freeform_tags={"env": "dev"},
        defined_tags={"ns": {"k": "v"}},
        current_version_number=3,
        is_auto_generation_enabled=True,
        secret_rules=[
            models.SecretExpiryRule(
                secret_version_expiry_interval="P30D",
                time_of_absolute_expiry=None,
                is_secret_content_retrieval_blocked_on_expiry=False,
            ),
            models.SecretReuseRule(is_enforced_on_deleted_secret_versions=True),
        ],
        secret_generation_context=models.PassphraseGenerationContext(
            generation_template="SECRETS_DEFAULT_PASSWORD",
            passphrase_length=12,
            secret_template="{}",
        ),
        rotation_config=models.RotationConfig(
            rotation_interval="P30D",
            is_scheduled_rotation_enabled=True,
            target_system_details=models.FunctionTargetSystemDetails(function_id="fn-1"),
        ),
        replication_config=models.ReplicationConfig(
            replication_targets=[
                models.ReplicationTarget(
                    target_region="us-phoenix-1",
                    target_vault_id="vault-2",
                    target_key_id="key-2",
                )
            ],
            is_write_forward_enabled=True,
        ),
    )
    fields.update(overrides)
    return make_secret(**fields)


@pytest.mark.parametrize("check_mode", [False, True])
def test_idempotent_rerun_makes_no_changes(module_obj, check_mode):
    client = FakeVaultsClient(make_converged_secret(module_obj))
    secrets = FakeSecretsClient(
        sys.modules["oci"].exceptions.ServiceError, {"CURRENT": b64("s3cr3t")}
    )
    params = dict(FULL_DESIRED, current_version_number=None, content="s3cr3t")

    payload = run_module(module_obj, params, client, check_mode, secrets)

    assert payload["changed"] is False
    assert payload["resource"]["name"] == SECRET_NAME
    assert client.call_names() == []
    assert len(secrets.calls) == 1


def test_idempotent_rerun_with_current_version_number(module_obj):
    client = FakeVaultsClient(make_converged_secret(module_obj))

    payload = run_module(module_obj, dict(FULL_DESIRED), client)

    assert payload["changed"] is False
    assert client.call_names() == []


@pytest.mark.parametrize(
    "desired, changed",
    [
        ("2030-01-01T00:00:00Z", False),
        ("2030-01-01T02:00:00+02:00", False),
        ("2030-01-01T00:00:00", False),
        ("2031-01-01T00:00:00Z", True),
    ],
)
def test_rule_timestamps_are_compared_as_instants(module_obj, desired, changed):
    models = sys.modules["oci"].vault.models
    secret = make_secret(
        secret_rules=[
            models.SecretExpiryRule(
                time_of_absolute_expiry=datetime(2030, 1, 1, tzinfo=timezone.utc)
            )
        ]
    )
    client = FakeVaultsClient(secret)

    payload = run_module(
        module_obj,
        {
            "secret_rules": [
                rule("SECRET_EXPIRY_RULE", time_of_absolute_expiry=desired)
            ]
        },
        client,
    )

    assert payload["changed"] is changed
    assert client.call_names() == (["update_secret"] if changed else [])


# updates


@pytest.mark.parametrize(
    "params, field, value",
    [
        ({"description": "new"}, "description", "new"),
        ({"metadata": {"a": "b"}}, "metadata", {"a": "b"}),
        ({"freeform_tags": {"env": "prod"}}, "freeform_tags", {"env": "prod"}),
        ({"defined_tags": {"ns": {"k": "v"}}}, "defined_tags", {"ns": {"k": "v"}}),
        ({"enable_auto_generation": True}, "enable_auto_generation", True),
        ({"current_version_number": 2}, "current_version_number", 2),
    ],
)
def test_update_single_field(module_obj, params, field, value):
    client = FakeVaultsClient(make_secret(current_version_number=3))

    payload = run_module(module_obj, params, client)

    assert payload["changed"] is True
    assert client.call_names() == ["update_secret"]
    call = client.calls_named("update_secret")[0]
    assert call[1] == SECRET_ID
    assert vars(call[2]) == {field: value}


def test_update_rules_builds_polymorphic_models(module_obj):
    client = FakeVaultsClient(make_secret())

    run_module(
        module_obj,
        {
            "secret_rules": [
                rule(
                    "SECRET_EXPIRY_RULE",
                    secret_version_expiry_interval="P30D",
                    time_of_absolute_expiry="2030-01-01T00:00:00Z",
                ),
                rule("SECRET_REUSE_RULE", is_enforced_on_deleted_secret_versions=True),
            ]
        },
        client,
    )

    details = client.calls_named("update_secret")[0][2]
    expiry, reuse = details.secret_rules
    assert type(expiry).__name__ == "SecretExpiryRule"
    assert expiry.time_of_absolute_expiry == datetime(2030, 1, 1, tzinfo=timezone.utc)
    assert type(reuse).__name__ == "SecretReuseRule"


@pytest.mark.parametrize(
    "current_rules, desired_rules",
    [
        ([], [rule("SECRET_REUSE_RULE", is_enforced_on_deleted_secret_versions=True)]),
        (
            [("SecretReuseRule", {"is_enforced_on_deleted_secret_versions": True})],
            [],
        ),
        (
            [("SecretReuseRule", {"is_enforced_on_deleted_secret_versions": False})],
            [rule("SECRET_REUSE_RULE", is_enforced_on_deleted_secret_versions=True)],
        ),
    ],
)
def test_added_removed_and_changed_rules_update_the_secret(
    module_obj, current_rules, desired_rules
):
    models = sys.modules["oci"].vault.models
    secret = make_secret(
        secret_rules=[getattr(models, name)(**fields) for name, fields in current_rules]
    )
    client = FakeVaultsClient(secret)

    payload = run_module(module_obj, {"secret_rules": desired_rules}, client)

    assert payload["changed"] is True
    details = client.calls_named("update_secret")[0][2]
    assert len(details.secret_rules) == len(desired_rules)


def test_rules_in_a_different_order_are_unchanged(module_obj):
    models = sys.modules["oci"].vault.models
    secret = make_secret(
        secret_rules=[
            models.SecretReuseRule(is_enforced_on_deleted_secret_versions=True),
            models.SecretExpiryRule(secret_version_expiry_interval="P30D"),
        ]
    )
    client = FakeVaultsClient(secret)

    payload = run_module(
        module_obj,
        {
            "secret_rules": [
                rule("SECRET_EXPIRY_RULE", secret_version_expiry_interval="P30D"),
                rule("SECRET_REUSE_RULE", is_enforced_on_deleted_secret_versions=True),
            ]
        },
        client,
    )

    assert payload["changed"] is False


def test_update_generation_context_rotation_and_replication(module_obj):
    client = FakeVaultsClient(make_secret())

    run_module(
        module_obj,
        {
            "secret_generation_context": FULL_DESIRED["secret_generation_context"],
            "rotation_config": FULL_DESIRED["rotation_config"],
            "replication_config": FULL_DESIRED["replication_config"],
        },
        client,
    )

    details = client.calls_named("update_secret")[0][2]
    assert details.secret_generation_context.generation_template == "SECRETS_DEFAULT_PASSWORD"
    assert not hasattr(details.secret_generation_context, "secret_template")
    assert details.rotation_config.target_system_details.function_id == "fn-1"
    assert type(details.rotation_config.target_system_details).__name__ == (
        "FunctionTargetSystemDetails"
    )
    assert details.replication_config.is_write_forward_enabled is True
    assert details.replication_config.replication_targets[0].target_key_id == "key-2"


def test_update_check_mode_does_not_call_oci(module_obj):
    client = FakeVaultsClient(make_secret())

    payload = run_module(module_obj, {"description": "new"}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


@pytest.mark.parametrize(
    "param, value",
    [
        ("name", "other-name"),
        ("compartment_id", "ocid1.compartment.oc1..other"),
        ("vault_id", "ocid1.vault.oc1..other"),
        ("key_id", "ocid1.key.oc1..other"),
    ],
)
def test_immutable_fields_fail(module_obj, param, value):
    client = FakeVaultsClient(make_secret())

    msg = run_module_failure(module_obj, {param: value}, client)

    assert param in msg
    assert client.call_names() == []


def test_rules_and_current_version_number_cannot_change_together(module_obj):
    client = FakeVaultsClient(make_secret(current_version_number=3))

    msg = run_module_failure(
        module_obj,
        {
            "secret_rules": [
                rule("SECRET_REUSE_RULE", is_enforced_on_deleted_secret_versions=True)
            ],
            "current_version_number": 2,
        },
        client,
    )

    assert "separate tasks" in msg
    assert client.call_names() == []


def test_update_name_lookup_hydrates_the_summary(module_obj):
    client = FakeVaultsClient(make_secret(metadata={"owner": "team"}))
    summary = FakeModel(id=SECRET_ID, secret_name=SECRET_NAME, lifecycle_state="ACTIVE")
    other = FakeModel(id="other", secret_name="other-name", lifecycle_state="ACTIVE")
    deleted = FakeModel(id="old", secret_name=SECRET_NAME, lifecycle_state="DELETED")
    listed = {}

    instance = make_instance(
        module_obj,
        {
            "secret_id": None,
            "name": SECRET_NAME,
            "compartment_id": COMPARTMENT_ID,
            "vault_id": VAULT_ID,
            "metadata": {"owner": "team"},
        },
        client,
    )

    def list_all_resources(list_fn, **kwargs):
        listed.update(list_fn=list_fn, kwargs=kwargs)
        return [other, deleted, summary]

    instance.list_all_resources = list_all_resources

    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()

    payload = excinfo.value.payload
    assert payload["changed"] is False
    assert payload["resource"]["metadata"] == {"owner": "team"}
    assert listed["list_fn"] == client.list_secrets
    assert listed["kwargs"] == {"compartment_id": COMPARTMENT_ID, "vault_id": VAULT_ID}
    assert client.calls == [("get_secret", SECRET_ID)]


def test_name_lookup_requires_vault_id(module_obj):
    client = FakeVaultsClient(make_secret())

    msg = run_module_failure(
        module_obj,
        {"secret_id": None, "name": SECRET_NAME, "compartment_id": COMPARTMENT_ID},
        client,
    )

    assert "vault_id" in msg


# content


def new_secrets_client(bundles):
    return FakeSecretsClient(sys.modules["oci"].exceptions.ServiceError, bundles)


@pytest.mark.parametrize("check_mode", [False, True])
def test_unchanged_content_is_not_written(module_obj, check_mode):
    client = FakeVaultsClient(make_secret())
    secrets = new_secrets_client({"CURRENT": b64("same")})

    payload = run_module(module_obj, {"content": "same"}, client, check_mode, secrets)

    assert payload["changed"] is False
    assert client.call_names() == []
    assert secrets.calls == [(SECRET_ID, {"stage": "CURRENT"})]


def test_unchanged_base64_content_is_not_written(module_obj):
    client = FakeVaultsClient(make_secret())
    secrets = new_secrets_client({"CURRENT": "AAECAwQ="})

    payload = run_module(
        module_obj,
        {"content": "AAECAwQ=", "content_encoding": "base64"},
        client,
        secrets=secrets,
    )

    assert payload["changed"] is False


def test_changed_content_writes_a_new_version(module_obj):
    client = FakeVaultsClient(make_secret())
    secrets = new_secrets_client({"CURRENT": b64("old")})

    payload = run_module(
        module_obj,
        {"content": "new", "content_name": "v2"},
        client,
        secrets=secrets,
    )

    assert payload["changed"] is True
    assert "content" not in payload["resource"]
    assert client.call_names() == ["update_secret"]
    # One bundle read serves both extra_change_needed calls and the apply step.
    assert len(secrets.calls) == 1
    details = client.calls_named("update_secret")[0][2]
    assert vars(details).keys() == {"secret_content"}
    assert details.secret_content.content == b64("new")
    assert details.secret_content.name == "v2"
    assert details.secret_content.stage == "CURRENT"


def test_changed_content_check_mode_does_not_write(module_obj):
    client = FakeVaultsClient(make_secret())
    secrets = new_secrets_client({"CURRENT": b64("old")})

    payload = run_module(
        module_obj, {"content": "new"}, client, check_mode=True, secrets=secrets
    )

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_missing_pending_version_is_written(module_obj):
    client = FakeVaultsClient(make_secret())
    secrets = new_secrets_client({"CURRENT": b64("current")})

    payload = run_module(
        module_obj,
        {"content": "next", "content_stage": "PENDING"},
        client,
        secrets=secrets,
    )

    assert payload["changed"] is True
    assert secrets.calls == [(SECRET_ID, {"stage": "PENDING"})]
    details = client.calls_named("update_secret")[0][2]
    assert details.secret_content.stage == "PENDING"


def test_matching_pending_version_is_not_written(module_obj):
    client = FakeVaultsClient(make_secret())
    secrets = new_secrets_client({"CURRENT": b64("current"), "PENDING": b64("next")})

    payload = run_module(
        module_obj,
        {"content": "next", "content_stage": "PENDING"},
        client,
        secrets=secrets,
    )

    assert payload["changed"] is False


@pytest.mark.parametrize("check_mode", [False, True])
def test_update_content_on_create_never_reads_existing_content(module_obj, check_mode):
    client = FakeVaultsClient(make_secret())

    payload = run_module(
        module_obj,
        {"content": "different", "update_content": "on_create"},
        client,
        check_mode,
        ForbiddenSecretsClient(),
    )

    assert payload["changed"] is False
    assert client.call_names() == []


def test_rules_and_content_are_written_in_separate_updates(module_obj):
    client = FakeVaultsClient(make_secret())
    secrets = new_secrets_client({"CURRENT": b64("old")})

    payload = run_module(
        module_obj,
        {
            "content": "new",
            "secret_rules": [
                rule("SECRET_REUSE_RULE", is_enforced_on_deleted_secret_versions=True)
            ],
        },
        client,
        secrets=secrets,
    )

    assert payload["changed"] is True
    assert client.call_names() == ["update_secret", "update_secret"]
    first, second = (call[2] for call in client.calls_named("update_secret"))
    assert vars(first).keys() == {"secret_rules"}
    assert vars(second).keys() == {"secret_content"}


def test_field_update_without_wait_settles_before_content_update(module_obj):
    client = FakeVaultsClient(make_secret(), updating_after_update=True)
    secrets = new_secrets_client({"CURRENT": b64("old")})

    run_module(
        module_obj,
        {"description": "new", "content": "new"},
        client,
        secrets=secrets,
    )

    names = [call[0] for call in client.calls]
    first_update = names.index("update_secret")
    second_update = names.index("update_secret", first_update + 1)
    assert "get_secret" in names[first_update + 1 : second_update]


# rotate


def test_rotate_without_wait_requests_one_rotation(module_obj):
    client = FakeVaultsClient(make_secret())
    client.rotating_polls = 5

    payload = run_module(module_obj, {"rotate": True}, client)

    assert payload["changed"] is True
    assert client.call_names() == ["rotate_secret"]
    assert payload["resource"]["rotation_status"] == "IN_PROGRESS"


def test_rotate_with_wait_polls_for_a_new_version(module_obj):
    client = FakeVaultsClient(make_secret(current_version_number=4))
    client.rotating_polls = 2

    payload = run_module(
        module_obj,
        {"rotate": True, "wait": True, "wait_timeout": 60, "wait_interval": 5},
        client,
    )

    assert payload["changed"] is True
    assert payload["resource"]["current_version_number"] == 5
    assert payload["resource"]["rotation_status"] == "NOT_ENABLED"
    assert client.call_names() == ["rotate_secret"]
    after_rotation = client.calls[client.calls.index(("rotate_secret", SECRET_ID)) :]
    assert len(after_rotation) >= 3


def test_rotate_wait_passes_timeout_and_interval(module_obj):
    client = FakeVaultsClient(make_secret())
    waited = {}

    def fake_wait_until(wait_client, response, **kwargs):
        waited.update(kwargs)
        return response

    sys.modules["oci"].wait_until = fake_wait_until

    run_module(
        module_obj,
        {"rotate": True, "wait": True, "wait_timeout": 60, "wait_interval": 5},
        client,
    )

    assert waited["max_wait_seconds"] == 60
    assert waited["max_interval_seconds"] == 5


def test_rotate_fails_when_the_secret_fails(module_obj):
    client = FakeVaultsClient(make_secret())
    client.fail_rotation = True
    client.rotating_polls = 1

    msg = run_module_failure(module_obj, {"rotate": True, "wait": True}, client)

    assert "failure state" in msg


def test_rotate_check_mode_does_not_call_oci(module_obj):
    client = FakeVaultsClient(make_secret())

    payload = run_module(module_obj, {"rotate": True}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_rotate_after_update_rotates_once(module_obj):
    client = FakeVaultsClient(make_secret())

    run_module(module_obj, {"rotate": True, "description": "new"}, client)

    assert client.call_names() == ["update_secret", "rotate_secret"]


# replicas


@pytest.mark.parametrize(
    "params",
    [{"description": "new"}, {"content": "new"}, {"rotate": True}],
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_replica_cannot_be_changed(module_obj, params, check_mode):
    client = FakeVaultsClient(make_secret(is_replica=True))
    secrets = new_secrets_client({"CURRENT": b64("old")})

    msg = run_module_failure(module_obj, params, client, check_mode, secrets)

    assert "replica" in msg
    assert client.call_names() == []


def test_unchanged_replica_is_not_an_error(module_obj):
    client = FakeVaultsClient(make_secret(is_replica=True))

    payload = run_module(module_obj, {"description": "a secret"}, client)

    assert payload["changed"] is False


# absent


def test_absent_schedules_deletion_with_default_window(module_obj):
    client = FakeVaultsClient(make_secret())

    payload = run_module(module_obj, {"state": "absent"}, client)

    assert payload == {"changed": True}
    call = client.calls_named("schedule_secret_deletion")[0]
    assert call[1] == SECRET_ID
    assert not hasattr(call[2], "time_of_deletion")


@pytest.mark.parametrize("deletion_days", [1, 30])
def test_absent_schedules_deletion_with_deletion_days(module_obj, deletion_days):
    client = FakeVaultsClient(make_secret())
    before = datetime.now(timezone.utc)

    run_module(module_obj, {"state": "absent", "deletion_days": deletion_days}, client)

    after = datetime.now(timezone.utc)
    time_of_deletion = client.calls_named("schedule_secret_deletion")[0][2].time_of_deletion
    window = timedelta(days=deletion_days)
    if deletion_days < 30:
        window += timedelta(minutes=10)
    assert before + window <= time_of_deletion <= after + window
    assert time_of_deletion.tzinfo is not None


@pytest.mark.parametrize("deletion_days", [0, 31])
def test_absent_deletion_days_out_of_range_fails(module_obj, deletion_days):
    client = FakeVaultsClient(make_secret())

    msg = run_module_failure(
        module_obj, {"state": "absent", "deletion_days": deletion_days}, client
    )

    assert "between 1 and 30" in msg
    assert client.calls == []


def test_absent_check_mode_does_not_call_oci(module_obj):
    client = FakeVaultsClient(make_secret())

    payload = run_module(module_obj, {"state": "absent"}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


@pytest.mark.parametrize(
    "state", ["PENDING_DELETION", "SCHEDULING_DELETION", "DELETING", "DELETED"]
)
@pytest.mark.parametrize("check_mode", [False, True])
def test_absent_on_already_deleted_secret_is_unchanged(module_obj, state, check_mode):
    client = FakeVaultsClient(make_secret(state))

    payload = run_module(module_obj, {"state": "absent"}, client, check_mode)

    assert payload == {"changed": False}
    assert client.call_names() == []


def test_absent_waits_for_pending_deletion(module_obj):
    client = FakeVaultsClient(make_secret())
    instance = make_instance(module_obj, {"state": "absent", "wait": True}, client)
    waited = {}

    def fake_wait(resource_id, target_states):
        waited.update(resource_id=resource_id, target_states=set(target_states))
        return client.secret

    instance.wait_for_resource_id = fake_wait

    with pytest.raises(ExitJsonCalled):
        instance.execute_resource_module()

    assert waited["resource_id"] == SECRET_ID
    assert "PENDING_DELETION" in waited["target_states"]
    assert "SCHEDULING_DELETION" not in waited["target_states"]


def test_absent_requires_an_identifier(module_obj):
    msg = run_module_failure(
        module_obj, {"state": "absent", "secret_id": None}, FakeVaultsClient(make_secret())
    )

    assert "secret_id" in msg


# restore


def test_present_on_pending_secret_cancels_deletion(module_obj):
    client = FakeVaultsClient(make_secret("PENDING_DELETION"))

    payload = run_module(module_obj, {}, client)

    assert payload["changed"] is True
    assert payload["resource"]["lifecycle_state"] == "ACTIVE"
    assert client.call_names() == ["cancel_secret_deletion"]


def test_present_on_pending_secret_check_mode_does_not_call_oci(module_obj):
    client = FakeVaultsClient(make_secret("PENDING_DELETION"))

    payload = run_module(module_obj, {}, client, check_mode=True)

    assert payload == {"changed": True}
    assert client.call_names() == []


def test_cancel_deletion_waits_for_active(module_obj):
    client = FakeVaultsClient(make_secret("PENDING_DELETION"))
    instance = make_instance(module_obj, {"wait": True}, client)
    waited = {}

    def fake_wait(resource_id, target_states):
        waited.update(resource_id=resource_id, target_states=tuple(target_states))
        return client.get_secret(resource_id).data

    instance.wait_for_resource_id = fake_wait

    with pytest.raises(ExitJsonCalled) as excinfo:
        instance.execute_resource_module()

    assert excinfo.value.payload["resource"]["lifecycle_state"] == "ACTIVE"
    assert waited == {"resource_id": SECRET_ID, "target_states": ("ACTIVE",)}


def test_pending_secret_is_restored_before_update(module_obj):
    client = FakeVaultsClient(make_secret("PENDING_DELETION"))

    payload = run_module(module_obj, {"description": "new"}, client)

    assert payload["changed"] is True
    assert client.call_names() == ["cancel_secret_deletion", "update_secret"]
    names = [call[0] for call in client.calls]
    assert "get_secret" in names[names.index("cancel_secret_deletion") + 1 :]


def test_pending_secret_is_restored_before_content_is_compared_and_written(module_obj):
    client = FakeVaultsClient(make_secret("PENDING_DELETION"))
    secrets = new_secrets_client({"CURRENT": b64("old")})

    payload = run_module(module_obj, {"content": "new"}, client, secrets=secrets)

    assert payload["changed"] is True
    assert client.call_names() == ["cancel_secret_deletion", "update_secret"]
    assert secrets.calls == [(SECRET_ID, {"stage": "CURRENT"})]


def test_pending_secret_is_restored_before_rotation(module_obj):
    client = FakeVaultsClient(make_secret("PENDING_DELETION"))

    run_module(module_obj, {"rotate": True}, client)

    assert client.call_names() == ["cancel_secret_deletion", "rotate_secret"]


def test_present_on_deleted_secret_fails_as_missing(module_obj):
    client = FakeVaultsClient(make_secret("DELETED"))

    msg = run_module_failure(module_obj, {}, client)

    assert SECRET_ID in msg
