"""Waiter and retry utilities for OCI resources."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module_utils: oci_wait
short_description: Waiter and retry utilities for OCI API operations
description:
 - Provides wait_for_resource to poll an OCI resource until it reaches a target
 lifecycle state, with configurable timeout and failure state detection.
 - Includes wait_for_work_request for tracking OCI async work requests, and
 call_with_retry for exponential backoff retries on transient API errors.
author:
 - Steve Fulmer (@stevefulme1)
 - Ron Gershburg (@ronger4)
"""

try:
    import oci
    from oci.exceptions import ServiceError
    HAS_OCI_SDK = True
except ImportError:
    HAS_OCI_SDK = False

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    DEAD_STATES,
)


def list_all_resources(list_fn, *args, **kwargs):
    """Return all records from an OCI list operation."""
    if not HAS_OCI_SDK:
        raise ImportError("The 'oci' Python SDK is required.")

    return oci.pagination.list_call_get_all_results(list_fn, *args, **kwargs).data


def _resource_wait_complete(module, response, target_states, failure_states, resource_id):
    state = getattr(response.data, "lifecycle_state", None)
    if state in failure_states:
        module.fail_json(
            msg=f"Resource {resource_id} entered failure state: {state}",
        )
    return state in target_states


def _work_request_wait_complete(
    module,
    response,
    target_states,
    failure_states,
    work_request_id,
):
    state = getattr(response.data, "status", None)
    if state in failure_states:
        module.fail_json(
            msg=f"Work request {work_request_id} {state}",
        )
    return state in target_states


def _target_states_include_dead_states(target_states):
    return any(state in DEAD_STATES for state in target_states)


def wait_for_resource(
    module,
    client,
    get_fn,
    resource_id,
    target_states,
    failure_states=None,
):
    """Poll a resource until it reaches a target lifecycle state."""
    if not HAS_OCI_SDK:
        raise ImportError("The 'oci' Python SDK is required.")

    wait = module.params.get("wait", True)
    if not wait:
        return get_fn(resource_id).data

    timeout = module.params.get("wait_timeout", 1200)
    interval = module.params.get("wait_interval", 30)

    if failure_states is None:
        failure_states = frozenset({"FAILED"})

    try:
        initial_response = get_fn(resource_id)
    except ServiceError as e:
        if e.status == 404 and _target_states_include_dead_states(target_states):
            return None
        raise

    waiter_result = oci.wait_until(
        client,
        initial_response,
        max_interval_seconds=interval,
        max_wait_seconds=timeout,
        succeed_on_not_found=_target_states_include_dead_states(target_states),
        evaluate_response=lambda response: _resource_wait_complete(
            module,
            response,
            target_states,
            failure_states,
            resource_id,
        ),
        fetch_func=lambda response=None: get_fn(resource_id),
    )
    return getattr(waiter_result, "data", None)


def wait_for_work_request(
    module,
    client,
    work_request_id,
    get_work_request_fn=None,
    target_states=None,
    failure_states=None,
):
    """Wait for an OCI work request to complete."""
    if not HAS_OCI_SDK:
        raise ImportError("The 'oci' Python SDK is required.")

    timeout = module.params.get("wait_timeout", 1200)
    interval = module.params.get("wait_interval", 30)

    if get_work_request_fn is None:
        get_work_request_fn = client.get_work_request
    if target_states is None:
        target_states = ("SUCCEEDED", "COMPLETED")
    if failure_states is None:
        failure_states = frozenset({"FAILED", "CANCELED"})

    initial_response = get_work_request_fn(work_request_id)
    waiter_result = oci.wait_until(
        client,
        initial_response,
        max_interval_seconds=interval,
        max_wait_seconds=timeout,
        evaluate_response=lambda response: _work_request_wait_complete(
            module,
            response,
            target_states,
            failure_states,
            work_request_id,
        ),
        fetch_func=lambda response=None: get_work_request_fn(work_request_id),
    )
    return getattr(waiter_result, "data", None)


def call_with_retry(fn, *args, max_retries=3, retry_on=(429, 500, 503), **kwargs):
    """Call an OCI API function with exponential backoff retry."""
    if not HAS_OCI_SDK:
        raise ImportError("The 'oci' Python SDK is required.")

    retry_strategy = oci.retry.RetryStrategyBuilder(
        max_attempts_check=True,
        max_attempts=max_retries + 1,
        service_error_check=True,
        service_error_retry_config={status: [] for status in retry_on},
    ).get_retry_strategy()

    return retry_strategy.make_retrying_call(fn, *args, **kwargs)
