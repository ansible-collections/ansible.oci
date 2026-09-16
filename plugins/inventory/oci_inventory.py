# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import hashlib

DOCUMENTATION = r"""
---
name: oci_inventory
plugin_type: inventory
short_description: Oracle Cloud Infrastructure Compute inventory source
description:
  - Builds an inventory from running OCI Compute instances in explicit compartments.
  - Uses a YAML configuration file ending in C(.oci_inventory.yml) or C(.oci_inventory.yaml).
extends_documentation_fragment:
  - inventory_cache
  - constructed
options:
  plugin:
    description: Token that ensures this is a source file for this plugin.
    required: true
    choices: [ansible.oci.oci_inventory]
  compartments:
    description: OCI compartment OCIDs to query.
    type: list
    elements: str
    required: true
  regions:
    description:
      - OCI regions to query.
      - When omitted, the region from the selected OCI profile is used.
    type: list
    elements: str
    default: []
  lifecycle_states:
    description: Instance lifecycle states to include.
    type: list
    elements: str
    default: [RUNNING]
  freeform_tags:
    description: Freeform tag key/value pairs that every returned instance must contain.
    type: dict
    default: {}
  defined_tags:
    description: Defined tag namespace/key/value pairs that every returned instance must contain.
    type: dict
    default: {}
  hostnames:
    description:
      - Ordered host variable names used to select the inventory hostname.
      - The default C(name_with_id) combines the OCI display name with a stable,
        short ID suffix; the full instance ID remains available as C(instance_id).
      - Supported values are C(name_with_id), C(id), C(display_name), C(private_ip), C(public_ip), and C(hostname_label).
    type: list
    elements: str
    default: [name_with_id, id]
  auth_type:
    description: OCI authentication method.
    type: str
    choices: [api_key, instance_principal, resource_principal, session_token]
    default: api_key
    env:
      - name: OCI_AUTH_TYPE
  config_file_location:
    description: Path to the OCI SDK configuration file.
    type: path
    default: ~/.oci/config
    env:
      - name: OCI_CONFIG_FILE
  config_profile_name:
    description: OCI SDK configuration profile name.
    type: str
    default: DEFAULT
    env:
      - name: OCI_CONFIG_PROFILE
  tenancy:
    description: OCI tenancy OCID overriding the configuration profile.
    type: str
    env:
      - name: OCI_TENANCY_ID
  region:
    description: OCI region overriding the configuration profile when C(regions) is omitted.
    type: str
    env:
      - name: OCI_REGION
  api_user:
    description: OCI user OCID overriding the configuration profile.
    type: str
    env:
      - name: OCI_USER_ID
  api_user_fingerprint:
    description: API key fingerprint overriding the configuration profile.
    type: str
    no_log: true
    env:
      - name: OCI_USER_FINGERPRINT
  api_user_key_file:
    description: API private-key path overriding the configuration profile.
    type: path
    env:
      - name: OCI_USER_KEY_FILE
  api_user_key_pass_phrase:
    description: Pass phrase for C(api_user_key_file).
    type: str
    no_log: true
    env:
      - name: OCI_USER_KEY_PASS_PHRASE
"""

EXAMPLES = r"""
# inventory.oci_inventory.yml
plugin: ansible.oci.oci_inventory
compartments:
  - ocid1.compartment.oc1..example
regions:
  - us-ashburn-1
freeform_tags:
  role: webserver
keyed_groups:
  - key: shape
    prefix: compute
compose:
  ansible_user: opc
cache: true
cache_plugin: jsonfile
cache_connection: /tmp/oci-inventory-cache
"""

from ansible.errors import AnsibleParserError
from ansible.module_utils.basic import missing_required_lib
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

from ansible_collections.ansible.oci.plugins.module_utils.oci_auth import (
    create_service_client_from_options,
    get_oci_config_from_options,
)
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    import_oci_sdk,
    serialize_oci_model,
)

_oci_sdk = import_oci_sdk()
oci = _oci_sdk[0]
HAS_OCI_SDK = _oci_sdk[1]


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "ansible.oci.oci_inventory"
    _hostname_fields = frozenset(
        (
            "name_with_id", "id", "display_name", "private_ip", "public_ip",
            "hostname_label",
        )
    )

    def verify_file(self, path):
        return super(InventoryModule, self).verify_file(path) and path.endswith(
            (".oci_inventory.yml", ".oci_inventory.yaml")
        )

    def parse(self, inventory, loader, path, cache=True):
        if not HAS_OCI_SDK:
            raise AnsibleParserError(
                "OCI inventory plugin cannot start: %s" % missing_required_lib("oci")
            )

        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)
        for record in self._get_records(path, cache):
            self._add_record(record)

    def _get_records(self, path, use_cache):
        cache_enabled = use_cache and self.get_option("cache")
        cache_key = self.get_cache_key(path) if cache_enabled else None
        if cache_enabled:
            try:
                return self.cache[cache_key]
            except KeyError:
                pass

        records = self._discover_records()
        if cache_enabled:
            self.cache[cache_key] = records
        return records

    def _discover_records(self):
        options = self._client_options()
        records = []
        seen_instance_ids = set()
        for region in self._regions(options):
            compute = create_service_client_from_options(
                options, oci.core.ComputeClient, region
            )
            network = create_service_client_from_options(
                options, oci.core.VirtualNetworkClient, region
            )
            for compartment_id in self.get_option("compartments"):
                for instance in self._list_instances(compute, compartment_id):
                    instance_id = getattr(instance, "id", None)
                    if instance_id in seen_instance_ids or not self._matches_tags(instance):
                        continue
                    record = self._record_for_instance(
                        compute, network, instance, compartment_id, region
                    )
                    if record:
                        records.append(record)
                        seen_instance_ids.add(instance_id)
        return records

    def _client_options(self):
        names = (
            "auth_type", "config_file_location", "config_profile_name", "tenancy",
            "region", "api_user", "api_user_fingerprint", "api_user_key_file",
            "api_user_key_pass_phrase",
        )
        return {name: self.get_option(name) for name in names}

    def _regions(self, options):
        regions = self.get_option("regions")
        if regions:
            return regions
        configured_region = get_oci_config_from_options(options).get("region")
        if not configured_region:
            raise AnsibleParserError(
                "regions is required when the OCI configuration does not provide a region"
            )
        return [configured_region]

    def _list_instances(self, compute, compartment_id):
        instances = []
        for lifecycle_state in self.get_option("lifecycle_states"):
            instances.extend(
                self._list_all(
                    compute.list_instances,
                    compartment_id=compartment_id,
                    lifecycle_state=lifecycle_state,
                )
            )
        return instances

    @staticmethod
    def _list_all(method, **kwargs):
        results = []
        page = None
        while True:
            response = method(page=page, **kwargs) if page else method(**kwargs)
            results.extend(response.data)
            page = getattr(response, "headers", {}).get("opc-next-page")
            if not page:
                return results

    def _matches_tags(self, instance):
        freeform_tags = getattr(instance, "freeform_tags", {}) or {}
        if any(
            freeform_tags.get(key) != value
            for key, value in self.get_option("freeform_tags").items()
        ):
            return False
        defined_tags = getattr(instance, "defined_tags", {}) or {}
        for namespace, tags in self.get_option("defined_tags").items():
            if any(
                defined_tags.get(namespace, {}).get(key) != value
                for key, value in tags.items()
            ):
                return False
        return True

    def _record_for_instance(self, compute, network, instance, compartment_id, region):
        attachments = self._list_all(
            compute.list_vnic_attachments,
            compartment_id=compartment_id,
            instance_id=instance.id,
        )
        primary = next(
            (item for item in attachments if getattr(item, "nic_index", None) == 0),
            None,
        )
        if not primary:
            self.display.warning(
                "Skipping OCI instance %s: no primary VNIC attachment" % instance.id
            )
            return None
        vnic = network.get_vnic(primary.vnic_id).data
        if not getattr(vnic, "private_ip", None):
            self.display.warning(
                "Skipping OCI instance %s: primary VNIC has no private IP" % instance.id
            )
            return None

        instance_data = serialize_oci_model(instance)
        vnic_data = serialize_oci_model(vnic)
        display_name = getattr(instance, "display_name", None)
        short_id = hashlib.sha256(instance.id.encode("utf-8")).hexdigest()[:8]
        return {
            "id": instance.id,
            "display_name": display_name,
            "name_with_id": "%s_%s" % (display_name, short_id) if display_name else instance.id,
            "hostname_label": getattr(vnic, "hostname_label", None),
            "private_ip": vnic.private_ip,
            "public_ip": getattr(vnic, "public_ip", None),
            "instance_id": instance.id,
            "compartment_id": getattr(instance, "compartment_id", compartment_id),
            "availability_domain": getattr(instance, "availability_domain", None),
            "shape": getattr(instance, "shape", None),
            "region": region,
            "lifecycle_state": getattr(instance, "lifecycle_state", None),
            "image_id": getattr(instance, "image_id", None),
            "freeform_tags": instance_data.get("freeform_tags", {}),
            "defined_tags": instance_data.get("defined_tags", {}),
            "vnic_id": getattr(vnic, "id", primary.vnic_id),
            "subnet_id": getattr(vnic, "subnet_id", None),
            "oci_instance": instance_data,
            "oci_vnic": vnic_data,
        }

    def _add_record(self, record):
        hostname = self._hostname(record)
        existing = self.inventory.get_host(hostname)
        if existing and existing.get_vars().get("instance_id") != record["instance_id"]:
            raise AnsibleParserError(
                "OCI hostname collision for %s; use a hostname preference that is unique"
                % hostname
            )

        self.inventory.add_host(hostname)
        for key, value in record.items():
            self.inventory.set_variable(hostname, key, value)
        self.inventory.set_variable(hostname, "ansible_host", record["private_ip"])
        self._add_default_groups(hostname, record)
        strict = self.get_option("strict")
        self._set_composite_vars(self.get_option("compose"), record, hostname, strict)
        self._add_host_to_composed_groups(
            self.get_option("groups"), record, hostname, strict
        )
        self._add_host_to_keyed_groups(
            self.get_option("keyed_groups"), record, hostname, strict
        )

    def _hostname(self, record):
        for field in self.get_option("hostnames"):
            if field not in self._hostname_fields:
                raise AnsibleParserError("Unsupported OCI hostname field: %s" % field)
            if record.get(field):
                return str(record[field])
        raise AnsibleParserError(
            "No configured hostname field is available for OCI instance %s" % record["id"]
        )

    def _add_default_groups(self, hostname, record):
        values = {
            "region": record["region"],
            "compartment": record["compartment_id"],
            "availability_domain": record["availability_domain"],
            "shape": record["shape"],
            "lifecycle_state": record["lifecycle_state"],
        }
        for kind, value in values.items():
            if value:
                self._add_generated_group("oci_%s_%s" % (kind, value), hostname)
        for key, value in record["freeform_tags"].items():
            self._add_generated_group("oci_tag_%s_%s" % (key, value), hostname)
        for namespace, tags in record["defined_tags"].items():
            for key, value in tags.items():
                self._add_generated_group(
                    "oci_tag_%s_%s_%s" % (namespace, key, value), hostname
                )

    def _add_generated_group(self, name, hostname):
        group = self.inventory.add_group(self._sanitize_group_name(name))
        self.inventory.add_child(group, hostname)
