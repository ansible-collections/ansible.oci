from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types
from unittest.mock import Mock

import pytest
from ansible.module_utils.common.arg_spec import ModuleArgumentSpecValidator

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
)


@pytest.mark.parametrize("params,error", [
    ({"vnic_id": "vnic"}, None),
    ({"vnic_id": "vnic", "id": "vnic"}, "id"),
    ({}, "vnic_id"),
    ({"vnic_id": ""}, "cannot be empty"),
])
def test_main_validates_required_id(monkeypatch, params, error):
    """Validate the canonical ID and reject aliases and missing or empty IDs."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_vnic_info")

    def validate_arguments(**kwargs):
        """Apply Ansible argument validation to the test inputs."""
        result = ModuleArgumentSpecValidator(kwargs["argument_spec"]).validate(params)
        if result.error_messages:
            raise FailJsonCalled({"msg": "; ".join(result.error_messages)})
        assert kwargs["supports_check_mode"] is True
        return DummyModule(result.validated_parameters)

    adapter = Mock()
    monkeypatch.setattr(module_obj, "AnsibleModule", validate_arguments)
    monkeypatch.setattr(module_obj, "OciNetworkVnicInfoModule", adapter)
    if error:
        with pytest.raises(FailJsonCalled, match=error):
            module_obj.main()
        adapter.assert_not_called()
        return
    module_obj.main()
    assert adapter.call_args.args[0].params["vnic_id"] == "vnic"


@pytest.mark.parametrize("check_mode", [False, True])
@pytest.mark.parametrize("status", [200, 404, 403, 500])
def test_info_get_and_errors(monkeypatch, check_mode, status):
    """Return one unchanged VNIC, handle 404, and propagate other errors."""
    install_fake_oci(monkeypatch)
    module_obj = load_collection_module("oci_network_vnic_info")
    resource = FakeModel(id="vnic", display_name="KeepCase", freeform_tags={"CaseKey": "CaseValue"})
    instance = object.__new__(module_obj.OciNetworkVnicInfoModule)
    instance.module = DummyModule({"vnic_id": "vnic"}, check_mode=check_mode)
    instance.client = types.SimpleNamespace(get_vnic=Mock(return_value=FakeResponse(resource)))
    instance.call_with_retry = lambda fn, **kwargs: fn(**kwargs)
    if status != 200:
        error = Exception("service error")
        error.status = status
        instance.client.get_vnic.side_effect = error
    if status in (403, 500):
        with pytest.raises(Exception) as exc:
            instance.execute_info_module()
        assert exc.value is error
    else:
        with pytest.raises(ExitJsonCalled) as exc:
            instance.execute_info_module()
        expected = [dict(id="vnic", name="KeepCase", freeform_tags={"CaseKey": "CaseValue"})] if status == 200 else []
        assert exc.value.payload == {"changed": False, "vnics": expected}
    instance.client.get_vnic.assert_called_once_with(vnic_id="vnic")
