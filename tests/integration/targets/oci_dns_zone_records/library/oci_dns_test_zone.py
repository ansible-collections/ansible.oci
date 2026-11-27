#!/usr/bin/python
"""Create and remove disposable DNS zones for integration tests."""
from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import create_service_client
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import OCI_AUTH_ARGS


class FixtureCreationError(RuntimeError):
    """Carry IDs for resources created before fixture setup failed."""

    def __init__(self, message, zone_id=None, view_id=None):
        super(FixtureCreationError, self).__init__(message)
        self.zone_id = zone_id
        self.view_id = view_id


def _check_names_available(client, oci, params):
    """Reject name collisions before this test creates any resource.

    Args:
        client: Authenticated DNS client.
        oci: Imported OCI SDK module.
        params: Validated fixture parameters.

    Returns:
        None.
    """
    zones = oci.pagination.list_call_get_all_results(
        client.list_zones, compartment_id=params["compartment_id"],
        name=params["zone_name"], scope=params["scope"].upper(),
    ).data

    if zones:
        raise RuntimeError("A DNS zone with the fixture name already exists")

    if params["scope"] == "private":
        views = oci.pagination.list_call_get_all_results(
            client.list_views, compartment_id=params["compartment_id"]
        ).data
        if any(view.display_name == params["view_name"] for view in views):
            raise RuntimeError("A DNS view with the fixture name already exists")


def _create_fixture(client, oci, params):
    """Create a primary zone and an optional private view.

    Args:
        client: Authenticated DNS client.
        oci: Imported OCI SDK module.
        params: Validated fixture parameters.

    Returns:
        The created zone and optional view models.

    Raises:
        FixtureCreationError: When creation or activation fails after ownership starts.
    """
    _check_names_available(client, oci, params)
    zone_id = None
    view_id = None

    try:
        if params["scope"] == "private":
            response = client.create_view(oci.dns.models.CreateViewDetails(
                compartment_id=params["compartment_id"],
                display_name=params["view_name"],
            ))
            view_id = response.data.id
            view = oci.wait_until(
                client, response,
                max_wait_seconds=180,
                evaluate_response=lambda response: response.data.lifecycle_state in ("ACTIVE", "FAILED"),
                fetch_func=lambda **unused: client.get_view(view_id),
            ).data

            if view.lifecycle_state != "ACTIVE":
                raise RuntimeError("The temporary DNS view entered FAILED")
        else:
            view = None

        response = client.create_zone(oci.dns.models.CreateZoneDetails(
            name=params["zone_name"], zone_type="PRIMARY",
            compartment_id=params["compartment_id"],
            scope=params["scope"].upper(), view_id=view_id,
        ))
        zone_id = response.data.id
        zone = oci.wait_until(
            client, response,
            max_wait_seconds=180,
            evaluate_response=lambda response: response.data.lifecycle_state in ("ACTIVE", "FAILED"),
            fetch_func=lambda **unused: client.get_zone(
                zone_id, scope=params["scope"].upper()
            ),
        ).data

        if zone.lifecycle_state != "ACTIVE":
            raise RuntimeError("The temporary DNS zone entered FAILED")

        return zone, view
    except Exception as error:
        raise FixtureCreationError(
            str(error), zone_id=zone_id, view_id=view_id
        )


def _delete_and_wait(client, oci, getter, deleter, resource_id, **kwargs):
    """Delete one known resource ID and wait for its removal.

    Args:
        client: Authenticated DNS client.
        oci: Imported OCI SDK module.
        getter: SDK get operation for the resource.
        deleter: SDK delete operation for the resource.
        resource_id: ID returned by this fixture create operation.
        **kwargs: Scope arguments for the get and delete operations.

    Returns:
        None.
    """
    try:
        response = getter(resource_id, **kwargs)
    except oci.exceptions.ServiceError as error:
        if error.status == 404:
            return

        raise

    if response.data.lifecycle_state not in ("DELETING", "DELETED"):
        deleter(resource_id, **kwargs)

    oci.wait_until(
        client, response, "lifecycle_state", "DELETED",
        succeed_on_not_found=True, max_wait_seconds=180,
        max_interval_seconds=5,
        fetch_func=lambda **unused: getter(resource_id, **kwargs),
    )


def _remove_fixture(client, oci, params):
    """Remove only the resource IDs returned by this fixture creation.

    Args:
        client: Authenticated DNS client.
        oci: Imported OCI SDK module.
        params: Fixture parameters, including owned resource IDs.

    Returns:
        None.
    """
    if params.get("zone_id"):
        _delete_and_wait(
            client, oci, client.get_zone, client.delete_zone, params["zone_id"],
            scope=params["scope"].upper(),
        )

    if params["scope"] == "private" and params.get("view_id"):
        _delete_and_wait(
            client, oci, client.get_view, client.delete_view, params["view_id"]
        )


def main():
    """Create or remove a disposable DNS fixture."""
    argument_spec = dict(OCI_AUTH_ARGS)
    argument_spec.update(dict(
        state=dict(type="str", choices=["present", "absent"], required=True),
        scope=dict(type="str", choices=["global", "private"], required=True),
        zone_name=dict(type="str", required=True),
        view_name=dict(type="str"), compartment_id=dict(type="str", required=True),
        zone_id=dict(type="str"), view_id=dict(type="str"),
    ))
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(changed=True)

    params = module.params
    try:
        from ansible_collections.ansible.oci.plugins.module_utils.oci_base import oci
        client = create_service_client(module, oci.dns.DnsClient)

        if params["state"] == "absent":
            _remove_fixture(client, oci, params)
            module.exit_json(changed=bool(params.get("zone_id") or params.get("view_id")))

        zone, view = _create_fixture(client, oci, params)
        module.exit_json(changed=True, zone_id=zone.id,
                         view_id=view.id if view else None)
    except FixtureCreationError as error:
        module.fail_json(msg=str(error), zone_id=error.zone_id, view_id=error.view_id)
    except Exception as error:
        module.fail_json(msg=str(error))


if __name__ == "__main__":
    main()
