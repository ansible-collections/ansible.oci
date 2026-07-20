import importlib.util
import sys
import types
from pathlib import Path


COLLECTION_ROOT = Path(__file__).resolve().parents[4]
COLLECTION_PACKAGES = {
    "ansible_collections": COLLECTION_ROOT.parent.parent,
    "ansible_collections.oracle": COLLECTION_ROOT.parent,
    "ansible_collections.oracle.oci": COLLECTION_ROOT,
    "ansible_collections.oracle.oci.plugins": COLLECTION_ROOT / "plugins",
    "ansible_collections.oracle.oci.plugins.module_utils": COLLECTION_ROOT
    / "plugins"
    / "module_utils",
}


def _ensure_collection_packages():
    for package_name, package_path in COLLECTION_PACKAGES.items():
        package = sys.modules.get(package_name)
        if package is None:
            package = types.ModuleType(package_name)
            sys.modules[package_name] = package
        package.__path__ = [str(package_path)]


def load_collection_module(module_name):
    _ensure_collection_packages()

    module_path = COLLECTION_ROOT / "plugins" / "module_utils" / f"{module_name}.py"
    qualified_name = (
        f"ansible_collections.oracle.oci.plugins.module_utils.{module_name}"
    )

    sys.modules.pop(qualified_name, None)

    spec = importlib.util.spec_from_file_location(qualified_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified_name] = module
    spec.loader.exec_module(module)
    return module
