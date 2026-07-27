"""Shared waiter, pagination, and retry helpers for OCI SDK calls."""

from __future__ import absolute_import, division, print_function
__metaclass__ = type

try:
    import oci
    from oci.exceptions import ServiceError
    HAS_OCI_SDK = True
except ImportError:
    HAS_OCI_SDK = False

from ansible_collections.oracle.oci.plugins.module_utils.oci_common import (
    DEAD_STATES,
    OCI_SDK_REQUIRED_MSG,
)


def list_all_resources(list_fn, *args, **kwargs):
    """Return every record from an OCI paginated list operation.

    ``list_fn`` is an OCI SDK list method. The helper requires the OCI SDK to
    be installed and returns the aggregated ``.data`` collection from all pages.
    """
    if not HAS_OCI_SDK:
        raise ImportError(OCI_SDK_REQUIRED_MSG)

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
    """Poll a resource until it reaches one of the requested lifecycle states.

    ``module`` supplies the ``wait``, ``wait_timeout``, and ``wait_interval``
    parameters. When waiting is disabled this helper performs one immediate
    ``get_fn(resource_id)`` call and returns its data. Otherwise it keeps
    polling until the resource reaches ``target_states`` or fails into
    ``failure_states``.
    """
    if not HAS_OCI_SDK:
        raise ImportError(OCI_SDK_REQUIRED_MSG)

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
    """Wait for an OCI asynchronous work request to finish.

    The helper polls ``get_work_request_fn`` until the work request enters one
    of ``target_states`` and returns the final OCI work request model. If the
    request enters ``failure_states``, the module fails immediately.
    """
    if not HAS_OCI_SDK:
        raise ImportError(OCI_SDK_REQUIRED_MSG)

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
    """Call an OCI SDK function with retry handling for transient failures.

    ``fn`` receives the provided positional and keyword arguments through the
    OCI retry strategy. The return value is whatever the wrapped OCI call
    returns after succeeding or exhausting the configured retry attempts.
    """
    if not HAS_OCI_SDK:
        raise ImportError(OCI_SDK_REQUIRED_MSG)

    retry_strategy = oci.retry.RetryStrategyBuilder(
        max_attempts_check=True,
        max_attempts=max_retries + 1,
        service_error_check=True,
        service_error_retry_config={status: [] for status in retry_on},
    ).get_retry_strategy()

    return retry_strategy.make_retrying_call(fn, *args, **kwargs)
