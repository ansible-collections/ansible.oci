# Module Authoring Guide

This guide explains how to add a new module and a matching `*_info` module to
the `ansible.oci` collection.

It is intentionally collection-specific. It does not try to replace the general
Ansible contributor guides linked from `CONTRIBUTING.md`. Instead, it explains
how this codebase expects OCI modules to be built on top of the shared helper
layer in `plugins/module_utils/`.

## How This Collection Is Structured

Most modules in this collection should be thin adapters over shared base
classes. You do not need to reimplement authentication, pagination, waiting,
common argument handling, or the standard present/absent lifecycle.

Use this mental model:

```text
AnsibleModule
  -> OciModuleBase
     -> OciResourceBase    # resource-managing modules
     -> OciInfoBase        # read-only info modules
```

### What the base classes already do

Keep the concrete module thin:

- `OciModuleBase` handles client setup and result shaping.
- `OciResourceBase` handles the standard present/absent lifecycle.
- `OciInfoBase` handles the standard get/list read flow.

That means this guide focuses on what you write inside the concrete module
class, not every helper available in the base layer.

## Before You Start

Read these files before you add a new module:

1. `plugins/module_utils/oci_base.py`
   Learn what every concrete module gets from `OciModuleBase`.
2. `plugins/module_utils/oci_resource.py`
   Learn the required hooks and metadata for a resource module.
3. `plugins/module_utils/oci_info.py`
   Learn the metadata-only pattern used by most info modules.
4. `plugins/modules/oci_network_subnet.py`
   Use this as the standard resource-module reference.
5. `plugins/modules/oci_network_subnet_info.py`
   Use this as the standard info-module reference.
6. `plugins/modules/oci_network_vcn.py`
   Read this when your update flow is more complex than one OCI
   `update_*` call.
7. `tests/unit/plugins/modules/test_oci_resource_common.py`
   See the shared behavior expected from resource modules.
8. `tests/unit/plugins/modules/test_oci_info_common.py`
   See the shared behavior expected from info modules.

## Step 1: Decide Which Base Class You Need

Use `OciResourceBase` when the module creates, updates, or deletes an OCI
resource.

Use `OciInfoBase` when the module only reads OCI data and returns it to the
caller.

In most cases you will add both:

- `plugins/modules/oci_<resource>.py`
- `plugins/modules/oci_<resource>_info.py`

## Step 2: Build the Resource Module

### Required class attributes

Set these on your `OciResourceBase` subclass:

| Attribute | Why it is needed |
| --- | --- |
| `client_class` | Required by `OciModuleBase` so the OCI SDK client can be created. Define it as a `@property` (not a plain class attribute), so `oci.<Client>` is only resolved once the class is instantiated, after `OciModuleBase.__init__()` has already confirmed the SDK is installed. |
| `resource_id_param` | Tells the base class which module parameter is the explicit OCI ID. |
| `create_resource_name` | Used in validation and error messages. |
| `create_required_fields` | Fields that must exist before create is allowed. |

### Commonly needed class attributes

These are not always mandatory, but most standard modules need them:

| Attribute | Why it is usually needed |
| --- | --- |
| `list_resource_method` | Enables scoped name lookup against a list API. |
| `list_filter_params` | Adds extra list filters beyond `compartment_id` and becomes part of the required scope for name-based lookup. |
| `update_field_specs` | Declares which module parameters can trigger updates. |
| `update_method_name` | OCI SDK update method for the standard update flow. |
| `update_details_name` | Keyword name for the OCI update details object. |
| `update_wait_states` | Lifecycle states that mark the resource as settled after update. |

### Required methods

Implement these methods on the concrete module class:

| Method | What it does |
| --- | --- |
| `get_resource_response(resource_id)` | Returns the raw OCI SDK response for one resource. |
| `create_resource()` | Creates the resource and returns the final SDK model. |
| `delete_resource(resource)` | Deletes the resource, usually via `delete_resource_and_wait()`. |

### Standard update path

If the resource uses a normal OCI `update_*` API, also provide:

| Item | Purpose |
| --- | --- |
| `update_method_name` | Names the OCI SDK update method to call. |
| `update_details_name` | Names the update-details keyword argument. |
| `update_wait_states` | Defines the post-update waiter target states. |
| `build_update_details(update_model_fields)` | Builds the OCI SDK update details object. |

### When to override `update_resource()`

Override `update_resource()` only when the normal metadata-driven path is not
enough. A good example is `oci_network_vcn`, which performs strategy-driven
CIDR operations and work-request waits before or alongside the normal update
call.

### Resource module flow

The base class will do the following when you call
`execute_resource_module()`:

1. Read `state`
2. Resolve the target resource by ID or by scoped `name`
3. For `state=absent`
   - validate the delete request
   - skip if the resource is already gone
   - honor check mode
   - call `delete_resource()`
4. For `state=present`
   - create when no resource exists
   - update when the resource exists and drift is detected
   - return unchanged when no drift exists

That means your concrete module should focus on OCI-specific API calls and
module metadata, not lifecycle orchestration.

## Step 3: Use the Right Shared Arguments and Doc Fragments

For resource modules, start the argument spec with `OCI_COMMON_ARGS`. That pulls
in shared authentication, wait, tag, and name-lookup behavior.

`OCI_COMMON_ARGS` already includes these common module parameters:

- authentication settings from `OCI_AUTH_ARGS`
- waiter settings from `OCI_WAIT_ARGS`
- tag inputs `freeform_tags` and `defined_tags`
- name-lookup inputs `name`, `compartment_id`, and `allow_duplicate_name`

For info modules, start the argument spec with `OCI_AUTH_ARGS`. Info modules do
not use the resource wait/tag/name-lookup bundle.

Use these documentation fragments:

### Resource modules

- `ansible.oci.oci_auth_options`
- `ansible.oci.oci_name_lookup_options`
- `ansible.oci.oci_wait_options`
- `ansible.oci.oci_tags_options`

### Info modules

- `ansible.oci.oci_auth_options`
- `ansible.oci.oci_info_filter_options`

## Resource Module Skeleton

The following skeleton follows the same structure as `oci_network_subnet.py`. Replace
the placeholder names with your real OCI service, methods, and models.

```python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_example_resource
short_description: Manage an Example resource in Oracle Cloud Infrastructure
description:
  - Create, update, and delete an OCI example resource.
version_added: "1.0.0"
author:
  - Your Name (@github-handle)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired lifecycle state of the resource.
    type: str
    choices: [present, absent]
    default: present
  example_resource_id:
    description:
      - The OCID of the resource.
    type: str
  name:
    description:
      - Human-readable display name for the resource.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment.
    type: str
  project_id:
    description:
      - The OCID of the parent project used to scope the resource.
    type: str
"""

EXAMPLES = r"""
- name: Create an example resource
  ansible.oci.oci_example_resource:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    project_id: ocid1.project.oc1..example
    name: example-resource
  register: created_example

- name: Reconcile a uniquely named example resource by name
  ansible.oci.oci_example_resource:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    project_id: ocid1.project.oc1..example
    name: example-resource

- name: Intentionally create a second example resource with the same display name
  ansible.oci.oci_example_resource:
    state: present
    allow_duplicate_name: true
    compartment_id: ocid1.compartment.oc1..example
    project_id: ocid1.project.oc1..example
    name: example-resource

- name: Delete the created example resource
  ansible.oci.oci_example_resource:
    state: absent
    example_resource_id: "{{ created_example.resource.id }}"

- name: Delete a uniquely named example resource without providing example_resource_id
  ansible.oci.oci_example_resource:
    state: absent
    compartment_id: ocid1.compartment.oc1..example
    project_id: ocid1.project.oc1..example
    name: example-resource
"""

RETURN = r"""
resource:
  description: The example resource.
  returned: when state != absent
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    LIFECYCLE_AVAILABLE,
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
)

oci, HAS_OCI_SDK = import_oci_sdk()

CREATE_REQUIRED_FIELDS = (
    "compartment_id",
    "project_id",
    "name",
)
WAIT_FOR_EXAMPLE_STATES = (LIFECYCLE_AVAILABLE,)


def build_create_example_details(params):
    details = filter_none_values(
        {
            "compartment_id": params.get("compartment_id"),
            "project_id": params.get("project_id"),
            "display_name": params.get("name"),
        }
    )
    return oci.example.models.CreateExampleDetails(**details)


class OciExampleResourceModule(OciResourceBase):
    @property
    def client_class(self):
        return oci.example.ExampleClient

    resource_id_param = "example_resource_id"
    list_resource_method = "list_example_resources"
    list_filter_params = ("project_id",)
    create_resource_name = "example resource"
    create_required_fields = CREATE_REQUIRED_FIELDS
    update_method_name = "update_example_resource"
    update_details_name = "update_example_resource_details"
    update_wait_states = WAIT_FOR_EXAMPLE_STATES
    update_field_specs = (
        {
            "param_name": "name",
            "resource_field": "display_name",
            "update_field": "display_name",
            "is_mutable": True,
        },
    )

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_example_resource,
            example_resource_id=resource_id,
        )

    def create_resource(self):
        response = self.call_with_retry(
            self.client.create_example_resource,
            create_example_resource_details=build_create_example_details(
                self.module.params
            ),
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_EXAMPLE_STATES,
        )

    def build_update_details(self, update_model_fields):
        return oci.example.models.UpdateExampleResourceDetails(
            **update_model_fields
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.delete_example_resource,
            example_resource_id=resource.id,
        )


def main():
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        example_resource_id=dict(type="str"),
        project_id=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    OciExampleResourceModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
```

## Resource Skeleton Walkthrough

Read the skeleton from top to bottom in this order:

1. `DOCUMENTATION`, `EXAMPLES`, and `RETURN`
   - keep the public module contract clear
   - extend the correct doc fragments
2. `argument_spec`
   - start with `OCI_COMMON_ARGS`
   - add only resource-specific fields after that
3. `client_class`
   - pick the OCI SDK client for the service
   - define it as a `@property`, not a plain class attribute
4. `resource_id_param`
   - define the explicit ID parameter used for update/delete targeting
5. `list_resource_method`
   - add this when you want `name`-based lookup
6. `list_filter_params`
   - each value is forwarded into the list API
   - for resource modules, these fields also become required scope when a caller
     uses `name` lookup
7. `create_required_fields`
   - include every field that must exist before create is valid
8. `update_field_specs`
   - describe the mutable and immutable fields
   - do not re-add `freeform_tags` and `defined_tags` unless you are replacing
     the base behavior, because `OciResourceBase` already injects tag update
     handling through `common_update_field_specs`
   - use `resource_field` when the OCI model field differs from the module
     parameter name
   - use `compare: "sorted_list"` for list fields where order should not matter
9. `get_resource_response()`
   - return the raw SDK response, not only `response.data`
10. `create_resource()`
   - make the OCI create call
   - pass the result through `get_mutation_result()` so wait behavior stays
     consistent
11. `build_update_details()`
    - keep it small and map the planned update fields into the OCI SDK model
12. `delete_resource()`
    - prefer `delete_resource_and_wait()` unless the resource needs custom
      delete behavior
13. `main()`
    - create `AnsibleModule`
    - enable `supports_check_mode=True`
    - hand control to `execute_resource_module()`

## Step 4: Build the Info Module

Info modules are usually much smaller because `OciInfoBase` already implements
the main read flow.

### Required class attributes

| Attribute | Why it is needed |
| --- | --- |
| `client_class` | Required by `OciModuleBase`. Define it as a `@property` (not a plain class attribute) for the same reason as resource modules — see the note above. |
| `results_key` | Defines the key returned in `exit_json()`. |

### Fetch metadata

Most info modules need some or all of the following:

| Attribute | Why it is used |
| --- | --- |
| `resource_id_param` | Tells the base class which parameter identifies a single resource. |
| `resource_get_method` | OCI SDK getter used when the ID is provided. |
| `list_resource_method` | OCI SDK list method used when listing resources. |
| `list_filter_params` | Parameters that should be forwarded into the list call. |

### Info module flow

When you call `execute_info_module()`, the base class:

1. checks whether the caller supplied the explicit resource ID
2. fetches one resource when an ID is present
3. otherwise calls the configured list method
4. passes supported filters into the list call
5. applies the local `name` filter
6. serializes results and returns `changed=False`

## Info Module Skeleton

The following skeleton follows the same pattern as `oci_network_subnet_info.py`.

```python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_example_resource_info
short_description: Retrieve Example resource information from Oracle Cloud Infrastructure
description:
  - Retrieve one or more OCI example resources.
version_added: "1.0.0"
author:
  - Your Name (@github-handle)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_info_filter_options
options:
  compartment_id:
    description:
      - The OCID of the compartment used for list operations.
    type: str
  example_resource_id:
    description:
      - The OCID of one specific resource.
    type: str
"""

EXAMPLES = r"""
- name: List example resources in a compartment
  ansible.oci.oci_example_resource_info:
    compartment_id: ocid1.compartment.oc1..example

- name: Get one example resource
  ansible.oci.oci_example_resource_info:
    example_resource_id: ocid1.example.oc1..example
"""

RETURN = r"""
example_resources:
  description: List of example resources that matched the query.
  returned: always
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_info import (
    OciInfoBase,
)

oci, HAS_OCI_SDK = import_oci_sdk()


class OciExampleResourceInfoModule(OciInfoBase):
    @property
    def client_class(self):
        return oci.example.ExampleClient

    results_key = "example_resources"
    resource_id_param = "example_resource_id"
    resource_get_method = "get_example_resource"
    list_resource_method = "list_example_resources"
    list_filter_params = (
        "compartment_id",
        "lifecycle_state",
    )


def main():
    argument_spec = dict(
        OCI_AUTH_ARGS,
        compartment_id=dict(type="str"),
        example_resource_id=dict(type="str"),
        name=dict(type="str"),
        lifecycle_state=dict(type="str"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_one_of=[("compartment_id", "example_resource_id")],
    )

    OciExampleResourceInfoModule(module).execute_info_module()


if __name__ == "__main__":
    main()
```

## Info Skeleton Walkthrough

Use this checklist when writing the info module:

1. start with `OCI_AUTH_ARGS`
2. define `results_key` to match the returned collection name
3. set `resource_id_param` and `resource_get_method` for single-resource fetch
4. set `list_resource_method` and `list_filter_params` for list operations
5. add `required_one_of` when the module should allow either ID lookup or list
   scope
6. call `execute_info_module()` and let the base class handle the rest

Compared to the resource module, the info module does not need:

- `state`
- update metadata
- create/delete methods
- wait settings
- tag helper arguments

## Step 5: Handle Updates Carefully

The most important design choice in a resource module is how updates work.

### Use `update_field_specs` for normal updates

This is the preferred pattern for most resources. Each entry describes one
module parameter and how it maps to the current OCI model and update payload.

Common keys:

| Key | Meaning |
| --- | --- |
| `param_name` | Module parameter name. |
| `resource_field` | Current OCI model field to compare against. |
| `update_field` | Field name used in the OCI update details model. |
| `is_mutable` | Whether updates are allowed after create. |
| `immutable_reason` | Extra detail when an update must fail. |
| `compare` | Comparison strategy such as `sorted_list`. |
| `strategy` | Custom planner method for complex update behavior. |

### Override `update_resource()` for advanced flows

Use a custom `update_resource()` when:

- one desired change expands into multiple OCI API calls
- a work request must be tracked outside the normal helper flow
- the update plan includes strategy operations that must run before the final
  update call

`oci_network_vcn.py` is the reference for this pattern.

## Step 6: Add Tests

At minimum, mirror the structure already used by the collection:

- add or extend a resource-module test in
  `tests/unit/plugins/modules/test_oci_<resource>.py`
- add or extend an info-module test in
  `tests/unit/plugins/modules/test_oci_<resource>_info.py` when the module has
  dedicated tests
- make sure the shared expectations in
  `tests/unit/plugins/modules/test_oci_resource_common.py` and
  `tests/unit/plugins/modules/test_oci_info_common.py` still make sense

For helper-level behavior, look at:

- `tests/unit/plugins/module_utils/test_oci_resource_and_info.py`
- `tests/unit/plugins/module_utils/test_oci_common.py`
- `tests/unit/plugins/module_utils/test_oci_auth.py`

## Step 7: Final Checklist

Before opening a pull request, confirm the module pair does all of the
following:

1. uses the correct base class
2. defines the required class attributes
3. implements the required methods
4. uses the correct shared args and documentation fragments
5. handles create, read, update, delete, or info flow through the shared base
6. includes unit-test coverage that matches nearby modules
7. documents the public module interface clearly

If your module follows the `oci_network_subnet` and `oci_network_subnet_info` patterns first,
you will usually stay aligned with the rest of this collection.
