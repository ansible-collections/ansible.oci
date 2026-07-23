import importlib.util
import sys
import types
from pathlib import Path


COLLECTION_ROOT = Path(__file__).resolve().parents[3]
COLLECTION_PACKAGES = {
    "ansible_collections": COLLECTION_ROOT.parent.parent,
    "ansible_collections.oracle": COLLECTION_ROOT.parent,
    "ansible_collections.oracle.oci": COLLECTION_ROOT,
    "ansible_collections.oracle.oci.plugins": COLLECTION_ROOT / "plugins",
    "ansible_collections.oracle.oci.plugins.module_utils": COLLECTION_ROOT
    / "plugins"
    / "module_utils",
    "ansible_collections.oracle.oci.plugins.modules": COLLECTION_ROOT
    / "plugins"
    / "modules",
}


def _ensure_collection_packages():
    for package_name, package_path in COLLECTION_PACKAGES.items():
        package = sys.modules.get(package_name)
        if package is None:
            package = types.ModuleType(package_name)
            sys.modules[package_name] = package
        package.__path__ = [str(package_path)]
        if package_name == "ansible_collections.oracle.oci":
            package._collection_meta = getattr(package, "_collection_meta", {})


def _resolve_plugin_dir(module_name, preferred_dir):
    candidate_dirs = (preferred_dir, "module_utils", "modules")
    for candidate_dir in candidate_dirs:
        module_path = COLLECTION_ROOT / "plugins" / candidate_dir / f"{module_name}.py"
        if module_path.is_file():
            return candidate_dir
    return preferred_dir


def load_collection_module(module_name, plugin_dir="modules"):
    _ensure_collection_packages()
    plugin_dir = _resolve_plugin_dir(module_name, plugin_dir)

    module_path = COLLECTION_ROOT / "plugins" / plugin_dir / f"{module_name}.py"
    qualified_name = (
        f"ansible_collections.oracle.oci.plugins.{plugin_dir}.{module_name}"
    )

    sys.modules.pop(qualified_name, None)

    spec = importlib.util.spec_from_file_location(qualified_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified_name] = module
    spec.loader.exec_module(module)
    return module
