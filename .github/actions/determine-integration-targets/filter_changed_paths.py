#!/usr/bin/env python3
"""Filter metadata registrations already covered by new modules."""

import re
import subprocess
import sys

import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    """Reject duplicate YAML keys."""

    def construct_mapping(self, node, deep=False):
        keys = [self.construct_object(key, deep=deep) for key, _ in node.value]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate metadata key")
        return super().construct_mapping(node, deep=deep)


def only_new_module_registrations(before, after, added_files):
    """Return whether metadata only registers modules added by the PR."""
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    old_groups = before.get("action_groups")
    new_groups = after.get("action_groups")
    if not isinstance(old_groups, dict) or not isinstance(new_groups, dict):
        return False
    old_members = old_groups.get("oci")
    new_members = new_groups.get("oci")
    for members in (old_members, new_members):
        if not isinstance(members, list):
            return False
        if not all(isinstance(member, str) and re.fullmatch(r"[a-z][a-z0-9_]*", member) for member in members):
            return False
        if len(members) != len(set(members)):
            return False

    added_members = set(new_members) - set(old_members)
    if not added_members:
        return False
    if not all(f"plugins/modules/{member}.py" in added_files for member in added_members):
        return False

    remaining_members = [member for member in new_members if member not in added_members]
    normalized = dict(after, action_groups=dict(new_groups, oci=remaining_members))
    return normalized == before


def git(*args):
    """Read data from the disposable collection checkout."""
    return subprocess.check_output(["git", *args], text=True)


def filter_paths(paths, base):
    """Keep metadata unless the registration exception applies."""
    if "meta/runtime.yml" not in paths:
        return paths
    try:
        before = yaml.load(git("show", f"{base}:meta/runtime.yml"), Loader=UniqueKeyLoader)
        after = yaml.load(git("show", "HEAD:meta/runtime.yml"), Loader=UniqueKeyLoader)
        added_files = set(git(
            "diff", "--name-only", "--no-renames", "--diff-filter=A",
            base, "HEAD", "--", "plugins/modules/",
        ).splitlines())
        covered = only_new_module_registrations(before, after, added_files)
    except (subprocess.CalledProcessError, yaml.YAMLError, ValueError, TypeError):
        covered = False
    if not covered:
        print("Metadata requires full integration selection.", file=sys.stderr)
        return paths
    print("Metadata only registers new modules; select tests from the remaining changed paths.", file=sys.stderr)
    return [path for path in paths if path != "meta/runtime.yml"]


def main():
    """Write the paths for native Ansible test selection."""
    paths = filter_paths(sys.stdin.read().splitlines(), sys.argv[1])
    if paths:
        print("\n".join(paths))


if __name__ == "__main__":
    main()
