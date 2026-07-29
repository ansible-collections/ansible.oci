import sys
import types

import pytest

from conftest import load_collection_module


class FailJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class DummyModule:
    def __init__(self, params):
        self.params = params
        self.check_mode = False

    def fail_json(self, **kwargs):
        raise FailJsonCalled(kwargs)


class DummyClient:
    def __init__(self, config=None, signer=None):
        self.config = config
        self.signer = signer


def make_fake_oci(config_from_file):
    return types.SimpleNamespace(
        config=types.SimpleNamespace(
            from_file=config_from_file,
            validate_config=lambda config: config,
        ),
        signer=types.SimpleNamespace(
            load_private_key_from_file=lambda path: f"private-key:{path}",
        ),
        auth=types.SimpleNamespace(
            signers=types.SimpleNamespace(
                InstancePrincipalsSecurityTokenSigner=lambda: "instance-signer",
                SecurityTokenSigner=lambda token, key: ("session-signer", token, key),
                get_resource_principals_signer=lambda: "resource-signer",
            ),
        ),
    )


def make_module_params(**overrides):
    params = {
        "auth_type": "api_key",
        "config_file_location": "~/.oci/config",
        "config_profile_name": "DEFAULT",
        "tenancy": None,
        "region": None,
        "api_user": None,
        "api_user_fingerprint": None,
        "api_user_key_file": None,
        "api_user_key_pass_phrase": None,
    }
    params.update(overrides)
    return params


def test_get_oci_config_uses_resolved_config_params(
    monkeypatch,
    tmp_path,
):
    config_file = tmp_path / "env-config"
    config_file.write_text("[ENV]\n", encoding="utf-8")
    loaded_calls = []
    fake_oci = make_fake_oci(
        lambda **kwargs: loaded_calls.append(kwargs) or {"region": "us-ashburn-1"}
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    oci_auth = load_collection_module("oci_auth")
    monkeypatch.setattr(
        oci_auth.os.path,
        "isfile",
        lambda path: path == str(config_file),
    )

    config = oci_auth.get_oci_config(
        DummyModule(
            make_module_params(
                config_file_location=str(config_file),
                config_profile_name="ENV",
            )
        )
    )

    assert loaded_calls == [
        {
            "file_location": str(config_file),
            "profile_name": "ENV",
        }
    ]
    assert config["region"] == "us-ashburn-1"


def test_get_oci_config_module_params_override_config_env_vars(
    monkeypatch,
    tmp_path,
):
    config_file = tmp_path / "explicit-config"
    config_file.write_text("[EXPLICIT]\n", encoding="utf-8")
    loaded_calls = []
    fake_oci = make_fake_oci(
        lambda **kwargs: loaded_calls.append(kwargs) or {"region": "us-phoenix-1"}
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    monkeypatch.setenv("OCI_CONFIG_FILE", str(tmp_path / "ignored-config"))
    monkeypatch.setenv("OCI_CONFIG_PROFILE", "IGNORED")

    oci_auth = load_collection_module("oci_auth")
    monkeypatch.setattr(
        oci_auth.os.path,
        "isfile",
        lambda path: path == str(config_file),
    )

    config = oci_auth.get_oci_config(
        DummyModule(
            make_module_params(
                config_file_location=str(config_file),
                config_profile_name="EXPLICIT",
            )
        )
    )

    assert loaded_calls == [
        {
            "file_location": str(config_file),
            "profile_name": "EXPLICIT",
        }
    ]
    assert config["region"] == "us-phoenix-1"


def test_get_oci_config_module_params_override_loaded_profile_fields(
    monkeypatch,
    tmp_path,
):
    config_file = tmp_path / "config"
    config_file.write_text("[DEFAULT]\n", encoding="utf-8")
    fake_oci = make_fake_oci(
        lambda **kwargs: {
            "region": "us-phoenix-1",
            "fingerprint": "config-fingerprint",
        }
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    oci_auth = load_collection_module("oci_auth")
    monkeypatch.setattr(
        oci_auth.os.path,
        "isfile",
        lambda path: path == str(config_file),
    )

    config = oci_auth.get_oci_config(
        DummyModule(
            make_module_params(
                config_file_location=str(config_file),
                config_profile_name="DEFAULT",
                region="us-ashburn-1",
                api_user_fingerprint="env-fingerprint",
            )
        )
    )

    assert config["region"] == "us-ashburn-1"
    assert config["fingerprint"] == "env-fingerprint"


def test_get_oci_config_builds_api_key_config_from_resolved_params(monkeypatch):
    fake_oci = make_fake_oci(lambda **kwargs: {})
    monkeypatch.setitem(sys.modules, "oci", fake_oci)

    oci_auth = load_collection_module("oci_auth")
    monkeypatch.setattr(oci_auth.os.path, "isfile", lambda path: False)

    config = oci_auth.get_oci_config(
        DummyModule(
            make_module_params(
                tenancy="ocid1.tenancy.oc1..env",
                api_user="ocid1.user.oc1..env",
                region="us-sanjose-1",
                api_user_fingerprint="env-fingerprint",
                api_user_key_file="/tmp/env-key.pem",
                api_user_key_pass_phrase="env-passphrase",
            )
        )
    )

    assert config == {
        "tenancy": "ocid1.tenancy.oc1..env",
        "user": "ocid1.user.oc1..env",
        "region": "us-sanjose-1",
        "fingerprint": "env-fingerprint",
        "key_file": "/tmp/env-key.pem",
        "pass_phrase": "env-passphrase",
    }


def test_get_auth_type_does_not_resolve_from_environment(monkeypatch):
    fake_oci = make_fake_oci(lambda **kwargs: {})
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    monkeypatch.setenv("OCI_AUTH_TYPE", "instance_principal")

    oci_auth = load_collection_module("oci_auth")

    assert oci_auth.get_auth_type(DummyModule(make_module_params())) == "api_key"


def test_get_oci_config_ignores_environment_for_shared_auth_fields(monkeypatch):
    fake_oci = make_fake_oci(lambda **kwargs: {})
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    monkeypatch.setenv("OCI_TENANCY_ID", "ocid1.tenancy.oc1..env")
    monkeypatch.setenv("OCI_USER_ID", "ocid1.user.oc1..env")
    monkeypatch.setenv("OCI_REGION", "us-sanjose-1")
    monkeypatch.setenv("OCI_USER_FINGERPRINT", "env-fingerprint")
    monkeypatch.setenv("OCI_USER_KEY_FILE", "/tmp/env-key.pem")
    monkeypatch.setenv("OCI_USER_KEY_PASS_PHRASE", "env-passphrase")

    oci_auth = load_collection_module("oci_auth")
    monkeypatch.setattr(oci_auth.os.path, "isfile", lambda path: False)

    config = oci_auth.get_oci_config(
        DummyModule(
            make_module_params(
                auth_type="api_key",
                config_file_location="~/.oci/config",
                config_profile_name="DEFAULT",
            )
        )
    )

    assert config == {}


def test_create_service_client_uses_resolved_auth_type_param(
    monkeypatch,
):
    fake_oci = make_fake_oci(lambda **kwargs: {})
    monkeypatch.setitem(sys.modules, "oci", fake_oci)

    oci_auth = load_collection_module("oci_auth")
    client = oci_auth.create_service_client(
        DummyModule(make_module_params(auth_type="instance_principal")),
        DummyClient,
    )

    assert client.config == {}
    assert client.signer == "instance-signer"


def test_create_service_client_module_auth_type_overrides_oci_auth_type_env(
    monkeypatch,
):
    fake_oci = make_fake_oci(lambda **kwargs: {})
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    monkeypatch.setenv("OCI_AUTH_TYPE", "instance_principal")

    oci_auth = load_collection_module("oci_auth")
    client = oci_auth.create_service_client(
        DummyModule(make_module_params(auth_type="resource_principal")),
        DummyClient,
    )

    assert client.config == {}
    assert client.signer == "resource-signer"


def test_create_service_client_ignores_oci_auth_type_env_when_param_uses_default(
    monkeypatch,
):
    fake_oci = make_fake_oci(lambda **kwargs: {})
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    monkeypatch.setenv("OCI_AUTH_TYPE", "instance_principal")

    oci_auth = load_collection_module("oci_auth")
    monkeypatch.setattr(oci_auth.os.path, "isfile", lambda path: False)
    client = oci_auth.create_service_client(
        DummyModule(make_module_params()),
        DummyClient,
    )

    assert client.config == {}
    assert client.signer is None


def test_session_token_auth_uses_resolved_config_profile(
    monkeypatch,
    tmp_path,
):
    config_file = tmp_path / "session-config"
    config_file.write_text("[SESSION]\n", encoding="utf-8")
    key_file = tmp_path / "session.pem"
    token_file = tmp_path / "token"
    token_file.write_text("session-token\n", encoding="utf-8")
    fake_oci = make_fake_oci(
        lambda **kwargs: {
            "key_file": str(key_file),
            "security_token_file": str(token_file),
        }
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    oci_auth = load_collection_module("oci_auth")
    monkeypatch.setattr(
        oci_auth.os.path,
        "isfile",
        lambda path: path == str(config_file),
    )

    client = oci_auth.create_service_client(
        DummyModule(
            make_module_params(
                auth_type="session_token",
                config_file_location=str(config_file),
                config_profile_name="SESSION",
            )
        ),
        DummyClient,
    )

    assert client.config["security_token_file"] == str(token_file)
    assert client.signer == (
        "session-signer",
        "session-token",
        f"private-key:{key_file}",
    )


def test_session_token_auth_requires_security_token_file_from_loaded_config(
    monkeypatch,
    tmp_path,
):
    config_file = tmp_path / "config"
    config_file.write_text("[DEFAULT]\n", encoding="utf-8")

    fake_oci = make_fake_oci(
        lambda **kwargs: {
            "key_file": str(tmp_path / "session.pem"),
        }
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)

    oci_auth = load_collection_module("oci_auth")
    module = DummyModule(
        {
            "auth_type": "session_token",
            "config_file_location": str(config_file),
            "config_profile_name": "DEFAULT",
        }
    )

    with pytest.raises(FailJsonCalled) as exc_info:
        oci_auth.create_service_client(module, DummyClient)

    assert "security_token_file" in exc_info.value.payload["msg"]


def test_instance_principal_auth_creates_client_with_instance_signer(monkeypatch):
    fake_oci = make_fake_oci(lambda **kwargs: {})
    monkeypatch.setitem(sys.modules, "oci", fake_oci)

    oci_auth = load_collection_module("oci_auth")
    client = oci_auth.create_service_client(
        DummyModule({"auth_type": "instance_principal"}),
        DummyClient,
    )

    assert client.config == {}
    assert client.signer == "instance-signer"


def test_resource_principal_auth_creates_client_with_resource_signer(monkeypatch):
    fake_oci = make_fake_oci(lambda **kwargs: {})
    monkeypatch.setitem(sys.modules, "oci", fake_oci)

    oci_auth = load_collection_module("oci_auth")
    client = oci_auth.create_service_client(
        DummyModule({"auth_type": "resource_principal"}),
        DummyClient,
    )

    assert client.config == {}
    assert client.signer == "resource-signer"


def test_session_token_auth_uses_security_token_file_from_loaded_config(
    monkeypatch,
    tmp_path,
):
    config_file = tmp_path / "config"
    config_file.write_text("[DEFAULT]\n", encoding="utf-8")
    key_file = tmp_path / "session.pem"
    token_file = tmp_path / "token"
    token_file.write_text("session-token\n", encoding="utf-8")

    fake_oci = make_fake_oci(
        lambda **kwargs: {
            "key_file": str(key_file),
            "security_token_file": str(token_file),
        }
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)

    oci_auth = load_collection_module("oci_auth")
    client = oci_auth.create_service_client(
        DummyModule(
            {
                "auth_type": "session_token",
                "config_file_location": str(config_file),
                "config_profile_name": "DEFAULT",
            }
        ),
        DummyClient,
    )

    assert client.config["security_token_file"] == str(token_file)
    assert client.signer == (
        "session-signer",
        "session-token",
        f"private-key:{key_file}",
    )


def test_api_key_auth_validates_loaded_config(monkeypatch, tmp_path):
    config_file = tmp_path / "config"
    config_file.write_text("[DEFAULT]\n", encoding="utf-8")

    validated_configs = []
    fake_oci = make_fake_oci(
        lambda **kwargs: {
            "tenancy": "ocid1.tenancy.oc1..example",
            "user": "ocid1.user.oc1..example",
            "region": "us-phoenix-1",
            "fingerprint": "fingerprint",
            "key_file": str(tmp_path / "api_key.pem"),
        }
    )
    fake_oci.config.validate_config = lambda config: validated_configs.append(config.copy())
    monkeypatch.setitem(sys.modules, "oci", fake_oci)

    oci_auth = load_collection_module("oci_auth")
    client = oci_auth.create_service_client(
        DummyModule(
            {
                "auth_type": "api_key",
                "config_file_location": str(config_file),
                "config_profile_name": "DEFAULT",
            }
        ),
        DummyClient,
    )

    assert validated_configs == [client.config]
