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


def test_to_dict_serializes_oci_sdk_style_model_properties():
    oci_common = load_collection_module("oci_common")

    result = oci_common.to_dict(FakeOciModel())

    assert result == {
        "id": "ocid1.vcn.oc1..example",
        "display_name": "example-vcn",
        "cidr_blocks": ["10.0.0.0/16"],
        "nested": {"name": "nested-resource"},
    }
