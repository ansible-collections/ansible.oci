from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.common.parameters import env_fallback

from conftest import load_collection_module


def test_filter_none_values_only_removes_none_entries():
    oci_common = load_collection_module("oci_common")

    result = oci_common.filter_none_values(
        {
            "string": "value",
            "none_value": None,
            "false_value": False,
            "zero_value": 0,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {},
        }
    )

    assert result == {
        "string": "value",
        "false_value": False,
        "zero_value": 0,
        "empty_string": "",
        "empty_list": [],
        "empty_dict": {},
    }


class FakeOciNestedModel:
    swagger_types = {"name": "str"}
    attribute_map = {"name": "name"}

    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name


class FakeOciModel:
    swagger_types = {
        "id": "str",
        "display_name": "str",
        "cidr_blocks": "list[str]",
        "nested": "FakeOciNestedModel",
    }
    attribute_map = {
        "id": "id",
        "display_name": "displayName",
        "cidr_blocks": "cidrBlocks",
        "nested": "nested",
    }

    def __init__(self):
        self._id = "ocid1.vcn.oc1..example"
        self._display_name = "example-vcn"
        self._cidr_blocks = ["10.0.0.0/16"]
        self._nested = FakeOciNestedModel("nested-resource")

    @property
    def id(self):
        return self._id

    @property
    def display_name(self):
        return self._display_name

    @property
    def cidr_blocks(self):
        return self._cidr_blocks

    @property
    def nested(self):
        return self._nested


def test_serialize_oci_model_serializes_oci_sdk_style_model_properties():
    oci_common = load_collection_module("oci_common")

    result = oci_common.serialize_oci_model(FakeOciModel())

    assert result == {
        "id": "ocid1.vcn.oc1..example",
        "display_name": "example-vcn",
        "cidr_blocks": ["10.0.0.0/16"],
        "nested": {"name": "nested-resource"},
    }


def test_oci_auth_args_define_defaults_and_env_fallbacks():
    oci_common = load_collection_module("oci_common")

    assert oci_common.OCI_AUTH_ARGS["config_file_location"]["default"] == "~/.oci/config"
    assert oci_common.OCI_AUTH_ARGS["config_file_location"]["fallback"] == (
        env_fallback,
        ["OCI_CONFIG_FILE"],
    )

    assert oci_common.OCI_AUTH_ARGS["config_profile_name"]["default"] == "DEFAULT"
    assert oci_common.OCI_AUTH_ARGS["config_profile_name"]["fallback"] == (
        env_fallback,
        ["OCI_CONFIG_PROFILE"],
    )

    assert oci_common.OCI_AUTH_ARGS["auth_type"]["default"] == "api_key"
    assert oci_common.OCI_AUTH_ARGS["auth_type"]["choices"] == [
        "api_key",
        "instance_principal",
        "resource_principal",
        "session_token",
    ]
    assert oci_common.OCI_AUTH_ARGS["auth_type"]["fallback"] == (
        env_fallback,
        ["OCI_AUTH_TYPE"],
    )

    expected_fallbacks = {
        "tenancy": ["OCI_TENANCY_ID"],
        "region": ["OCI_REGION"],
        "api_user": ["OCI_USER_ID"],
        "api_user_fingerprint": ["OCI_USER_FINGERPRINT"],
        "api_user_key_file": ["OCI_USER_KEY_FILE"],
        "api_user_key_pass_phrase": ["OCI_USER_KEY_PASS_PHRASE"],
    }

    for param_name, env_vars in expected_fallbacks.items():
        assert oci_common.OCI_AUTH_ARGS[param_name]["fallback"] == (
            env_fallback,
            env_vars,
        )
