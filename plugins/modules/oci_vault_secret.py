# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_vault_secret
short_description: Manage a secret in an Oracle Cloud Infrastructure Vault
description:
  - Create, update, rotate, schedule for deletion, and restore OCI Vault secrets.
  - Uses the shared OCI helper layer for authentication, waiting, retry
    behavior, and result shaping.
  - The module never returns secret content. Use M(ansible.oci.oci_vault_secret_info)
    to read it.
version_added: "1.3.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.oci.oci_name_lookup_options
  - ansible.oci.oci_wait_options
  - ansible.oci.oci_tags_options
options:
  state:
    description:
      - The desired state of the secret.
      - C(present) creates the secret when it does not exist, applies updates,
        and rotates it when I(rotate=true). A secret that is pending deletion is
        restored by cancelling the scheduled deletion.
      - C(absent) schedules the secret for deletion. OCI never deletes a secret
        immediately, so a secret that is already pending deletion is reported
        as unchanged.
    type: str
    choices: [present, absent]
    default: present
  secret_id:
    description:
      - The OCID of the secret.
      - When provided, the module manages this exact secret.
      - When omitted, the module uses O(compartment_id), O(vault_id), and O(name)
        to find an existing secret. If more than one secret matches, the task
        fails and the caller must supply O(secret_id).
      - Create requests must omit O(secret_id).
    type: str
  name:
    description:
      - Human-readable name for the secret.
      - Required when creating a secret.
      - The module does not rename an existing secret.
    type: str
  compartment_id:
    description:
      - The OCID of the compartment containing the secret.
      - Required when creating a secret.
      - The module does not move an existing secret to another compartment.
      - Also scopes name-based secret lookups when O(secret_id) is omitted.
    type: str
  vault_id:
    description:
      - The OCID of the vault that holds the secret.
      - Required when creating a secret.
      - Also scopes name-based secret lookups when O(secret_id) is omitted.
      - The module does not move an existing secret to another vault.
    type: str
  key_id:
    description:
      - The OCID of the master encryption key that encrypts the secret.
      - Required when creating a secret.
      - The module does not update this field after create.
    type: str
  description:
    description:
      - A description of the secret.
    type: str
  metadata:
    description:
      - Free-form metadata of the secret, as key-value pairs.
      - Replaces the existing metadata when it differs.
    type: dict
  content:
    description:
      - The content of the secret.
      - Required when creating a secret unless O(enable_auto_generation=true).
      - Cannot be combined with O(enable_auto_generation=true) or O(current_version_number).
      - Each change creates a new secret version.
    type: str
  content_encoding:
    description:
      - How O(content) is encoded.
      - With C(text) the module sends the UTF-8 bytes of O(content).
      - With C(base64) the module decodes O(content) and sends the resulting bytes.
    type: str
    choices: [text, base64]
    default: text
  content_name:
    description:
      - The name of the secret version that O(content) creates.
    type: str
  content_stage:
    description:
      - The rotation state of the secret version that O(content) creates.
      - C(current) makes the version the current one.
      - C(pending) stages the version for a later rotation. A secret can only be
        created with C(current).
    type: str
    choices: [current, pending]
    default: current
  update_content:
    description:
      - When the module writes O(content) to an existing secret.
      - C(when_changed) compares O(content) with the secret version in
        O(content_stage) and writes a new version only when they differ. This
        requires the C(read secret-bundles) permission.
      - C(on_create) writes O(content) only when the module creates the secret
        and never reads or updates the content of an existing secret.
    type: str
    choices: [when_changed, on_create]
    default: when_changed
  secret_rules:
    description:
      - The rules that control the use and expiry of the secret.
      - The list replaces the existing rules. An empty list removes all rules.
      - OCI rejects an update that changes both the rules and O(content) or
        O(current_version_number), so the module changes them in separate requests
        and fails when rules and O(current_version_number) change together.
    type: list
    elements: dict
    suboptions:
      rule_type:
        description:
          - The type of rule.
        type: str
        required: true
        choices: [secret_expiry_rule, secret_reuse_rule]
      secret_version_expiry_interval:
        description:
          - The interval after which a secret version expires, as an ISO 8601
            duration such as C(P30D).
          - Only for C(secret_expiry_rule).
        type: str
      time_of_absolute_expiry:
        description:
          - The time at which the current secret version expires, as an ISO 8601
            timestamp such as C(2030-01-01T00:00:00Z). A timestamp without an
            offset is read as UTC.
          - Only for C(secret_expiry_rule).
        type: str
      is_secret_content_retrieval_blocked_on_expiry:
        description:
          - Whether OCI blocks retrieval of an expired secret version's content.
          - Only for C(secret_expiry_rule).
        type: bool
      is_enforced_on_deleted_secret_versions:
        description:
          - Whether the reuse rule also applies to secret versions that are deleted.
          - Only for C(secret_reuse_rule).
        type: bool
  enable_auto_generation:
    description:
      - Whether OCI generates the secret content from O(secret_generation_context).
      - Requires O(secret_generation_context) when creating a secret.
      - Cannot be combined with O(content).
    type: bool
  secret_generation_context:
    description:
      - How OCI generates the secret content when O(enable_auto_generation=true).
    type: dict
    suboptions:
      generation_type:
        description:
          - The kind of content to generate.
        type: str
        required: true
        choices: [passphrase, ssh_key, bytes]
      generation_template:
        description:
          - The template that generates the content.
          - C(secrets_default_password) and C(dbaas_default_password) apply to C(passphrase).
          - C(rsa_2048), C(rsa_3072), and C(rsa_4096) apply to C(ssh_key).
          - C(bytes_512) and C(bytes_1024) apply to C(bytes).
        type: str
        choices:
          - secrets_default_password
          - dbaas_default_password
          - rsa_2048
          - rsa_3072
          - rsa_4096
          - bytes_512
          - bytes_1024
      passphrase_length:
        description:
          - The length of the generated passphrase.
          - Only for C(passphrase).
        type: int
      secret_template:
        description:
          - A template that wraps the generated content, in the format OCI documents
            for the generation type.
        type: str
  rotation_config:
    description:
      - The rotation settings of the secret.
    type: dict
    suboptions:
      rotation_interval:
        description:
          - The interval between scheduled rotations, as an ISO 8601 duration such as C(P30D).
        type: str
      is_scheduled_rotation_enabled:
        description:
          - Whether OCI rotates the secret on the schedule in I(rotation_interval).
        type: bool
      target_system_details:
        description:
          - The system whose credential the rotation updates.
        type: dict
        suboptions:
          target_system_type:
            description:
              - The type of the target system.
            type: str
            required: true
            choices: [adb, function]
          adb_id:
            description:
              - The OCID of the Autonomous Database.
              - Only for C(adb).
            type: str
          function_id:
            description:
              - The OCID of the function that performs the rotation.
              - Only for C(function).
            type: str
  replication_config:
    description:
      - The cross-region replication settings of the secret.
    type: dict
    suboptions:
      replication_targets:
        description:
          - The regions and vaults that hold the replicas.
        type: list
        elements: dict
        suboptions:
          target_region:
            description:
              - The region of the replica, for example C(us-phoenix-1).
            type: str
            required: true
          target_vault_id:
            description:
              - The OCID of the vault that holds the replica.
            type: str
            required: true
          target_key_id:
            description:
              - The OCID of the master encryption key that encrypts the replica.
            type: str
            required: true
      is_write_forward_enabled:
        description:
          - Whether a replica secret can forward writes to the source secret.
        type: bool
  current_version_number:
    description:
      - The number of the secret version that becomes the current version.
      - Use it to roll back to an earlier version.
      - Cannot be combined with O(content).
    type: int
  rotate:
    description:
      - Whether to rotate the secret on every run of the task with C(state=present).
      - Rotation always runs, so the task reports a change every time.
      - Ignored for a secret created by the same task.
      - The secret needs a O(rotation_config) that OCI can rotate. If the secret
        is pending deletion, the module restores it first.
      - With O(wait=true) the module waits until a new version number appears and
        the rotation is no longer in progress.
    type: bool
    default: false
  deletion_days:
    description:
      - The number of days from now until OCI deletes the secret when O(state=absent).
      - OCI accepts values from 1 to 30. When omitted, OCI uses 30 days.
      - The secret remains in C(PENDING_DELETION) until then and can be restored by
        running the task again with O(state=present).
    type: int
"""

EXAMPLES = r"""
- name: Create a text secret
  ansible.oci.oci_vault_secret:
    compartment_id: ocid1.compartment.oc1..example
    vault_id: ocid1.vault.oc1..example
    key_id: ocid1.key.oc1..example
    name: example-secret
    description: Database password
    content: s3cr3t
  no_log: true
  register: created_secret

- name: Create a secret from base64 content
  ansible.oci.oci_vault_secret:
    compartment_id: ocid1.compartment.oc1..example
    vault_id: ocid1.vault.oc1..example
    key_id: ocid1.key.oc1..example
    name: example-binary-secret
    content: AAECAwQ=
    content_encoding: base64
  no_log: true

- name: Create a secret with an auto-generated passphrase
  ansible.oci.oci_vault_secret:
    compartment_id: ocid1.compartment.oc1..example
    vault_id: ocid1.vault.oc1..example
    key_id: ocid1.key.oc1..example
    name: example-generated-secret
    enable_auto_generation: true
    secret_generation_context:
      generation_type: passphrase
      generation_template: secrets_default_password

- name: Write a new secret version when the content changes
  ansible.oci.oci_vault_secret:
    secret_id: "{{ created_secret.resource.id }}"
    content: n3ws3cr3t
    content_name: rotated-2030
  no_log: true

- name: Roll back to an earlier secret version
  ansible.oci.oci_vault_secret:
    secret_id: "{{ created_secret.resource.id }}"
    current_version_number: 1

- name: Expire secret versions after 30 days and forbid reusing old content
  ansible.oci.oci_vault_secret:
    secret_id: "{{ created_secret.resource.id }}"
    secret_rules:
      - rule_type: secret_expiry_rule
        secret_version_expiry_interval: P30D
      - rule_type: secret_reuse_rule
        is_enforced_on_deleted_secret_versions: true

- name: Configure scheduled rotation and rotate now
  ansible.oci.oci_vault_secret:
    secret_id: "{{ created_secret.resource.id }}"
    rotation_config:
      rotation_interval: P30D
      is_scheduled_rotation_enabled: true
      target_system_details:
        target_system_type: function
        function_id: ocid1.fnfunc.oc1..example
    rotate: true

- name: Schedule a secret for deletion in 3 days
  ansible.oci.oci_vault_secret:
    secret_id: "{{ created_secret.resource.id }}"
    state: absent
    deletion_days: 3

- name: Restore a secret that is pending deletion
  ansible.oci.oci_vault_secret:
    secret_id: "{{ created_secret.resource.id }}"
    state: present
"""

RETURN = r"""
resource:
  description: The secret resource. It never includes the secret content.
  returned: when state != absent
  type: dict
  contains:
    id:
      description: The OCID of the secret.
      type: str
      returned: always
    name:
      description: The name of the secret.
      type: str
      returned: always
    compartment_id:
      description: The OCID of the compartment containing the secret.
      type: str
      returned: always
    vault_id:
      description: The OCID of the vault that holds the secret.
      type: str
      returned: always
    key_id:
      description: The OCID of the master encryption key that encrypts the secret.
      type: str
      returned: always
    description:
      description: The description of the secret.
      type: str
      returned: always
    lifecycle_state:
      description: The lifecycle state of the secret, for example C(ACTIVE).
      type: str
      returned: always
    lifecycle_details:
      description: Details about the lifecycle state.
      type: str
      returned: always
    current_version_number:
      description: The number of the current secret version.
      type: int
      returned: always
    metadata:
      description: The metadata of the secret.
      type: dict
      returned: always
    secret_rules:
      description: The expiry and reuse rules of the secret.
      type: list
      elements: dict
      returned: always
    rotation_config:
      description: The rotation settings of the secret.
      type: dict
      returned: always
    rotation_status:
      description: The rotation status, for example C(NOT_ENABLED) or C(IN_PROGRESS).
      type: str
      returned: always
    last_rotation_time:
      description: The time of the last rotation.
      type: str
      returned: always
    next_rotation_time:
      description: The time of the next scheduled rotation.
      type: str
      returned: always
    replication_config:
      description: The replication settings of the secret.
      type: dict
      returned: always
    is_replica:
      description: Whether the secret is a replica of a secret in another region.
      type: bool
      returned: always
    source_region_information:
      description: The source region of a replica secret.
      type: dict
      returned: always
    is_auto_generation_enabled:
      description: Whether OCI generates the secret content.
      type: bool
      returned: always
    secret_generation_context:
      description: How OCI generates the secret content.
      type: dict
      returned: always
    time_created:
      description: The time the secret was created.
      type: str
      returned: always
    time_of_current_version_expiry:
      description: The time the current secret version expires.
      type: str
      returned: always
    time_of_deletion:
      description: The time OCI deletes the secret, set while the secret is pending deletion.
      type: str
      returned: always
    freeform_tags:
      description: Free-form tags of the secret.
      type: dict
      returned: always
    defined_tags:
      description: Defined tags of the secret.
      type: dict
      returned: always
"""

from datetime import datetime, timezone
from functools import partial

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_COMMON_ARGS,
    filter_none_values,
    import_oci_sdk,
    normalize_choice_parameters,
    values_differ_as_subset,
    values_differ_as_unordered_subset_list,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_resource import (
    OciResourceBase,
    UpdateFieldSpec,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_vault import (
    SECRET_CONTENT_ENCODINGS,
    SECRET_MIN_DELETION_DAYS,
    OciScheduledDeletionMixin,
    OciSecretBundleMixin,
    encode_secret_content,
    secret_content_to_bytes,
)

oci = import_oci_sdk()[0]


SECRET_RULE_MODELS = {
    "SECRET_EXPIRY_RULE": "SecretExpiryRule",
    "SECRET_REUSE_RULE": "SecretReuseRule",
}
GENERATION_CONTEXT_MODELS = {
    "PASSPHRASE": "PassphraseGenerationContext",
    "SSH_KEY": "SshKeyGenerationContext",
    "BYTES": "BytesGenerationContext",
}
TARGET_SYSTEM_MODELS = {
    "ADB": "AdbTargetSystemDetails",
    "FUNCTION": "FunctionTargetSystemDetails",
}

CHOICE_VALUE_MAPS = {
    ("content_stage",): {
        "current": "CURRENT",
        "pending": "PENDING",
    },
    ("secret_rules", "rule_type"): {
        "secret_expiry_rule": "SECRET_EXPIRY_RULE",
        "secret_reuse_rule": "SECRET_REUSE_RULE",
    },
    ("secret_generation_context", "generation_type"): {
        "passphrase": "PASSPHRASE",
        "ssh_key": "SSH_KEY",
        "bytes": "BYTES",
    },
    ("secret_generation_context", "generation_template"): {
        "secrets_default_password": "SECRETS_DEFAULT_PASSWORD",
        "dbaas_default_password": "DBAAS_DEFAULT_PASSWORD",
        "rsa_2048": "RSA_2048",
        "rsa_3072": "RSA_3072",
        "rsa_4096": "RSA_4096",
        "bytes_512": "BYTES_512",
        "bytes_1024": "BYTES_1024",
    },
    ("rotation_config", "target_system_details", "target_system_type"): {
        "adb": "ADB",
        "function": "FUNCTION",
    },
}

CREATE_REQUIRED_FIELDS = ("compartment_id", "vault_id", "key_id", "name")
SECRET_STATE_UPDATING = "UPDATING"
ACTIVE_STATES = ("ACTIVE",)
ROTATION_IN_PROGRESS = "IN_PROGRESS"
CONTENT_STAGE_CURRENT = "CURRENT"


def parse_timestamp(value):
    """Return an ISO 8601 timestamp as a timezone-aware datetime.

    Args:
        value: An ISO 8601 string or a datetime. A value without an offset is
            read as UTC.

    Returns:
        A timezone-aware ``datetime``.

    Raises:
        ValueError: When ``value`` is not a valid ISO 8601 timestamp.
    """
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def normalize_rule_timestamps(rule):
    """Return a secret rule with its absolute expiry parsed to a datetime.

    Args:
        rule: A serialized secret rule or a rule from the module parameters.

    Returns:
        A copy of ``rule`` whose ``time_of_absolute_expiry`` is timezone-aware,
        when set.
    """
    rule = dict(rule)
    if rule.get("time_of_absolute_expiry") is not None:
        rule["time_of_absolute_expiry"] = parse_timestamp(rule["time_of_absolute_expiry"])
    return rule


def secret_rule_differs(current_rule, desired_rule):
    """Report whether a current rule differs from a desired rule.

    Args:
        current_rule: The serialized rule of the secret.
        desired_rule: The rule requested by the caller.

    Returns:
        True when a field the caller set differs from the current rule.
    """
    return values_differ_as_subset(
        normalize_rule_timestamps(current_rule),
        normalize_rule_timestamps(desired_rule),
    )


def polymorphic_option_values(params):
    """Yield every option dict that selects a polymorphic SDK model.

    Args:
        params: The module parameters, with choices already normalized.

    Yields:
        Tuples of option name, discriminator field, model names by discriminator
        value, and the option's field dict.
    """
    for rule in params.get("secret_rules") or []:
        yield "secret_rules", "rule_type", SECRET_RULE_MODELS, rule
    if params.get("secret_generation_context") is not None:
        yield (
            "secret_generation_context",
            "generation_type",
            GENERATION_CONTEXT_MODELS,
            params["secret_generation_context"],
        )
    target = (params.get("rotation_config") or {}).get("target_system_details")
    if target is not None:
        yield "target_system_details", "target_system_type", TARGET_SYSTEM_MODELS, target


def validate_options(module):
    """Fail on option combinations that OCI or the SDK would reject later.

    Checks them before the check-mode exit so check mode reports the failure.

    Args:
        module: The active Ansible module with normalized choices.
    """
    params = module.params
    content = params.get("content")
    if content is not None and params.get("enable_auto_generation"):
        module.fail_json(
            msg="content cannot be combined with enable_auto_generation=true"
        )
    if content is not None and params.get("content_encoding") == "base64":
        try:
            secret_content_to_bytes(content, "base64")
        except ValueError:
            module.fail_json(msg="content is not valid base64")
    for rule in params.get("secret_rules") or []:
        try:
            normalize_rule_timestamps(rule)
        except ValueError:
            module.fail_json(
                msg=(
                    "time_of_absolute_expiry must be an ISO 8601 timestamp, got "
                    f"{rule['time_of_absolute_expiry']}"
                )
            )
    for option, discriminator, model_names, fields in polymorphic_option_values(params):
        model_class = getattr(oci.vault.models, model_names[fields[discriminator]])
        unsupported = sorted(
            name
            for name, value in fields.items()
            if value is not None and name not in model_class().swagger_types
        )
        if unsupported:
            module.fail_json(
                msg=(
                    f"{option} {discriminator}={fields[discriminator]} does not "
                    f"support: {', '.join(unsupported)}"
                )
            )


def build_polymorphic_model(model_names, discriminator, fields):
    """Build the SDK model that the discriminator value selects.

    Args:
        model_names: Model class names in ``oci.vault.models`` by discriminator value.
        discriminator: The field that selects the model.
        fields: The option dict, including the discriminator.

    Returns:
        An instance of the selected model. The SDK sets the discriminator itself.
    """
    fields = filter_none_values(fields)
    model_class = getattr(oci.vault.models, model_names[fields.pop(discriminator)])
    return model_class(**fields)


def build_nested_models(fields):
    """Convert nested option dicts to the SDK models OCI expects.

    Args:
        fields: Create or update fields keyed by SDK field name.

    Returns:
        A copy of ``fields`` where rules, the generation context, the rotation
        config, and the replication config are SDK models.
    """
    models = oci.vault.models
    fields = dict(fields)
    if fields.get("secret_rules") is not None:
        fields["secret_rules"] = [
            build_polymorphic_model(
                SECRET_RULE_MODELS,
                "rule_type",
                normalize_rule_timestamps(rule),
            )
            for rule in fields["secret_rules"]
        ]
    if fields.get("secret_generation_context") is not None:
        fields["secret_generation_context"] = build_polymorphic_model(
            GENERATION_CONTEXT_MODELS,
            "generation_type",
            fields["secret_generation_context"],
        )
    if fields.get("rotation_config") is not None:
        rotation_config = filter_none_values(fields["rotation_config"])
        if rotation_config.get("target_system_details") is not None:
            rotation_config["target_system_details"] = build_polymorphic_model(
                TARGET_SYSTEM_MODELS,
                "target_system_type",
                rotation_config["target_system_details"],
            )
        fields["rotation_config"] = models.RotationConfig(**rotation_config)
    if fields.get("replication_config") is not None:
        replication_config = filter_none_values(fields["replication_config"])
        if replication_config.get("replication_targets") is not None:
            replication_config["replication_targets"] = [
                models.ReplicationTarget(**filter_none_values(target))
                for target in replication_config["replication_targets"]
            ]
        fields["replication_config"] = models.ReplicationConfig(**replication_config)
    return fields


def build_content_details(params):
    """Build the secret content model from module parameters.

    Args:
        params: The validated module parameters, with choices normalized.

    Returns:
        An ``oci.vault.models.Base64SecretContentDetails`` instance.
    """
    return oci.vault.models.Base64SecretContentDetails(
        **filter_none_values(
            {
                "content": encode_secret_content(
                    params["content"], params["content_encoding"]
                ),
                "name": params.get("content_name"),
                "stage": params.get("content_stage"),
            }
        )
    )


def build_create_secret_details(params):
    """Build the OCI create-secret model from module parameters.

    Args:
        params: The validated module parameters, with choices already
            normalized to OCI values.

    Returns:
        An ``oci.vault.models.CreateSecretDetails`` instance.
    """
    fields = build_nested_models(
        filter_none_values(
            {
                "compartment_id": params.get("compartment_id"),
                "vault_id": params.get("vault_id"),
                "key_id": params.get("key_id"),
                "secret_name": params.get("name"),
                "description": params.get("description"),
                "metadata": params.get("metadata"),
                "secret_rules": params.get("secret_rules"),
                "enable_auto_generation": params.get("enable_auto_generation"),
                "secret_generation_context": params.get("secret_generation_context"),
                "rotation_config": params.get("rotation_config"),
                "replication_config": params.get("replication_config"),
                "freeform_tags": params.get("freeform_tags"),
                "defined_tags": params.get("defined_tags"),
            }
        )
    )
    if params.get("content") is not None:
        fields["secret_content"] = build_content_details(params)
    return oci.vault.models.CreateSecretDetails(**fields)


class OciVaultSecretModule(OciSecretBundleMixin, OciScheduledDeletionMixin, OciResourceBase):
    """Concrete resource adapter for OCI Vault secrets."""

    @property
    def client_class(self):
        """Return the regional vault client class.

        Returns:
            The ``oci.vault.VaultsClient`` class.
        """
        return oci.vault.VaultsClient

    resource_id_param = "secret_id"
    list_resource_method = "list_secrets"
    list_filter_params = ("vault_id",)
    name_response_field = "secret_name"
    field_param_aliases = {"secret_name": "name"}
    create_resource_name = "secret"
    create_required_fields = CREATE_REQUIRED_FIELDS
    update_method_name = "update_secret"
    update_details_name = "update_secret_details"
    update_wait_states = ACTIVE_STATES
    min_deletion_days = SECRET_MIN_DELETION_DAYS
    update_field_specs = (
        UpdateFieldSpec(
            param_name="name",
            is_mutable=False,
            resource_field="secret_name",
            immutable_reason="OCI does not rename secrets",
        ),
        UpdateFieldSpec(
            param_name="compartment_id",
            is_mutable=False,
            immutable_reason="this module does not move secrets between compartments",
        ),
        UpdateFieldSpec(
            param_name="vault_id",
            is_mutable=False,
            immutable_reason="a secret cannot move to another vault",
        ),
        UpdateFieldSpec(
            param_name="key_id",
            is_mutable=False,
            immutable_reason="the master encryption key of a secret cannot change",
        ),
        UpdateFieldSpec(param_name="description", is_mutable=True),
        UpdateFieldSpec(param_name="metadata", is_mutable=True),
        UpdateFieldSpec(
            param_name="secret_rules",
            is_mutable=True,
            compare="unordered_subset_list",
        ),
        UpdateFieldSpec(
            param_name="enable_auto_generation",
            is_mutable=True,
            resource_field="is_auto_generation_enabled",
            update_field="enable_auto_generation",
        ),
        UpdateFieldSpec(
            param_name="secret_generation_context",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="rotation_config",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(
            param_name="replication_config",
            is_mutable=True,
            compare="subset_dict",
        ),
        UpdateFieldSpec(param_name="current_version_number", is_mutable=True),
    )
    _content_update_needed = None

    def get_resource_response(self, resource_id):
        """Return the raw ``get_secret`` response for ``resource_id``.

        Args:
            resource_id: The OCID of the secret.

        Returns:
            The OCI SDK response wrapper.
        """
        return self.call_with_retry(self.client.get_secret, secret_id=resource_id)

    def hydrate_named_resource(self, resource):
        """Return the full secret for a name-lookup match.

        ``list_secrets`` returns a ``SecretSummary`` that omits ``metadata``,
        ``secret_rules``, and ``current_version_number``, so a name-resolved
        match must be re-fetched with ``get_secret`` before the update planner
        compares desired values against it.

        Args:
            resource: The ``SecretSummary`` matched by name.

        Returns:
            The full secret, or ``resource`` if it can no longer be fetched.
        """
        full_resource = self.get_resource_by_id(resource.id)
        return full_resource if full_resource is not None else resource

    def compare_update_field_values(self, current_value, desired_value, compare=None):
        """Compare current and desired values, normalizing rule timestamps.

        The inherited ``unordered_subset_list`` comparison would compare the
        ISO 8601 ``time_of_absolute_expiry`` string the caller supplied with the
        datetime OCI returns, so a rule would always look changed.

        Args:
            current_value: The current serialized field value.
            desired_value: The requested field value.
            compare: The strategy declared by the update field specification.

        Returns:
            True when the requested field differs from the current field.
        """
        if compare == "unordered_subset_list":
            return values_differ_as_unordered_subset_list(
                current_value, desired_value, item_differs=secret_rule_differs
            )
        return super(OciVaultSecretModule, self).compare_update_field_values(
            current_value, desired_value, compare=compare
        )

    def validate_create_request(self):
        """Require content or a generation context, and a current-stage version.

        Extends the inherited required-field check with the rules that tie
        ``content``, ``enable_auto_generation``, and ``content_stage`` together.
        """
        super(OciVaultSecretModule, self).validate_create_request()
        params = self.module.params
        if params.get("content_stage") != CONTENT_STAGE_CURRENT:
            self.module.fail_json(
                msg="A secret can only be created with content_stage=current"
            )
        if params.get("enable_auto_generation"):
            if params.get("secret_generation_context") is None:
                self.module.fail_json(
                    msg="enable_auto_generation=true requires secret_generation_context"
                )
        elif params.get("content") is None:
            self.module.fail_json(
                msg=(
                    "Creating a secret requires content unless "
                    "enable_auto_generation is true"
                )
            )

    def create_resource(self):
        """Create the secret and wait for it to be active.

        Returns:
            The created secret.
        """
        response = self.call_with_retry(
            self.client.create_secret,
            create_secret_details=build_create_secret_details(self.module.params),
        )
        return self.get_mutation_result(
            response.data,
            getattr(response.data, "id", None),
            ACTIVE_STATES,
        )

    def fail_if_replica(self, resource):
        """Fail when ``resource`` is a replica, which OCI only changes at its source.

        Args:
            resource: The current secret.
        """
        if getattr(resource, "is_replica", False):
            self.module.fail_json(
                msg=(
                    f"Secret {resource.id} is a replica and cannot be updated. "
                    "Update its source secret instead"
                )
            )

    def needs_update(self, resource):
        """Report field drift, failing when it would change a replica.

        Extends the inherited check so that check mode also rejects the update.

        Args:
            resource: The current secret.

        Returns:
            True when the update planner detects drift.
        """
        update_needed = super(OciVaultSecretModule, self).needs_update(resource)
        if update_needed:
            self.fail_if_replica(resource)
        return update_needed

    def build_update_details(self, update_model_fields):
        """Build the OCI update-secret model from planned field changes.

        Args:
            update_model_fields: The planned changes keyed by update field.

        Returns:
            An ``oci.vault.models.UpdateSecretDetails`` instance.
        """
        if "secret_rules" in update_model_fields and "current_version_number" in update_model_fields:
            self.module.fail_json(
                msg=(
                    "OCI does not allow changing secret_rules and "
                    "current_version_number in one update. Change them in separate tasks"
                )
            )
        return oci.vault.models.UpdateSecretDetails(
            **build_nested_models(update_model_fields)
        )

    def content_update_needed(self, resource):
        """Report whether ``content`` must be written as a new secret version.

        The decision is made once per run because the base flow asks twice and
        the answer costs a secret bundle read.

        Args:
            resource: The current secret.

        Returns:
            True when ``content`` differs from the version in ``content_stage``.
        """
        params = self.module.params
        if params.get("content") is None or params.get("update_content") == "on_create":
            return False
        if self._content_update_needed is None:
            current_content = self.get_secret_bundle_content(
                resource.id, stage=params["content_stage"]
            )
            self._content_update_needed = (
                current_content is None
                or secret_content_to_bytes(current_content, "base64")
                != secret_content_to_bytes(params["content"], params["content_encoding"])
            )
            if self._content_update_needed:
                self.fail_if_replica(resource)
        return self._content_update_needed

    def extra_change_needed(self, resource):
        """Report whether a deletion must be cancelled or content or rotation applied.

        Extends the inherited cancellation check because neither a content
        change nor a rotation is an update-field difference.

        Args:
            resource: The current secret.

        Returns:
            True when the secret is pending deletion, its content changed, or
            ``rotate`` is set.
        """
        if super(OciVaultSecretModule, self).extra_change_needed(resource):
            return True
        if self.module.params.get("rotate"):
            self.fail_if_replica(resource)
            return True
        return self.content_update_needed(resource)

    def apply_extra_change(self, resource):
        """Cancel a pending deletion, then write changed content and rotate.

        Extends the inherited cancellation. A preceding field update with
        ``wait: false`` can leave the secret updating, which OCI rejects a
        further update or rotation for, so that transition is waited out first.

        Args:
            resource: The current secret.

        Returns:
            The secret after cancellation and, when requested, the content
            update and rotation.
        """
        resource = super(OciVaultSecretModule, self).apply_extra_change(resource)
        if getattr(resource, "lifecycle_state", None) == SECRET_STATE_UPDATING:
            resource = self.wait_for_restoration(resource)
        if self.content_update_needed(resource):
            resource = self.update_secret_content(resource)
        if self.module.params.get("rotate"):
            resource = self.rotate_secret(resource)
        return resource

    def update_secret_content(self, resource):
        """Write ``content`` as a new secret version and wait for it to be active.

        Args:
            resource: The current secret.

        Returns:
            The updated secret.
        """
        response = self.call_with_retry(
            self.client.update_secret,
            secret_id=resource.id,
            update_secret_details=oci.vault.models.UpdateSecretDetails(
                secret_content=build_content_details(self.module.params)
            ),
        )
        return self.get_mutation_result(
            response.data, resource.id, ACTIVE_STATES
        )

    def rotate_secret(self, resource):
        """Rotate the secret and, when waiting, wait for the new version.

        Args:
            resource: The current secret.

        Returns:
            The refreshed secret.
        """
        previous_version = getattr(resource, "current_version_number", None) or 0
        self.call_with_retry(self.client.rotate_secret, secret_id=resource.id)
        if not self.module.params.get("wait", True):
            return self.get_resource_response(resource.id).data

        def fetch(response=None):
            return self.get_resource_response(resource.id)

        waiter_result = oci.wait_until(
            self.client,
            fetch(),
            max_wait_seconds=self.module.params.get("wait_timeout", 1200),
            max_interval_seconds=self.module.params.get("wait_interval", 30),
            evaluate_response=partial(
                self._rotation_complete, resource.id, previous_version
            ),
            fetch_func=fetch,
        )
        return getattr(waiter_result, "data", None)

    def _rotation_complete(self, secret_id, previous_version, response):
        """Evaluate one rotation poll, failing when the secret fails.

        ``rotate_secret`` returns before the rotation starts, and the SDK has
        no Vault work-request client to wait on, so completion is a new
        version number together with a rotation that is no longer in progress.

        Args:
            secret_id: The OCID of the secret being rotated.
            previous_version: The current version number before rotation.
            response: The current ``get_secret`` response.

        Returns:
            Whether the rotation produced a new version and has finished.
        """
        secret = response.data
        if getattr(secret, "lifecycle_state", None) == "FAILED":
            self.module.fail_json(
                msg=f"Secret {secret_id} entered failure state: FAILED"
            )
        return (
            (getattr(secret, "current_version_number", None) or 0) > previous_version
            and getattr(secret, "rotation_status", None) != ROTATION_IN_PROGRESS
        )

    def cancel_deletion(self, resource):
        """Cancel the scheduled deletion of ``resource``.

        ``cancel_secret_deletion`` returns no body, so the secret is fetched
        again to hand the restoration check a resource even when not waiting.

        Args:
            resource: The secret that is pending deletion.

        Returns:
            The restored secret.
        """
        self.call_with_retry(self.client.cancel_secret_deletion, secret_id=resource.id)
        return self.get_mutation_result(
            self.get_resource_response(resource.id).data,
            resource.id,
            ACTIVE_STATES,
        )

    def delete_resource(self, resource):
        """Schedule ``resource`` for deletion and wait until it is pending.

        Args:
            resource: The secret to delete.

        Returns:
            The secret in ``PENDING_DELETION``, or the raw response data when not waiting.
        """
        return self.delete_resource_and_wait(
            resource,
            self.client.schedule_secret_deletion,
            action_verb="schedule deletion of",
            secret_id=resource.id,
            schedule_secret_deletion_details=(
                oci.vault.models.ScheduleSecretDeletionDetails(
                    **self.build_deletion_schedule()
                )
            ),
        )


def main():
    """Run the ``oci_vault_secret`` module."""
    argument_spec = dict(
        OCI_COMMON_ARGS,
        state=dict(type="str", choices=["present", "absent"], default="present"),
        secret_id=dict(type="str"),
        vault_id=dict(type="str"),
        key_id=dict(type="str"),
        description=dict(type="str"),
        metadata=dict(type="dict"),
        content=dict(type="str", no_log=True),
        content_encoding=dict(
            type="str", choices=list(SECRET_CONTENT_ENCODINGS), default="text"
        ),
        content_name=dict(type="str"),
        content_stage=dict(
            type="str",
            choices=list(CHOICE_VALUE_MAPS[("content_stage",)]),
            default="current",
        ),
        update_content=dict(
            type="str", choices=["when_changed", "on_create"], default="when_changed"
        ),
        secret_rules=dict(
            type="list",
            elements="dict",
            no_log=False,
            options=dict(
                rule_type=dict(
                    type="str",
                    required=True,
                    choices=list(CHOICE_VALUE_MAPS[("secret_rules", "rule_type")]),
                ),
                secret_version_expiry_interval=dict(type="str", no_log=False),
                time_of_absolute_expiry=dict(type="str"),
                is_secret_content_retrieval_blocked_on_expiry=dict(type="bool"),
                is_enforced_on_deleted_secret_versions=dict(type="bool"),
            ),
        ),
        enable_auto_generation=dict(type="bool"),
        secret_generation_context=dict(
            type="dict",
            no_log=False,
            options=dict(
                generation_type=dict(
                    type="str",
                    required=True,
                    choices=list(
                        CHOICE_VALUE_MAPS[("secret_generation_context", "generation_type")]
                    ),
                ),
                generation_template=dict(
                    type="str",
                    choices=list(
                        CHOICE_VALUE_MAPS[
                            ("secret_generation_context", "generation_template")
                        ]
                    ),
                ),
                passphrase_length=dict(type="int", no_log=False),
                secret_template=dict(type="str", no_log=False),
            ),
        ),
        rotation_config=dict(
            type="dict",
            options=dict(
                rotation_interval=dict(type="str"),
                is_scheduled_rotation_enabled=dict(type="bool"),
                target_system_details=dict(
                    type="dict",
                    options=dict(
                        target_system_type=dict(
                            type="str",
                            required=True,
                            choices=list(
                                CHOICE_VALUE_MAPS[
                                    (
                                        "rotation_config",
                                        "target_system_details",
                                        "target_system_type",
                                    )
                                ]
                            ),
                        ),
                        adb_id=dict(type="str"),
                        function_id=dict(type="str"),
                    ),
                ),
            ),
        ),
        replication_config=dict(
            type="dict",
            options=dict(
                replication_targets=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        target_region=dict(type="str", required=True),
                        target_vault_id=dict(type="str", required=True),
                        target_key_id=dict(type="str", required=True),
                    ),
                ),
                is_write_forward_enabled=dict(type="bool"),
            ),
        ),
        current_version_number=dict(type="int"),
        rotate=dict(type="bool", default=False),
        deletion_days=dict(type="int"),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[["content", "current_version_number"]],
        supports_check_mode=True,
    )

    normalize_choice_parameters(module, CHOICE_VALUE_MAPS)
    validate_options(module)

    OciVaultSecretModule(module).execute_resource_module()


if __name__ == "__main__":
    main()
