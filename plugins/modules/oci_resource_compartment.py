#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: oci_resource_compartment
short_description: Move an OCI resource to another compartment
description:
  - Move one existing resource through the OCI Identity bulk-move API.
  - Discover the resource and supported move types at runtime.
  - Support requires both OCI Identity bulk move and Resource Search.
  - >-
    Currently unsupported by this module: bastions, DNS resolvers, compartments, identity domains, identity policies,
    dynamic routing gateways, network load balancers, network firewalls and their policies, OKE clusters and node pools,
    volume backup policies, web application firewalls and their policies.
notes:
  - O(wait_timeout) sets a polling deadline after OCI accepts the move.
  - Initial discovery and submission retries are outside this deadline.
  - An active HTTP request can finish after the deadline. Late responses cannot produce successful completion.
  - Connection and read timeouts limit individual network waits, not total module execution time.
version_added: "1.3.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_wait_options
options:
  resource_id:
    description:
      - The resource OCID, including for Object Storage buckets.
    type: str
    required: true
  target_compartment_id:
    description:
      - The destination compartment OCID in the same tenancy.
      - Use the tenancy OCID for the root compartment.
    type: str
    required: true
'''

EXAMPLES = r'''
- name: Move an instance
  ansible.oci.oci_resource_compartment:
    resource_id: "{{ instance_id }}"
    target_compartment_id: "{{ destination_compartment_id }}"

- name: Move a bucket
  ansible.oci.oci_resource_compartment:
    resource_id: "{{ bucket_ocid }}"
    target_compartment_id: "{{ destination_compartment_id }}"
'''

RETURN = r'''
resource_id:
  description: The requested resource OCID.
  returned: always
  type: str
resource_type:
  description: The discovered resource type. Unchanged tasks use the Search type.
  returned: after discovery
  type: str
previous_compartment_id:
  description: The compartment reported by the initial Search result.
  returned: after discovery
  type: str
target_compartment_id:
  description: The requested destination compartment.
  returned: always
  type: str
work_request_id:
  description: The work request OCID.
  returned: after submission
  type: str
work_request_status:
  description: The last observed work request status.
  returned: after polling the work request
  type: str
resource:
  description: The Search summary. This differs from a service-specific resource response.
  returned: when unchanged, in check mode, or after verified completion
  type: dict
'''

import re
import time
import uuid

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import (
    create_service_client,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_base import (
    OciModuleBase,
    oci,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    DEAD_STATES,
    OCI_AUTH_ARGS,
    OCI_WAIT_ARGS,
    filter_resources_by_response_field,
    serialize_oci_model,
)


class OciCompartmentMove(OciModuleBase):
    """Discover and move one resource through the common OCI APIs.

    Attributes:
        search (ResourceSearchClient): Client for resource discovery.
        work (WorkRequestClient or None): Client created when an accepted move needs polling.
        result (dict): Ansible result, including any accepted move details.
    """

    @property
    def client_class(self):
        """Return the Identity client class after the shared SDK check."""
        return oci.identity.IdentityClient

    def __init__(self, module):
        """Create the clients through the collection authentication helper.

        Args:
            module (AnsibleModule): Active module with authentication and move inputs.
        """
        super().__init__(module)
        self.search = create_service_client(
            module, oci.resource_search.ResourceSearchClient
        )
        self.work = None

        if module.params.get('region'):
            self.search.base_client.set_region(module.params['region'])

        self.result = dict(
            changed=False,
            resource_id=module.params['resource_id'],
            target_compartment_id=module.params['target_compartment_id'],
        )

    def get_tenancy_id(self):
        """Resolve the tenancy from module inputs, configuration, or the signer.

        Returns:
            str: The resolved tenancy OCID.

        Raises:
            ValueError: No tenancy is available.
        """
        base_client = self.client.base_client
        tenancy_id = (
            self.module.params.get('tenancy')
            or base_client.config.get('tenancy')
            or getattr(base_client.signer, 'tenancy_id', None)
        )
        if not tenancy_id:
            raise ValueError('Set tenancy to identify the current tenancy.')

        return tenancy_id

    def configure_identity(self):
        """Route Identity calls to the tenancy home region.

        Search continues to use the configured resource region.

        Returns:
            str: Home region used for Identity and later work request polling.

        Raises:
            ValueError: The tenancy or its home region cannot be determined.
        """
        regions = self.list_all_resources(
            self.client.list_region_subscriptions, self.get_tenancy_id()
        )
        home_region = next(
            (region.region_name for region in regions if region.is_home_region),
            None,
        )
        if not home_region:
            raise ValueError('OCI did not return a tenancy home region.')

        self.client.base_client.set_region(home_region)
        return home_region

    def find_resource(self, resource_type=None, deadline=None):
        """Find the exact resource OCID through Search.

        Search permits expanded fields only for a specific resource type.
        The initial lookup discovers that type without a local mapping.

        Args:
            resource_type (str, optional): Search type for an expanded lookup.
                If omitted, search all types using the common fields.
            deadline (float, optional): Shared deadline during destination verification.

        Returns:
            ResourceSummary or None: The exact match, or None if no match exists.

        Raises:
            ValueError: The Search type is invalid or multiple exact matches exist.
        """
        selector = 'all'
        if resource_type:
            if not re.fullmatch(r'\w+', resource_type, flags=re.ASCII):
                raise ValueError('OCI returned an invalid Search resource type.')
            selector = resource_type

        fields = ' return allAdditionalFields' if resource_type else ''
        resource_id = self.module.params['resource_id']
        query = "query {} resources{} where identifier = '{}'".format(
            selector, fields, resource_id
        )

        details = oci.resource_search.models.StructuredSearchDetails(query=query)
        if deadline is None:
            resources = self.list_all_resources(self.search.search_resources, details)
        else:
            resources = self.list_during_wait(
                self.search, self.search.search_resources, deadline,
                'OCI completed the move, but Search did not report the destination before the timeout.',
                details,
            )
        matches = filter_resources_by_response_field(
            resources, 'identifier', resource_id
        )
        if len(matches) > 1:
            raise ValueError('Search returned multiple records for the resource OCID.')

        return matches[0] if matches else None

    def get_move_type(self, resource):
        """Find the resource type advertised by OCI bulk-move discovery.

        Args:
            resource (ResourceSummary): Resource found through Search.

        Returns:
            BulkActionResourceType: OCI type name and required metadata keys.

        Raises:
            ValueError: OCI bulk move does not support the resource type.
        """
        supported_types = self.list_all_resources(
            self.client.list_bulk_action_resource_types,
            bulk_action_type='BULK_MOVE_RESOURCES',
        )
        for supported in supported_types:
            if supported.name.lower() == resource.resource_type.lower():
                return supported

        raise ValueError(
            'OCI bulk move does not support resource type: ' + resource.resource_type
        )

    @staticmethod
    def metadata_strings(*sources):
        """Merge metadata sources and retain only nonblank strings.

        Later sources replace earlier values only when the new value is valid.
        Preserve spaces within valid values.

        Args:
            *sources: Metadata dictionaries, or None when absent.

        Returns:
            dict[str, str]: Nonblank strings from the supplied sources.
        """
        values = {}
        for source in sources:
            values.update({
                key: value for key, value in (source or {}).items()
                if isinstance(value, str) and value.strip()
            })
        return values

    def resolve_metadata(self, resource, move_type):
        """Discover the additional identifiers required for the move.

        Prefer Search identity context. Fetch expanded fields only for missing identifiers.
        Bucket field names differ between Search and bulk move, so translate those two names locally.

        Args:
            resource (ResourceSummary): Initial resource with its source compartment.
            move_type (BulkActionResourceType): Type and metadata keys advertised by OCI.

        Returns:
            dict[str, str]: Required identifiers using bulk-move field names.

        Raises:
            ValueError: Required identifiers are unavailable or the source compartment changed.
        """
        required_keys = set(move_type.metadata_keys or [])
        values = self.metadata_strings(resource.identity_context)

        if required_keys - values.keys():
            expanded = self.find_resource(resource.resource_type)
            if expanded is None:
                raise ValueError(
                    'Search cannot retrieve additional identifiers for this resource.'
                )
            if expanded.compartment_id != resource.compartment_id:
                raise ValueError(
                    'The resource compartment changed during discovery. Run the task again.'
                )

            additional_details = expanded.additional_details or {}
            values.update(self.metadata_strings(additional_details, expanded.identity_context))

            if move_type.name.lower() == 'bucket':
                values['bucketName'] = values.get('bucketName') or expanded.display_name
                values['namespaceName'] = (
                    values.get('namespaceName') or additional_details.get('namespace')
                )

        missing = sorted(
            key for key in required_keys
            if not isinstance(values.get(key), str) or not values[key].strip()
        )
        if missing:
            raise ValueError(
                'Cannot discover required identifiers for ' + move_type.name
                + ': ' + ', '.join(missing)
                + '. Check Search permissions and indexing. This resource cannot be moved automatically.'
            )

        return {key: values[key] for key in required_keys}

    def list_during_wait(self, client, fn, deadline, message, *args, **kwargs):
        """Read all pages within the shared polling deadline.

        Args:
            client (object): SDK client that owns the operation.
            fn (Callable): SDK list or search operation.
            deadline (float): Shared monotonic deadline.
            message (str): Timeout message for the current phase.
            *args: Positional operation arguments.
            **kwargs: Keyword operation arguments.

        Returns:
            list: Records collected through the shared paginator.

        Raises:
            TimeoutError: The deadline expires.
            Exception: A nonretryable SDK failure occurs.
        """
        def fetch_page(*page_args, **page_kwargs):
            """Read one page using the remaining polling time."""
            return self.call_during_wait(
                client, fn, deadline, message, *page_args, **page_kwargs
            )

        return self.list_all_resources(fetch_page, *args, **kwargs)

    def call_during_wait(self, client, fn, deadline, message, *args, **kwargs):
        """Read one SDK response with retries bounded by the shared deadline.

        Disable operation retries and handle transient failures here.
        Pagination receives only success or a nonretryable failure.
        An active network request can finish late; reject its response in that case.

        Args:
            client (object): SDK client that owns the operation.
            fn (Callable): SDK read operation.
            deadline (float): Shared monotonic deadline.
            message (str): Timeout message for the current phase.
            *args: Positional operation arguments.
            **kwargs: Keyword operation arguments.

        Returns:
            Response: SDK response received before the deadline.

        Raises:
            TimeoutError: The deadline expires.
            Exception: A nonretryable SDK failure occurs.
        """
        checker = oci.retry.retry_checkers.TimeoutConnectionAndServiceErrorRetryChecker()
        kwargs['retry_strategy'] = oci.retry.NoneRetryStrategy()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(message)

            original_timeout = client.base_client.timeout
            connect_timeout, read_timeout = original_timeout
            client.base_client.timeout = (
                min(connect_timeout, remaining / 2),
                min(read_timeout, remaining / 2),
            )
            try:
                response = fn(*args, **kwargs)
            except Exception as exc:
                if not checker.should_retry(exception=exc):
                    raise
            else:
                if time.monotonic() >= deadline:
                    raise TimeoutError(message)
                return response
            finally:
                client.base_client.timeout = original_timeout

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(message)
            time.sleep(min(self.module.params['wait_interval'], remaining))

    def poll(self, fetch, complete, deadline, message):
        """Poll one phase using the deadline shared by both wait phases.

        Args:
            fetch (Callable): Function that returns the current value.
            complete (Callable): Function that returns True when the fetched value is complete.
            deadline (float): Deadline measured by the monotonic clock.
            message (str): Error message used when the deadline expires.

        Returns:
            object: The first fetched value for which complete returns True.

        Raises:
            TimeoutError: The phase remains incomplete after the deadline.
        """
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError(message)
            value = fetch()
            if time.monotonic() >= deadline:
                raise TimeoutError(message)
            completed = complete(value)
            if time.monotonic() >= deadline:
                raise TimeoutError(message)
            if completed:
                return value

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(message)

            time.sleep(min(self.module.params['wait_interval'], remaining))

    def wait_for_move(self, home_region):
        """Wait for successful work and destination visibility in Search.

        Both phases use one polling deadline. An active request can finish after that deadline.
        Failures preserve the accepted move details in the result.

        Args:
            home_region (str): Region used for bulk-move work requests.

        Returns:
            ResourceSummary: Resource observed in the destination compartment.

        Raises:
            ValueError: OCI reports a failed or unrecognized terminal work status.
            TimeoutError: Work completion or the Search update exceeds the shared deadline.
        """
        deadline = time.monotonic() + self.module.params['wait_timeout']
        self.work = create_service_client(self.module, oci.work_requests.WorkRequestClient)
        self.work.base_client.set_region(home_region)

        def fetch_work():
            """Read the work request while allowing delayed initial visibility.

            Returns:
                WorkRequest or None: Current request, or None while OCI returns 404.
            """
            try:
                response = self.call_during_wait(
                    self.work, self.work.get_work_request, deadline,
                    'Timed out waiting for the bulk-move work request.',
                    self.result['work_request_id']
                )
                return response.data
            except Exception as exc:
                if getattr(exc, 'status', None) == 404:
                    return None
                raise

        def work_complete(work):
            """Record the status and check work completion.

            Args:
                work (WorkRequest or None): Current work request, if visible.

            Returns:
                bool: True when the work request succeeded.

            Raises:
                ValueError: Work failed, was canceled, or has an unknown status.
            """
            if work is None:
                return False

            self.result['work_request_status'] = work.status
            if work.status in ('ACCEPTED', 'IN_PROGRESS', 'CANCELING'):
                return False

            if work.status != 'SUCCEEDED':
                message = 'Bulk move failed with status ' + work.status

                try:
                    errors = self.list_during_wait(
                        self.work, self.work.list_work_request_errors, deadline,
                        'Timed out retrieving work request errors.', self.result['work_request_id'],
                    )
                    message += ': ' + str(serialize_oci_model(errors))
                except Exception as exc:
                    message += '. Could not retrieve work request errors: ' + str(exc)
                raise ValueError(message)

            return True

        self.poll(
            fetch_work,
            work_complete,
            deadline,
            'Timed out waiting for the bulk-move work request.',
        )
        return self.poll(
            lambda: self.find_resource(deadline=deadline),
            lambda resource: (
                resource is not None
                and resource.compartment_id == self.module.params['target_compartment_id']
            ),
            deadline,
            'OCI completed the move, but Search did not report the destination before the timeout.',
        )

    def validate_arguments(self):
        """Validate resource identifiers and wait limits before Search queries.

        Raises:
            ValueError: An identifier is invalid or a wait limit is not positive.
        """
        for key in ('resource_id', 'target_compartment_id'):
            value = self.module.params[key]
            if not re.fullmatch(r'ocid1\.\w+\.[\w.:-]+', value, flags=re.ASCII):
                raise ValueError(key + ' must be an OCID.')

        if not self.module.params['target_compartment_id'].startswith(('ocid1.compartment.', 'ocid1.tenancy.')):
            raise ValueError('target_compartment_id must identify a compartment or tenancy.')

        target = self.module.params['target_compartment_id']
        if target.startswith('ocid1.tenancy.') and target != self.get_tenancy_id():
            raise ValueError('The root destination must match the configured tenancy OCID.')

        if self.module.params['wait_timeout'] <= 0 or self.module.params['wait_interval'] <= 0:
            raise ValueError('wait_timeout and wait_interval must be positive.')

    def submit_move(self, resource, move_type, metadata):
        """Submit one move and preserve the accepted request details.

        Reuse one token across submission retries to prevent duplicate requests.

        Args:
            resource (ResourceSummary): Resource and its source compartment.
            move_type (BulkActionResourceType): Type advertised by OCI.
            metadata (dict): Identifiers resolved during move preparation.

        Raises:
            ValueError: OCI accepts the move without a work request ID.
        """
        details = oci.identity.models.BulkMoveResourcesDetails(
            target_compartment_id=self.module.params['target_compartment_id'],
            resources=[
                oci.identity.models.BulkActionResource(
                    identifier=resource.identifier,
                    entity_type=move_type.name,
                    metadata=metadata,
                ),
            ],
        )
        reply = self.client.bulk_move_resources(
            resource.compartment_id,
            details,
            opc_retry_token=str(uuid.uuid4()),
        )
        self.result.update(
            changed=True,
            work_request_id=reply.headers.get('opc-work-request-id'),
        )
        if not self.result['work_request_id']:
            raise ValueError('OCI accepted the move without a work request ID.')

    def execute_module(self):
        """Validate, discover, submit, and report the move.

        Exit through Ansible with the result or an error that retains accepted move details.
        Check mode validates move feasibility without submitting a request.
        """
        try:
            self.validate_arguments()
            resource = self.find_resource()
            if resource is None:
                raise ValueError(
                    'Search cannot find the resource. Check its region, permissions, and indexing delay.'
                )
            if not resource.compartment_id or resource.lifecycle_state in DEAD_STATES:
                raise ValueError('Search returned a deleted resource or no source compartment.')

            self.result['resource_type'] = resource.resource_type
            self.result['previous_compartment_id'] = resource.compartment_id
            if resource.compartment_id == self.module.params['target_compartment_id']:
                self.result['resource'] = serialize_oci_model(resource)
            else:
                home_region = self.configure_identity()
                move_type = self.get_move_type(resource)
                self.result['resource_type'] = move_type.name
                metadata = self.resolve_metadata(resource, move_type)
                if self.module.check_mode:
                    self.result['changed'] = True
                    self.result['resource'] = serialize_oci_model(resource)
                else:
                    self.submit_move(resource, move_type, metadata)
                    if self.module.params['wait']:
                        self.result['resource'] = serialize_oci_model(self.wait_for_move(home_region))
        except Exception as exc:
            self.module.fail_json(msg=str(exc), **self.result)

        self.module.exit_json(**self.result)


def main():
    """Create the Ansible module and execute the compartment move.

    Authentication and wait arguments use the collection's shared definitions.
    """
    module = AnsibleModule(
        argument_spec=dict(
            OCI_AUTH_ARGS,
            **OCI_WAIT_ARGS,
            resource_id=dict(type='str', required=True),
            target_compartment_id=dict(type='str', required=True),
        ),
        supports_check_mode=True,
    )
    OciCompartmentMove(module).execute_module()


if __name__ == '__main__':
    main()
