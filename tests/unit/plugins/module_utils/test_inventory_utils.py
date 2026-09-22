from __future__ import absolute_import, division, print_function
__metaclass__ = type

import sys
import types
from unittest.mock import Mock

import pytest

from .conftest import load_collection_module


class InventoryClient:
    def __init__(self, config=None, signer=None):
        self.config = config
        self.signer = signer
        self.base_client = types.SimpleNamespace(set_region=Mock())


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


def test_get_oci_config_from_options_uses_profile_and_explicit_values(
    monkeypatch,
    tmp_path,
):
    config_file = tmp_path / "inventory-config"
    config_file.write_text("[INVENTORY]\n", encoding="utf-8")
    loaded_calls = []
    fake_oci = make_fake_oci(
        lambda **kwargs: loaded_calls.append(kwargs) or {"region": "us-phoenix-1"}
    )
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    inventory_utils = load_collection_module("inventory_utils.oci_inventory")
    monkeypatch.setattr(
        inventory_utils.os.path, "isfile", lambda path: path == str(config_file)
    )

    options = {
        "config_file_location": str(config_file),
        "config_profile_name": "INVENTORY",
        "tenancy": "ocid1.tenancy.oc1..example",
        "api_user": "ocid1.user.oc1..example",
        "api_user_fingerprint": "fingerprint",
        "api_user_key_file": "/tmp/key.pem",
        "api_user_key_pass_phrase": "passphrase",
    }
    config = inventory_utils.get_oci_config_from_options(options)

    assert loaded_calls == [
        {"file_location": str(config_file), "profile_name": "INVENTORY"}
    ]
    assert config == {
        "region": "us-phoenix-1",
        "tenancy": "ocid1.tenancy.oc1..example",
        "user": "ocid1.user.oc1..example",
        "fingerprint": "fingerprint",
        "key_file": "/tmp/key.pem",
        "pass_phrase": "passphrase",
    }
    assert inventory_utils.get_oci_config_from_options(
        {"auth_type": "instance_principal"}
    ) == {"auth_type": "instance_principal"}


def test_create_service_client_from_options_handles_all_auth_types(
    monkeypatch,
    tmp_path,
):
    fake_oci = make_fake_oci(lambda **kwargs: {})
    monkeypatch.setitem(sys.modules, "oci", fake_oci)
    inventory_utils = load_collection_module("inventory_utils.oci_inventory")

    client = inventory_utils.create_service_client_from_options(
        {"auth_type": "instance_principal"}, InventoryClient, "us-ashburn-1"
    )
    assert client.signer == "instance-signer"
    client.base_client.set_region.assert_called_once_with("us-ashburn-1")

    client = inventory_utils.create_service_client_from_options(
        {"auth_type": "resource_principal"}, InventoryClient
    )
    assert client.signer == "resource-signer"

    config = {"key_file": "/tmp/key.pem"}
    monkeypatch.setattr(
        inventory_utils, "get_oci_config_from_options", lambda options: config
    )
    client = inventory_utils.create_service_client_from_options({}, InventoryClient)
    assert client.config == config

    token_file = tmp_path / "token"
    token_file.write_text("session-token\n", encoding="utf-8")
    monkeypatch.setattr(
        inventory_utils,
        "get_oci_config_from_options",
        lambda options: {
            "key_file": "/tmp/session.pem",
            "security_token_file": str(token_file),
        },
    )
    client = inventory_utils.create_service_client_from_options(
        {"auth_type": "session_token"}, InventoryClient
    )
    assert client.signer == (
        "session-signer",
        "session-token",
        "private-key:/tmp/session.pem",
    )

    monkeypatch.setattr(
        inventory_utils, "get_oci_config_from_options", lambda options: {}
    )
    with pytest.raises(ValueError, match="security_token_file"):
        inventory_utils.create_service_client_from_options(
            {"auth_type": "session_token"}, InventoryClient
        )
