# -*- coding: utf-8 -*-
# Copyright (c) 2026, Ansible Content Engineering Team
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: oci_autonomous_database_wallet
short_description: Download the wallet for an Autonomous Database in Oracle Cloud Infrastructure
description:
  - Generates a credentials wallet (zip file) for an OCI Autonomous Database and
    saves it to a file on the Ansible host.
version_added: "1.2.0"
author:
  - Mike Morency (@mikemorency)
extends_documentation_fragment:
  - ansible.oci.oci_auth_options
  - ansible.builtin.files
options:
  autonomous_database_id:
    description:
      - OCID of the Autonomous Database whose wallet is downloaded.
    type: str
    required: true
  dest:
    description:
      - File on the Ansible host to write the wallet zip to.
      - The parent directory must already exist.
      - A newly created file gets mode C(0600) unless O(mode) is set.
      - If O(dest) is a symlink, the wallet is written to the link target and
        file attributes are applied to the target. The link itself is kept.
    type: path
    required: true
  password:
    description:
      - Password used to encrypt the keys inside the wallet.
      - Must be at least 8 characters long and include at least one letter and
        either one numeric or one special character.
    type: str
    required: true
  generate_type:
    description:
      - Type of wallet to generate for a serverless Autonomous Database.
      - C(single) generates a wallet for this database only. C(all) generates a
        regional wallet for all serverless Autonomous Databases in the region.
      - When unset, OCI generates a C(single) wallet for serverless databases.
      - Leave unset for Autonomous Databases on dedicated Exadata infrastructure.
    type: str
    choices: [single, all]
  is_regional:
    description:
      - Whether the wallet uses regional connection strings in PDB connect info.
      - Only applies to cross-region Autonomous Data Guard.
    type: bool
  force:
    description:
      - Whether to download a new wallet when O(dest) already exists.
      - When false, an existing O(dest) is never replaced, regardless of its
        content. File attributes such as O(mode) are still applied.
      - When false and another process creates O(dest) while the wallet is
        downloading, the new wallet is discarded and the task reports no change.
        This requires a filesystem that supports hard links.
      - When true, a new wallet is always generated and replaces O(dest), so the
        task always reports a change.
      - OCI generates new keys every time a wallet is downloaded, so the content
        of an existing file cannot be compared with the remote wallet.
    type: bool
    default: false
notes:
  - Check mode does not request a wallet from OCI. It reports a change when a
    wallet would be downloaded. The OCI client is still configured, so
    authentication settings must be valid.
"""

EXAMPLES = r"""
- name: Download an Autonomous Database wallet
  ansible.oci.oci_autonomous_database_wallet:
    autonomous_database_id: ocid1.autonomousdatabase.oc1..exampleuniqueID
    dest: /home/app/wallets/adb_wallet.zip
    password: "{{ wallet_password }}"

- name: Replace an existing wallet and restrict access to one group
  ansible.oci.oci_autonomous_database_wallet:
    autonomous_database_id: ocid1.autonomousdatabase.oc1..exampleuniqueID
    dest: /etc/app/adb_wallet.zip
    password: "{{ wallet_password }}"
    force: true
    owner: root
    group: app
    mode: "0640"

- name: Download a regional wallet for all serverless databases in the region
  ansible.oci.oci_autonomous_database_wallet:
    autonomous_database_id: ocid1.autonomousdatabase.oc1..exampleuniqueID
    dest: /tmp/regional_wallet.zip
    password: "{{ wallet_password }}"
    generate_type: all
"""

RETURN = r"""
dest:
  description: Path of the wallet file on the Ansible host.
  returned: always
  type: str
  sample: /home/app/wallets/adb_wallet.zip
"""

import os
import tempfile

from ansible.module_utils.basic import AnsibleModule

from ansible_collections.ansible.oci.plugins.module_utils.oci_base import OciModuleBase
from ansible_collections.ansible.oci.plugins.module_utils.oci_common import (
    OCI_AUTH_ARGS,
    build_model,
    import_oci_sdk,
)

oci = import_oci_sdk()[0]

DOWNLOAD_CHUNK_SIZE = 1024 * 1024


class OciAutonomousDatabaseWalletModule(OciModuleBase):
    """Download an Autonomous Database wallet to the Ansible host."""

    @property
    def client_class(self):
        """Return the SDK client class.

        Returns:
            type: OCI Database client class.
        """
        return oci.database.DatabaseClient

    def validate_arguments(self, destination):
        """Fail the module when ``destination`` cannot hold the wallet file.

        Args:
            destination (str): Resolved local path for the wallet zip.
        """
        if os.path.isdir(destination):
            self.module.fail_json(msg="dest must be a file path, not a directory")
        parent = os.path.dirname(destination)
        if not os.path.isdir(parent):
            self.module.fail_json(msg=f"Destination directory {parent} does not exist")

    def generate_wallet(self):
        """Request a new wallet from OCI.

        Returns:
            oci.response.Response: Response whose data is the streamed zip body.

        Raises:
            oci.exceptions.ServiceError: If OCI rejects the wallet request.
        """
        params = self.module.params
        details = build_model(
            params,
            oci.database.models.GenerateAutonomousDatabaseWalletDetails,
            keys=("password", "generate_type", "is_regional"),
            enum_keys=frozenset({"generate_type"}),
        )
        return self.call_with_retry(
            self.client.generate_autonomous_database_wallet,
            autonomous_database_id=params["autonomous_database_id"],
            generate_autonomous_database_wallet_details=details,
        )

    def download_wallet(self, destination):
        """Stream a new wallet to a temporary file and move it to ``destination``.

        Args:
            destination (str): Resolved local path for the wallet zip.

        Returns:
            bool: Whether ``destination`` was written.
        """
        try:
            response = self.generate_wallet()
        except oci.exceptions.ServiceError as exc:
            self.module.fail_json(
                msg=f"Failed to generate the Autonomous Database wallet: {exc}"
            )
        try:
            return self.write_wallet(response.data, destination)
        except OSError as exc:
            # Covers local file errors (permissions, disk full) and interrupted
            # downloads, since requests' stream errors derive from OSError.
            self.module.fail_json(
                msg=f"Failed to write the Autonomous Database wallet to {destination}: {exc}"
            )
        finally:
            response.data.close()

    def write_wallet(self, body, destination):
        """Write a streamed wallet body to ``destination`` with private permissions.

        Args:
            body: Streamed wallet response body.
            destination (str): Resolved local path for the wallet zip.

        Returns:
            bool: Whether ``destination`` was written. False when O(force) is
            false and another process created ``destination`` during the download.
        """
        # Stage beside the destination so the final move stays atomic.
        # mkstemp creates the file with mode 0600.
        file_descriptor, temporary = tempfile.mkstemp(
            prefix=".ansible-oci-wallet-",
            dir=os.path.dirname(destination),
        )
        try:
            with os.fdopen(file_descriptor, "wb") as output:
                for chunk in body.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                    output.write(chunk)
            if not self.module.params["force"]:
                # Linking refuses to overwrite a destination created during the download.
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    return False
                return True
            creating = not os.path.exists(destination)
            # atomic_move gives a newly created file the umask-based default
            # mode. Tighten the umask so the wallet is never readable by others
            # during the move, then set the mode explicitly afterwards.
            previous_umask = os.umask(0o077)
            try:
                self.module.atomic_move(
                    temporary,
                    destination,
                    unsafe_writes=self.module.params["unsafe_writes"],
                )
            finally:
                os.umask(previous_umask)
            if creating:
                os.chmod(destination, 0o600)
            return True
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def execute_module(self):
        """Download the wallet unless ``dest`` exists, then apply file attributes."""
        params = self.module.params
        # Follow symlinks so the wallet replaces the link target, not the link.
        # A dangling link resolves to its missing target, which is downloaded.
        destination = os.path.realpath(params["dest"])
        self.validate_arguments(destination)

        changed = False
        if params["force"] or not os.path.exists(destination):
            changed = True
            if not self.module.check_mode:
                changed = self.download_wallet(destination)

        file_args = self.module.load_file_common_arguments(params, path=destination)
        if not (changed and self.module.check_mode):
            changed = self.module.set_fs_attributes_if_different(file_args, changed)
        self.module.exit_json(changed=changed, dest=params["dest"])


def main():
    """Create the Ansible module and download the requested wallet."""
    argument_spec = dict(
        OCI_AUTH_ARGS,
        autonomous_database_id=dict(type="str", required=True),
        dest=dict(type="path", required=True),
        password=dict(type="str", required=True, no_log=True),
        generate_type=dict(type="str", choices=["single", "all"]),
        is_regional=dict(type="bool"),
        force=dict(type="bool", default=False),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        add_file_common_args=True,
        supports_check_mode=True,
    )
    OciAutonomousDatabaseWalletModule(module).execute_module()


if __name__ == "__main__":
    main()
