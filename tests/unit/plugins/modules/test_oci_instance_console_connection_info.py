from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

import pytest

from conftest import (
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_console_connection_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciInstanceConsoleConnectionInfoModule",
        params,
        client=client,
    )


def test_main_requires_compartment_id_or_instance_console_connection_id(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_instance_console_connection_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["required_one_of"] = kwargs["required_one_of"]
        return types.SimpleNamespace()

    class FakeConsoleConnectionInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj,
        "OciInstanceConsoleConnectionInfoModule",
        FakeConsoleConnectionInfoModule,
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["required_one_of"] == [
        ["compartment_id", "instance_console_connection_id"]
    ]
    assert captured["argument_spec"]["instance_console_connection_id"] == {
        "type": "str"
    }
    assert captured["argument_spec"]["instance_id"] == {"type": "str"}
    assert captured["argument_spec"]["lifecycle_state"] == {"type": "str"}
    # Console connections have no display name in the OCI API, so the
    # shared name-lookup filter must not be exposed.
    assert "name" not in captured["argument_spec"]


def test_name_filter_param_is_disabled(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_console_connection_info")

    assert (
        info_module.OciInstanceConsoleConnectionInfoModule.name_filter_param is None
    )


def test_fetch_resources_prefers_id_lookup(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_console_connection_info")
    get_calls = []

    def get_instance_console_connection(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(
                id=kwargs["instance_console_connection_id"],
                lifecycle_state="ACTIVE",
            )
        )

    instance = make_console_connection_info_module(
        info_module,
        {"instance_console_connection_id": "ocid1.instanceconsoleconnection.oc1..example"},
        client=types.SimpleNamespace(
            get_instance_console_connection=get_instance_console_connection
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("list_all_resources should not be called")),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    resources = instance.fetch_resources()

    assert get_calls == [
        {"instance_console_connection_id": "ocid1.instanceconsoleconnection.oc1..example"}
    ]
    assert len(resources) == 1
    assert resources[0].id == "ocid1.instanceconsoleconnection.oc1..example"


def test_fetch_resources_returns_empty_list_on_404(monkeypatch):
    _oci_module, ServiceError = install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_console_connection_info")

    def get_missing_console_connection(**kwargs):
        raise ServiceError(404, "missing")

    instance = make_console_connection_info_module(
        info_module,
        {"instance_console_connection_id": "ocid1.instanceconsoleconnection.oc1..missing"},
        client=types.SimpleNamespace(
            get_instance_console_connection=get_missing_console_connection
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == []


def test_fetch_resources_lists_with_compartment_and_instance_filters(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_console_connection_info")
    paginate_calls = []
    instance = make_console_connection_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "instance_id": "ocid1.instance.oc1..example",
        },
        client=types.SimpleNamespace(
            list_instance_console_connections="list_method"
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    resources = instance.fetch_resources()

    assert resources == []
    assert paginate_calls == [
        (
            "list_method",
            {
                "compartment_id": "ocid1.compartment.oc1..example",
                "instance_id": "ocid1.instance.oc1..example",
            },
        )
    ]


def test_fetch_resources_does_not_send_lifecycle_state_as_a_list_filter(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_console_connection_info")
    paginate_calls = []
    instance = make_console_connection_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "lifecycle_state": "ACTIVE",
        },
        client=types.SimpleNamespace(
            list_instance_console_connections="list_method"
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: paginate_calls.append((list_fn, kwargs)) or [],
    )

    instance.fetch_resources()

    assert paginate_calls == [
        ("list_method", {"compartment_id": "ocid1.compartment.oc1..example"})
    ]


def test_fetch_resources_filters_list_results_by_lifecycle_state_locally(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_console_connection_info")
    active_connection = FakeModel(
        id="ocid1.instanceconsoleconnection.oc1..active",
        lifecycle_state="ACTIVE",
    )
    deleted_connection = FakeModel(
        id="ocid1.instanceconsoleconnection.oc1..deleted",
        lifecycle_state="DELETED",
    )
    instance = make_console_connection_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "lifecycle_state": "ACTIVE",
        },
        client=types.SimpleNamespace(
            list_instance_console_connections="list_method"
        ),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        lambda list_fn, **kwargs: [deleted_connection, active_connection],
    )

    resources = instance.fetch_resources()

    assert resources == [active_connection]


def test_fetch_resources_filters_id_lookup_result_by_lifecycle_state(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_console_connection_info")
    instance = make_console_connection_info_module(
        info_module,
        {
            "instance_console_connection_id": "ocid1.instanceconsoleconnection.oc1..example",
            "lifecycle_state": "ACTIVE",
        },
        client=types.SimpleNamespace(
            get_instance_console_connection=lambda **kwargs: FakeResponse(
                data=FakeModel(
                    id=kwargs["instance_console_connection_id"],
                    lifecycle_state="DELETED",
                )
            )
        ),
    )
    monkeypatch.setattr(
        instance,
        "call_with_retry",
        lambda fn, **kwargs: fn(**kwargs),
    )

    assert instance.fetch_resources() == []


def test_run_returns_results_key(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_console_connection_info")
    resource = FakeModel(
        id="ocid1.instanceconsoleconnection.oc1..example",
        compartment_id="ocid1.compartment.oc1..example",
        instance_id="ocid1.instance.oc1..example",
        lifecycle_state="ACTIVE",
        connection_string="ssh -o ProxyCommand=... instance-console",
    )
    instance = make_console_connection_info_module(
        info_module,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    with pytest.raises(ExitJsonCalled) as exc_info:
        instance.execute_info_module()

    assert exc_info.value.payload == {
        "changed": False,
        "instance_console_connections": [
            {
                "id": "ocid1.instanceconsoleconnection.oc1..example",
                "compartment_id": "ocid1.compartment.oc1..example",
                "instance_id": "ocid1.instance.oc1..example",
                "lifecycle_state": "ACTIVE",
                "connection_string": "ssh -o ProxyCommand=... instance-console",
            }
        ],
    }
