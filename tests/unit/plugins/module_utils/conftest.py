import sys
from pathlib import Path

HELPER_DIR = Path(__file__).resolve().parents[1]
if str(HELPER_DIR) not in sys.path:
    sys.path.insert(0, str(HELPER_DIR))

from shared_loader import load_collection_module as _load_collection_module


def load_collection_module(module_name):
    return _load_collection_module(module_name, plugin_dir="module_utils")
