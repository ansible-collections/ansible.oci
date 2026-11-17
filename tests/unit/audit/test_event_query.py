# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

from pathlib import Path

import pytest
import yaml


@pytest.fixture(scope="module")
def query_document():
    query_file = Path(__file__).resolve().parents[3] / "extensions/audit/event_query.yml"
    with query_file.open() as handle:
        document = yaml.safe_load(handle)
    return document


def test_audit_query_document(query_document):
    assert set(query_document) == {"ansible.oci.*"}
    query = query_document["ansible.oci.*"]["query"]
    assert isinstance(query, str)
    assert query.strip()


@pytest.fixture(scope="module")
def audit_query(query_document):
    jq = pytest.importorskip("jq", reason="jq is optional for audit output checks")
    return jq.compile(query_document["ansible.oci.*"]["query"])


def expected_record(identifier, name, bucket, node_type):
    return {
        "name": identifier,
        "canonical_facts": {"id": identifier},
        "facts": {
            "name": name,
            "infra_type": "public_cloud",
            "infra_bucket": bucket,
            "device_type": node_type,
            "node_type": node_type,
        },
    }


@pytest.mark.parametrize(
    "module_output, expected",
    [
        pytest.param(
            {"changed": False, "resource": {
                "id": "ocid1.instance.oc1..server1", "name": "server1",
                "compartment_id": "ocid1.compartment.oc1..example",
            }},
            [expected_record("ocid1.instance.oc1..server1", "server1", "compute", "instance")],
            id="oci_instance",
        ),
        pytest.param(
            {"instances": [
                {"id": "ocid1.instance.oc1..server1", "name": "server1"},
                {"id": "ocid1.instance.oc1..server2"},
            ]},
            [
                expected_record("ocid1.instance.oc1..server1", "server1", "compute", "instance"),
                expected_record("ocid1.instance.oc1..server2", "ocid1.instance.oc1..server2", "compute", "instance"),
            ],
            id="oci_instance_info",
        ),
        pytest.param(
            {"vcns": [{"id": "ocid1.vcn.oc1..network1", "name": "network1"}]},
            [expected_record("ocid1.vcn.oc1..network1", "network1", "networking", "vcn")],
            id="oci_network_vcn_info",
        ),
        pytest.param(
            {"resource": {"topic_id": "ocid1.onstopic.oc1..topic1", "name": "alerts"}},
            [expected_record("ocid1.onstopic.oc1..topic1", "alerts", "app_integration_messaging", "onstopic")],
            id="oci_notification_topic",
        ),
        pytest.param(
            {"users": [{"id": "scim-user-123", "ocid": "ocid1.user.oc1..user1", "name": "user1"}]},
            [expected_record("ocid1.user.oc1..user1", "user1", "security_identity", "user")],
            id="oci_identity_user_info",
        ),
        pytest.param(
            {"user_group_memberships": [{
                "membership_ocid": "ocid1.usergroupmembership.oc1..membership1",
                "user_ocid": "ocid1.user.oc1..user1",
                "group_id": "scim-group-123",
            }]},
            [expected_record(
                "ocid1.usergroupmembership.oc1..membership1",
                "ocid1.usergroupmembership.oc1..membership1",
                "security_identity", "usergroupmembership",
            )],
            id="oci_identity_user_group_membership_info",
        ),
    ],
)
def test_module_output_generates_audit_records(audit_query, module_output, expected):
    assert audit_query.input_value(module_output).all() == expected


@pytest.mark.parametrize(
    "module_output",
    [
        pytest.param(
            {"buckets": [{"namespace": "example", "name": "bucket1",
                          "compartment_id": "ocid1.compartment.oc1..example"}]},
            id="bucket_summary_without_ocid",
        ),
        pytest.param({"resource": {"id": "short-rule-id"}}, id="non_ocid"),
        pytest.param({"resource": {"id": None}}, id="null_identity"),
        pytest.param({"changed": True}, id="no_resource"),
    ],
)
def test_output_without_resource_identity_generates_no_records(audit_query, module_output):
    assert audit_query.input_value(module_output).all() == []
