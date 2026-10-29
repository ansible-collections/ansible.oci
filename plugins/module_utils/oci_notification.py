"""Helpers shared by the OCI Notifications subscription modules."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import json
from urllib.parse import urlsplit


def parse_deliver_policy(value):
    """Convert the JSON delivery policy returned by get_subscription to a dict.

    ``Subscription.deliver_policy`` is a JSON string with camelCase keys, while
    ``SubscriptionSummary.delivery_policy`` from list_subscriptions is a model.
    This returns the same snake_case shape the summary model serializes to.

    Args:
        value: The ``deliver_policy`` JSON string, or None.

    Returns:
        A dict with a ``backoff_retry_policy`` entry, or None when the policy
        is unset or is not valid JSON.
    """
    if not value:
        return None
    try:
        policy = json.loads(value)
    except ValueError:
        return None
    if not isinstance(policy, dict):
        return None
    backoff = policy.get("backoffRetryPolicy")
    if not backoff:
        return {"backoff_retry_policy": None}
    return {
        "backoff_retry_policy": {
            "max_retry_duration": backoff.get("maxRetryDuration"),
            "policy_type": backoff.get("policyType"),
        }
    }


def summarize_endpoint(value):
    """Reduce a subscription endpoint to its scheme, hostname, and port.

    Slack and PagerDuty endpoints embed credentials in the URL path, so module
    results only report where notifications are sent, not the full URL.

    Args:
        value: The subscription endpoint, or None.

    Returns:
        The endpoint scheme, hostname, and port when one is set, such as
        ``https://hooks.slack.com`` or ``https://example.com:8443``, or None
        when the endpoint is not a URL, such as an email address.
    """
    if not value:
        return None
    parts = urlsplit(value)
    if not parts.scheme or not parts.hostname:
        return None
    host = parts.hostname
    if ":" in host:
        host = f"[{host}]"
    try:
        port = parts.port
    except ValueError:
        port = None
    if port is not None:
        host = f"{host}:{port}"
    return f"{parts.scheme}://{host}"


def normalize_subscription_result(resource_dict):
    """Normalize a serialized subscription for module results.

    Get responses carry ``deliver_policy`` as a JSON string and list responses
    carry ``delivery_policy`` as a model, so results would otherwise differ in
    shape depending on how the subscription was retrieved. The endpoint is
    reduced to its scheme, hostname, and port so credentials in it are not returned.

    Args:
        resource_dict: A serialized Subscription or SubscriptionSummary.

    Returns:
        A copy of ``resource_dict`` where ``deliver_policy`` is replaced by the
        parsed ``delivery_policy`` dict and ``endpoint`` is summarized.
    """
    if not isinstance(resource_dict, dict):
        return resource_dict
    result = dict(resource_dict)
    if "deliver_policy" in result:
        result["delivery_policy"] = parse_deliver_policy(result.pop("deliver_policy"))
    if "endpoint" in result:
        result["endpoint"] = summarize_endpoint(result["endpoint"])
    return result
