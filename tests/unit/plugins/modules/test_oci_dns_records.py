from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest

from .conftest import DummyModule, load_collection_module


RESOURCE_MODULES = (
    ("oci_dns_zone_records", "OciDnsZoneRecordsModule", "zone"),
    ("oci_dns_domain_records", "OciDnsDomainRecordsModule", "domain"),
    ("oci_dns_record_set", "OciDnsRecordSetModule", "rrset"),
)

INFO_MODULES = (
    ("oci_dns_zone_records_info", "OciDnsZoneRecordsInfoModule", "zone"),
    ("oci_dns_domain_records_info", "OciDnsDomainRecordsInfoModule", "domain"),
    ("oci_dns_record_set_info", "OciDnsRecordSetInfoModule", "rrset"),
)


@pytest.mark.parametrize("module_name,class_name,kind", RESOURCE_MODULES)
def test_resource_main_uses_scope_builder_and_executor(monkeypatch, module_name, class_name, kind):
    """Check each resource wrapper passes its scope to shared DNS code."""
    module_obj = load_collection_module(module_name)
    captured = {}

    def fake_builder(actual_kind, info=False):
        captured["builder"] = (actual_kind, info)
        return {"zone_name_or_id": {"type": "str", "required": True}}

    def fake_ansible_module(**kwargs):
        captured["required_if"] = kwargs["required_if"]
        return DummyModule({})

    class FakeModuleClass:
        scope_kind = kind

        def __init__(self, module):
            captured["scope"] = self.scope_kind

        def execute_resource_module(self):
            captured["executed"] = True

    monkeypatch.setattr(module_obj, "build_dns_argument_spec", fake_builder)
    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, class_name, FakeModuleClass)

    module_obj.main()

    assert captured["builder"] == (kind, False)
    assert captured["required_if"] == [("state", "present", ["update_items"])]
    assert captured["scope"] == kind
    assert captured["executed"] is True


@pytest.mark.parametrize("module_name,class_name,kind", INFO_MODULES)
def test_info_main_uses_scope_builder_and_executor(monkeypatch, module_name, class_name, kind):
    """Check each info wrapper passes its scope to shared DNS code."""
    module_obj = load_collection_module(module_name)
    captured = {}

    def fake_builder(actual_kind, info=False):
        captured["builder"] = (actual_kind, info)
        return {"zone_name_or_id": {"type": "str", "required": True}}

    class FakeInfoClass:
        scope_kind = kind

        def __init__(self, module):
            captured["scope"] = self.scope_kind

        def execute_info_module(self):
            captured["executed"] = True

    monkeypatch.setattr(module_obj, "build_dns_argument_spec", fake_builder)
    monkeypatch.setattr(module_obj, "AnsibleModule", lambda **kwargs: DummyModule({}))
    monkeypatch.setattr(module_obj, class_name, FakeInfoClass)

    module_obj.main()

    assert captured["builder"] == (kind, True)
    assert captured["scope"] == kind
    assert captured["executed"] is True


@pytest.mark.parametrize("module_name", [name for name, unused_class, unused_kind in RESOURCE_MODULES])
def test_resource_documentation_defines_complete_record_fields(module_name):
    """Check resource docs describe each required desired record field."""
    module_obj = load_collection_module(module_name)

    for field in ("domain", "rtype", "rdata", "ttl"):
        assert "      " + field + ":" in module_obj.DOCUMENTATION

    assert "update_items:" in module_obj.DOCUMENTATION
    assert "is_protected" in module_obj.RETURN or "all OCI record fields" in module_obj.RETURN
