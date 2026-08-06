from __future__ import absolute_import, division, print_function
__metaclass__ = type

import types

from conftest import (
    DummyModule,
    ExitJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
    raising,
)


def make_instance_info_module(module_obj, params, client=None):
    return make_module_instance(
        module_obj,
        "OciInstanceInfoModule",
        params,
        client=client,
    )


def test_main_requires_compartment_id_or_instance_id(monkeypatch):
    install_fake_oci(monkeypatch)

    module_obj = load_collection_module("oci_instance_info")
    captured = {}

    def fake_ansible_module(**kwargs):
        captured["argument_spec"] = kwargs["argument_spec"]
        captured["required_one_of"] = kwargs["required_one_of"]
        return DummyModule({})

    class FakeComputeInstanceInfoModule:
        def __init__(self, module):
            self.module = module

        def execute_info_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(
        module_obj, "OciInstanceInfoModule", FakeComputeInstanceInfoModule
    )

    module_obj.main()

    assert captured["run_called"] is True
    assert captured["required_one_of"] == [["compartment_id", "instance_id"]]
    assert "availability_domain" in captured["argument_spec"]


def test_fetch_resources_prefers_id_lookup(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_info")
    get_calls = []

    def get_instance(**kwargs):
        get_calls.append(kwargs)
        return FakeResponse(
            data=FakeModel(id=kwargs["instance_id"], display_name="example-instance")
        )

    instance = make_instance_info_module(
        info_module,
        {"instance_id": "ocid1.instance.oc1..example"},
        client=types.SimpleNamespace(get_instance=get_instance),
    )
    monkeypatch.setattr(
        instance,
        "list_all_resources",
        raising(AssertionError("list_all_resources should not be called")),
    )
    monkeypatch.setattr(instance, "call_with_retry", lambda fn, **kwargs: fn(**kwargs))

    resources = instance.fetch_resources()

    assert len(resources) == 1
    assert resources[0].id == "ocid1.instance.oc1..example"
    assert get_calls == [{"instance_id": "ocid1.instance.oc1..example"}]


def test_fetch_resources_lists_by_compartment_and_availability_domain(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_info")
    paginate_calls = []
    instance = make_instance_info_module(
        info_module,
        {
            "compartment_id": "ocid1.compartment.oc1..example",
            "availability_domain": "Uocm:PHX-AD-1",
            "lifecycle_state": "RUNNING",
        },
        client=types.SimpleNamespace(list_instances="list_method"),
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
                "availability_domain": "Uocm:PHX-AD-1",
                "lifecycle_state": "RUNNING",
            },
        )
    ]


def test_run_returns_instances_key(monkeypatch):
    install_fake_oci(monkeypatch)

    info_module = load_collection_module("oci_instance_info")
    resource = FakeModel(
        id="ocid1.instance.oc1..example",
        display_name="example-instance",
        lifecycle_state="RUNNING",
    )
    instance = make_instance_info_module(
        info_module,
        {"compartment_id": "ocid1.compartment.oc1..example"},
    )
    monkeypatch.setattr(instance, "fetch_resources", lambda: [resource])

    try:
        instance.execute_info_module()
        raise AssertionError("execute_info_module should raise ExitJsonCalled")
    except ExitJsonCalled as exc_info:
        assert exc_info.payload == {
            "changed": False,
            "instances": [
                {
                    "id": "ocid1.instance.oc1..example",
                    "name": "example-instance",
                    "lifecycle_state": "RUNNING",
                }
            ],
        }
