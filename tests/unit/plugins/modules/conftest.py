import sys
import types
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parents[1]
if str(HELPER_DIR) not in sys.path:
    sys.path.insert(0, str(HELPER_DIR))

from shared_loader import load_collection_module as _load_collection_module


def load_collection_module(module_name, plugin_dir="modules"):
    return _load_collection_module(module_name, plugin_dir=plugin_dir)


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
