from __future__ import absolute_import, division, print_function
__metaclass__ = type

import importlib
import sys
import types


def load_collection_module(module_name, plugin_dir="modules"):
    qualified_name = f"ansible_collections.oracle.oci.plugins.{plugin_dir}.{module_name}"
    sys.modules.pop(qualified_name, None)
    return importlib.import_module(qualified_name)


class FailJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class ExitJsonCalled(Exception):
    def __init__(self, payload):
        self.payload = payload


class DummyModule:
    def __init__(self, params=None, check_mode=False):
        self.params = params or {}
        self.check_mode = check_mode

    def fail_json(self, **kwargs):
        raise FailJsonCalled(kwargs)

    def exit_json(self, **kwargs):
        raise ExitJsonCalled(kwargs)


class FakeModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class FakeResponse:
    def __init__(self, data=None, headers=None):
        self.data = data
        self.headers = headers or {}


class FakeVirtualNetworkClient:
    pass


class FakeComputeClient:
    pass


class FakeWorkRequestClient:
    pass


def install_fake_oci(monkeypatch, *, model_names=(), include_work_requests=False):
    oci_module = types.ModuleType("oci")
    exceptions_module = types.ModuleType("oci.exceptions")

    class ServiceError(Exception):
        def __init__(self, status, message="service error"):
            super().__init__(message)
            self.status = status
            self.message = message

    exceptions_module.ServiceError = ServiceError
    oci_module.exceptions = exceptions_module
    oci_module.core = types.SimpleNamespace(
        VirtualNetworkClient=FakeVirtualNetworkClient,
        ComputeClient=FakeComputeClient,
        models=types.SimpleNamespace(
            **{model_name: FakeModel for model_name in model_names}
        ),
    )
    if include_work_requests:
        oci_module.work_requests = types.SimpleNamespace(
            WorkRequestClient=FakeWorkRequestClient,
        )

    monkeypatch.setitem(sys.modules, "oci", oci_module)
    monkeypatch.setitem(sys.modules, "oci.exceptions", exceptions_module)

    return oci_module, ServiceError


def raising(exception):
    """Return a callable that raises ``exception`` when invoked, ignoring any arguments.

    Handy as a ``monkeypatch.setattr`` replacement for methods that should
    not be called during a given test path.
    """

    def implementation(*args, **kwargs):
        raise exception

    return implementation


def make_module_instance(
    module_obj,
    class_name,
    params,
    client=None,
    check_mode=False,
    **extra_attrs,
):
    instance = object.__new__(getattr(module_obj, class_name))
    instance.module = DummyModule(params, check_mode=check_mode)
    instance.client = client or types.SimpleNamespace()
    instance.check_mode = check_mode
    for attr_name, value in extra_attrs.items():
        setattr(instance, attr_name, value)
    return instance
