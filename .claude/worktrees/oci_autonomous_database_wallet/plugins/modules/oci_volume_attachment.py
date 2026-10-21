# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_volume_attachment
short_description: Manage a block volume attachment resource in Oracle Cloud Infrastructure
description:
  - Attach a block volume to a compute instance and detach it again.
  - Supports the C(iscsi) and C(paravirtualized) attachment types.
  - A volume attachment has no update operation in OCI, so every configuration
    field is fixed at attach time. Changing C(instance_id), C(volume_id),
    C(device), C(read_only), C(shareable), C(type), C(use_chap),
    C(encryption_in_transit_type), C(pv_encryption_in_transit_enabled), or
    C(name) for an existing attachment is rejected; detach and re-attach
    instead.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - Create requests must omit C(volume_attachment_id). After attach, capture the
    returned attachment ID and use it for later C(state=present) and
    C(state=absent) tasks.
version_added: "1.0.0"
author:
  - Ron Gershburg (@ronger4)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
options:
  state:
    description:
      - The desired lifecycle state of the volume attachment.
      - C(present) attaches the volume, C(absent) detaches it.
    type: str
    choices: [present, absent]
    default: present
  volume_attachment_id:
    description:
      - The OCID of the volume attachment.
      - When provided, the module manages this exact attachment.
      - Required to distinguish between multiple attachments that share the
        same scoped C(name).
    type: str
  name:
    description:
      - Human-readable name for the volume attachment.
      - When C(volume_attachment_id) is omitted, the module uses
        C(compartment_id + instance_id + volume_id + name) to find an existing
        attachment.
      - If exactly one attachment matches, C(state=present) manages it as the
        target and C(state=absent) detaches it.
      - If more than one attachment matches, the task fails and the caller must
        supply C(volume_attachment_id).
    type: str
  compartment_id:
    description:
      - The OCID of the compartment used to scope name-based attachment lookups
        when C(volume_attachment_id) is omitted.
      - This is not part of the OCI attach payload (the attachment inherits its
        compartment from the instance), but it is required to scope the list
        call used for name-based lookup.
    type: str
  instance_id:
    description:
      - The OCID of the compute instance to attach the volume to.
      - Required when creating an attachment.
      - The module does not move an existing attachment to another instance.
    type: str
  volume_id:
    description:
      - The OCID of the block volume to attach.
      - Required when creating an attachment.
      - The module does not move an existing attachment to another volume.
    type: str
  type:
    description:
      - The attachment type to use when attaching the volume.
      - When omitted at create time, the volume is attached as
        C(paravirtualized).
      - Omit this on later C(state=present) tasks unless you intend to
        detect drift against the current attachment type. A default value
        would make every omitted-type rerun look like C(paravirtualized).
    type: str
    choices: [iscsi, paravirtualized]
  device:
    description:
      - The device name to expose the attached volume as on the instance
        (for example C(/dev/oracleoci/oraclevdb)).
    type: str
  read_only:
    description:
      - Whether to attach the volume in read-only mode.
      - Returned by OCI as C(is_read_only).
    type: bool
  shareable:
    description:
      - Whether the volume attachment is shareable across instances.
      - Returned by OCI as C(is_shareable).
    type: bool
  use_chap:
    description:
      - Whether to use CHAP authentication for the iSCSI attachment.
      - Only used when C(type=iscsi).
    type: bool
  encryption_in_transit_type:
    description:
      - The iSCSI encryption-in-transit mode to request.
      - Only used when C(type=iscsi).
    type: str
    choices: [none, bm_encryption_in_transit]
  pv_encryption_in_transit_enabled:
    description:
      - Whether to enable in-transit encryption for the paravirtualized
        attachment.
      - Only used when C(type=paravirtualized).
      - Returned by OCI as C(is_pv_encryption_in_transit_enabled).
    type: bool
notes:
  - iSCSI CHAP credentials (C(chap_username) and C(chap_secret)) are omitted
    from returned resources.
"""

EXAMPLES = r"""
- name: Attach a volume as a paravirtualized device
  ansible.oci.oci_volume_attachment:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    volume_id: ocid1.volume.oc1..example
    name: example-attachment
    type: paravirtualized
  register: created_attachment

- name: Attach a volume over iSCSI in read-only mode
  ansible.oci.oci_volume_attachment:
    state: present
    compartment_id: ocid1.compartment.oc1..example
    instance_id: ocid1.instance.oc1..example
    volume_id: ocid1.volume.oc1..example
    name: example-iscsi-attachment
    type: iscsi
    read_only: true
    device: /dev/oracleoci/oraclevdb

- name: Detach the volume
  ansible.oci.oci_volume_attachment:
    state: absent
    volume_attachment_id: "{{ created_attachment.resource.id }}"
"""

RETURN = r"""
resource:
  description: The volume attachment resource.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the volume attachment.
      type: str
      returned: always
      sample: ocid1.volumeattachment.oc1..example
    name:
      description: The display name of the volume attachment.
      type: str
      returned: always
      sample: example-attachment
    compartment_id:
      description: The OCID of the compartment containing the attachment.
      type: str
      returned: always
      sample: ocid1.compartment.oc1..example
    availability_domain:
      description: The availability domain of the attachment.
      type: str
      returned: always
      sample: Uocm:PHX-AD-1
    instance_id:
      description: The OCID of the attached compute instance.
      type: str
      returned: always
      sample: ocid1.instance.oc1..example
    volume_id:
      description: The OCID of the attached block volume.
      type: str
      returned: always
      sample: ocid1.volume.oc1..example
    attachment_type:
      description: The attachment type as returned by OCI.
      type: str
      returned: always
      sample: paravirtualized
    lifecycle_state:
      description: The current lifecycle state of the attachment.
      type: str
      returned: always
      sample: ATTACHED
    device:
      description: The device name the volume is exposed as on the instance, if any.
      type: str
      returned: always
      sample: /dev/oracleoci/oraclevdb
    is_read_only:
      description: Whether the volume is attached read-only.
      type: bool
      returned: always
      sample: false
    is_shareable:
      description: Whether the attachment is shareable across instances.
      type: bool
      returned: always
      sample: false
    ipv4:
      description: The IPv4 address of the iSCSI target, when C(attachment_type) is C(iscsi).
      type: str
      returned: when attachment_type is iscsi
      sample: 10.0.0.12
    iqn:
      description: The iSCSI qualified name of the target, when C(attachment_type) is C(iscsi).
      type: str
      returned: when attachment_type is iscsi
      sample: iqn.2015-12.com.oracleiaas:example
    port:
      description: The iSCSI target port, when C(attachment_type) is C(iscsi).
      type: int
      returned: when attachment_type is iscsi
      sample: 3260
    iscsi_login_state:
      description: The iSCSI login state of the attachment, when C(attachment_type) is C(iscsi).
      type: str
      returned: when attachment_type is iscsi
      sample: LOGIN_SUCCEEDED
    encryption_in_transit_type:
      description: The iSCSI encryption-in-transit mode, when C(attachment_type) is C(iscsi).
      type: str
      returned: when attachment_type is iscsi
      sample: NONE
    is_pv_encryption_in_transit_enabled:
      description: Whether in-transit encryption is enabled for a paravirtualized attachment.
      type: bool
      returned: when attachment_type is paravirtualized
      sample: false
    time_created:
      description: The date and time the attachment was created, in RFC3339 format.
      type: str
      returned: always
      sample: "2026-01-01T00:00:00.000Z"
  sample:
    id: ocid1.volumeattachment.oc1..example
    name: example-attachment
    compartment_id: ocid1.compartment.oc1..example
    availability_domain: Uocm:PHX-AD-1
    instance_id: ocid1.instance.oc1..example
    volume_id: ocid1.volume.oc1..example
    attachment_type: paravirtualized
    lifecycle_state: ATTACHED
    device: /dev/oracleoci/oraclevdb
    is_read_only: false
    is_shareable: false
    time_created: "2026-01-01T00:00:00.000Z"
"""

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    OCI_NAME_LOOKUP_ARGS,
    OCI_WAIT_ARGS,
    filter_none_values,
    import_oci_sdk,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)

imported_oci_sdk = import_oci_sdk()
oci = imported_oci_sdk[0]
HAS_OCI_SDK = imported_oci_sdk[1]

CREATE_REQUIRED_FIELDS = [
    "compartment_id",
    "instance_id",
    "volume_id",
    "name",
]
# A volume attachment uses DETACHED as its terminal lifecycle state instead of
# the collection default TERMINATED state.
WAIT_FOR_VOLUME_ATTACHMENT_STATES = ["ATTACHED"]
DETACHED_STATE = "DETACHED"
DEFAULT_ATTACHMENT_TYPE = "paravirtualized"
ISCSI_ONLY_PARAMS = ("use_chap", "encryption_in_transit_type")
PARAVIRTUALIZED_ONLY_PARAMS = ("pv_encryption_in_transit_enabled",)
REDACTED_RESULT_KEYS = ("chap_username", "chap_secret")


def resolved_attachment_type(params, resource=None):
    requested_type = params.get("type")
    if requested_type:
        return requested_type
    if resource is not None:
        return getattr(resource, "attachment_type", None) or DEFAULT_ATTACHMENT_TYPE
    return DEFAULT_ATTACHMENT_TYPE


def validate_attachment_type_params(params, fail_json, resource=None):
    attachment_type = resolved_attachment_type(params, resource)
    if attachment_type == "iscsi":
        forbidden_params = PARAVIRTUALIZED_ONLY_PARAMS
        required_type = "paravirtualized"
    else:
        forbidden_params = ISCSI_ONLY_PARAMS
        required_type = "iscsi"
    for field_name in forbidden_params:
        if params.get(field_name) is not None:
            fail_json(
                msg=(
                    f"{field_name} can only be set when type is {required_type}"
                )
            )


def build_attach_volume_details(params):
    common_fields = {
        "instance_id": params.get("instance_id"),
        "volume_id": params.get("volume_id"),
        "display_name": params.get("name"),
        "device": params.get("device"),
        "is_read_only": params.get("read_only"),
        "is_shareable": params.get("shareable"),
    }
    if params.get("type") == "iscsi":
        encryption_in_transit_type = params.get("encryption_in_transit_type")
        details = filter_none_values(
            dict(
                common_fields,
                use_chap=params.get("use_chap"),
                encryption_in_transit_type=(
                    encryption_in_transit_type.upper()
                    if encryption_in_transit_type is not None
                    else None
                ),
            )
        )
        return oci.core.models.AttachIScsiVolumeDetails(**details)

    details = filter_none_values(
        dict(
            common_fields,
            is_pv_encryption_in_transit_enabled=params.get(
                "pv_encryption_in_transit_enabled"
            ),
        )
    )
    return oci.core.models.AttachParavirtualizedVolumeDetails(**details)


class OciVolumeAttachmentModule(OciResourceBase):
    """Concrete resource adapter for OCI block volume attachments.

    OCI exposes no update operation for volume attachments, so every declared
    field is immutable and drift on any of them fails the task rather than
    issuing an update. This adapter declares ``DETACHED`` as its terminal state
    so the shared present/absent lifecycle handles it consistently.
    """

    @property
    def client_class(self):
        return oci.core.ComputeClient

    resource_id_param = "volume_attachment_id"
    list_resource_method = "list_volume_attachments"
    list_filter_params = ("instance_id", "volume_id")
    create_required_fields = CREATE_REQUIRED_FIELDS
    create_resource_name = "volume attachment"
    dead_states = frozenset({DETACHED_STATE})
    redacted_result_keys = REDACTED_RESULT_KEYS
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            resource_field="display_name",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="instance_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="volume_id",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="type",
            resource_field="attachment_type",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="device",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="read_only",
            resource_field="is_read_only",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="shareable",
            resource_field="is_shareable",
            is_mutable=False,
        ),
        UpdateFieldSpec(
            param_name="pv_encryption_in_transit_enabled",
            resource_field="is_pv_encryption_in_transit_enabled",
            is_mutable=False,
        ),
    )

    def validate_create_request(self):
        super().validate_create_request()
        validate_attachment_type_params(self.module.params, self.module.fail_json)

    def build_update_plan(self, resource):
        validate_attachment_type_params(
            self.module.params,
            self.module.fail_json,
            resource=resource,
        )
        use_chap = self.module.params.get("use_chap")
        if use_chap is not None:
            current_use_chap = bool(getattr(resource, "chap_username", None))
            if current_use_chap != use_chap:
                self.fail_immutable_field_change("use_chap")
        encryption_in_transit_type = self.module.params.get(
            "encryption_in_transit_type"
        )
        if encryption_in_transit_type is not None:
            current_encryption = getattr(
                resource, "encryption_in_transit_type", None
            )
            current_encryption = (current_encryption or "NONE").upper()
            if current_encryption != encryption_in_transit_type.upper():
                self.fail_immutable_field_change("encryption_in_transit_type")
        return super().build_update_plan(resource)

    def get_resource_response(self, resource_id):
        return self.call_with_retry(
            self.client.get_volume_attachment,
            volume_attachment_id=resource_id,
        )

    def create_resource(self):
        attach_volume_details = build_attach_volume_details(self.module.params)
        response = self.call_with_retry(
            self.client.attach_volume,
            attach_volume_details=attach_volume_details,
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            WAIT_FOR_VOLUME_ATTACHMENT_STATES,
        )

    def delete_resource(self, resource):
        return self.delete_resource_and_wait(
            resource,
            self.client.detach_volume,
            action_verb="detach",
            volume_attachment_id=resource.id,
        )


def main():
    # Volume attachments have no freeform/defined tags, so this spec is the
    # auth/wait/name-lookup pieces of OCI_COMMON_ARGS without OCI_TAG_ARGS.
    argument_spec = dict(
        OCI_AUTH_ARGS,
        **OCI_WAIT_ARGS,
        **OCI_NAME_LOOKUP_ARGS,
    )
    argument_spec.update(
        state=dict(type="str", choices=["present", "absent"], default="present"),
        volume_attachment_id=dict(type="str"),
        instance_id=dict(type="str"),
        volume_id=dict(type="str"),
        type=dict(
            type="str",
            choices=["iscsi", "paravirtualized"],
        ),
        device=dict(type="str"),
        read_only=dict(type="bool"),
        shareable=dict(type="bool"),
        use_chap=dict(type="bool"),
        encryption_in_transit_type=dict(
            type="str",
            choices=["none", "bm_encryption_in_transit"],
        ),
        pv_encryption_in_transit_enabled=dict(type="bool"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        mutually_exclusive=[
            ("use_chap", "pv_encryption_in_transit_enabled"),
            ("encryption_in_transit_type", "pv_encryption_in_transit_enabled"),
        ],
    )

    OciVolumeAttachmentModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
