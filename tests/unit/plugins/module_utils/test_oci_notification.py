from __future__ import absolute_import, division, print_function
__metaclass__ = type

import copy
import json

import pytest

from .conftest import load_collection_module


FULL_POLICY = json.dumps(
    {"backoffRetryPolicy": {"maxRetryDuration": 7200000, "policyType": "EXPONENTIAL"}}
)


@pytest.mark.parametrize("value", [None, ""])
def test_parse_deliver_policy_unset_returns_none(value):
    """Return None when the delivery policy is unset or empty."""
    helper = load_collection_module("oci_notification")
    assert helper.parse_deliver_policy(value) is None


@pytest.mark.parametrize("value", ["{not json", "plain text"])
def test_parse_deliver_policy_invalid_json_returns_none(value):
    """Return None instead of raising for invalid JSON."""
    helper = load_collection_module("oci_notification")
    assert helper.parse_deliver_policy(value) is None


@pytest.mark.parametrize("value", ["[]", '"text"', "42", "null"])
def test_parse_deliver_policy_non_dict_json_returns_none(value):
    """Return None when the JSON document is not an object."""
    helper = load_collection_module("oci_notification")
    assert helper.parse_deliver_policy(value) is None


@pytest.mark.parametrize("value", ["{}", '{"backoffRetryPolicy": null}'])
def test_parse_deliver_policy_without_backoff_policy(value):
    """Report an empty backoff retry policy when none is present."""
    helper = load_collection_module("oci_notification")
    assert helper.parse_deliver_policy(value) == {"backoff_retry_policy": None}


def test_parse_deliver_policy_full_policy_uses_snake_case():
    """Convert a full camelCase policy to the snake_case result shape."""
    helper = load_collection_module("oci_notification")
    assert helper.parse_deliver_policy(FULL_POLICY) == {
        "backoff_retry_policy": {
            "max_retry_duration": 7200000,
            "policy_type": "EXPONENTIAL",
        }
    }


@pytest.mark.parametrize("value", [None, "text", ["deliver_policy"]])
def test_normalize_subscription_result_non_dict_passthrough(value):
    """Return non-dict values unchanged."""
    helper = load_collection_module("oci_notification")
    assert helper.normalize_subscription_result(value) is value


def test_normalize_subscription_result_without_deliver_policy_keeps_delivery_policy():
    """Keep an existing delivery_policy when there is no deliver_policy key."""
    helper = load_collection_module("oci_notification")
    resource = {"id": "s1", "delivery_policy": {"backoff_retry_policy": None}}
    assert helper.normalize_subscription_result(resource) == resource


def test_normalize_subscription_result_converts_deliver_policy():
    """Replace deliver_policy with a parsed delivery_policy dict."""
    helper = load_collection_module("oci_notification")
    result = helper.normalize_subscription_result({"id": "s1", "deliver_policy": FULL_POLICY})
    assert "deliver_policy" not in result
    assert result["id"] == "s1"
    assert result["delivery_policy"]["backoff_retry_policy"]["max_retry_duration"] == 7200000


def test_normalize_subscription_result_unset_policy_is_none():
    """Report a None delivery_policy when deliver_policy is unset."""
    helper = load_collection_module("oci_notification")
    result = helper.normalize_subscription_result({"id": "s1", "deliver_policy": None})
    assert result == {"id": "s1", "delivery_policy": None}


def test_normalize_subscription_result_does_not_mutate_input():
    """Leave the input dict untouched when converting."""
    helper = load_collection_module("oci_notification")
    resource = {"id": "s1", "deliver_policy": FULL_POLICY}
    original = copy.deepcopy(resource)
    helper.normalize_subscription_result(resource)
    assert resource == original


@pytest.mark.parametrize(
    "value, expected",
    [
        ("https://hooks.slack.com/services/T000/B000/secret", "https://hooks.slack.com"),
        ("https://events.pagerduty.com/integration/key/enqueue", "https://events.pagerduty.com"),
        ("https://user:password@example.com:8443/path?token=1", "https://example.com:8443"),
        ("https://example.com:443/path", "https://example.com:443"),
        ("https://[2001:db8::1]:8443/path", "https://[2001:db8::1]:8443"),
        ("https://[2001:db8::1]/path", "https://[2001:db8::1]"),
        ("https://example.com:notaport/path", "https://example.com"),
        ("ops@example.com", None),
        ("+15555550100", None),
        ("ocid1.fnfunc.oc1..example", None),
        ("", None),
        (None, None),
    ],
)
def test_summarize_endpoint(value, expected):
    """Keep only the scheme, hostname, and port of URL endpoints."""
    helper = load_collection_module("oci_notification")
    assert helper.summarize_endpoint(value) == expected


def test_normalize_subscription_result_summarizes_endpoint():
    """Replace the endpoint with its scheme, hostname, and port."""
    helper = load_collection_module("oci_notification")
    resource = {"id": "s1", "endpoint": "https://hooks.slack.com/services/T000/B000/secret"}
    assert helper.normalize_subscription_result(resource) == {
        "id": "s1",
        "endpoint": "https://hooks.slack.com",
    }
