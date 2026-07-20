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
