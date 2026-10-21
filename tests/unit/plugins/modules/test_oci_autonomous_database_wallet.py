from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import stat
import types

import pytest

from .conftest import (
    DummyModule,
    ExitJsonCalled,
    FailJsonCalled,
    FakeModel,
    FakeResponse,
    install_fake_oci,
    load_collection_module,
    make_module_instance,
)

ADB_ID = "ocid1.autonomousdatabase.oc1..example"
WALLET_CHUNKS = (b"PK\x03\x04", b"wallet-body")


class FileModule(DummyModule):
    """DummyModule with stand-ins for the AnsibleModule file helpers."""

    def __init__(self, params=None, check_mode=False):
        super().__init__(params, check_mode=check_mode)
        self.unsafe_writes = []

    def atomic_move(self, src, dest, unsafe_writes=False):
        self.unsafe_writes.append(unsafe_writes)
        creating = not os.path.exists(dest)
        os.replace(src, dest)
        if creating:
            # Mirror AnsibleModule.atomic_move, which applies the umask to new files.
            umask = os.umask(0)
            os.umask(umask)
            os.chmod(dest, 0o666 & ~umask)

    def load_file_common_arguments(self, params, path=None):
        return {"path": path or params["dest"], "mode": params.get("mode")}

    def set_fs_attributes_if_different(self, file_args, changed):
        mode = file_args["mode"]
        if mode is None:
            return changed
        mode = int(mode, 8)
        if stat.S_IMODE(os.stat(file_args["path"]).st_mode) == mode:
            return changed
        if not self.check_mode:
            os.chmod(file_args["path"], mode)
        return True


class WalletBody:
    def __init__(self, chunks, error=None):
        self.chunks = chunks
        self.error = error
        self.closed = False

    def iter_content(self, chunk_size):
        yield from self.chunks
        if self.error is not None:
            raise self.error

    def close(self):
        self.closed = True


class DatabaseClient:
    def __init__(self, chunks=WALLET_CHUNKS, error=None, service_error=None):
        self.chunks = chunks
        self.error = error
        self.service_error = service_error
        self.requests = []
        self.bodies = []

    def generate_autonomous_database_wallet(self, **kwargs):
        self.requests.append(kwargs)
        if self.service_error is not None:
            raise self.service_error
        body = WalletBody(self.chunks, self.error)
        self.bodies.append(body)
        return FakeResponse(body)


def load_wallet_module(monkeypatch):
    module_obj, _service_error = load_wallet_module_with_errors(monkeypatch)
    return module_obj


def load_wallet_module_with_errors(monkeypatch):
    oci_module, service_error = install_fake_oci(monkeypatch)
    oci_module.database = types.SimpleNamespace(
        DatabaseClient=type("FakeDatabaseClient", (), {}),
        models=types.SimpleNamespace(GenerateAutonomousDatabaseWalletDetails=FakeModel),
    )
    return load_collection_module("oci_autonomous_database_wallet"), service_error


def base_params(destination, **kwargs):
    params = {
        "autonomous_database_id": ADB_ID,
        "dest": str(destination),
        "password": "WalletPass1",
        "generate_type": None,
        "is_regional": None,
        "force": False,
        "mode": None,
        "unsafe_writes": False,
    }
    params.update(kwargs)
    return params


def run(module_obj, monkeypatch, client, params, check_mode=False, file_module=FileModule):
    instance = make_module_instance(
        module_obj,
        "OciAutonomousDatabaseWalletModule",
        params,
        client=client,
        check_mode=check_mode,
    )
    instance.module = file_module(params, check_mode=check_mode)
    monkeypatch.setattr(
        instance, "call_with_retry", lambda fn, *args, **kwargs: fn(*args, **kwargs)
    )
    with pytest.raises(ExitJsonCalled) as result:
        instance.execute_module()
    return result.value.payload


def file_mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def test_main_wires_argument_spec_and_runs_module(monkeypatch):
    module_obj = load_wallet_module(monkeypatch)
    captured = {}

    def fake_ansible_module(**kwargs):
        captured.update(kwargs)
        return DummyModule({})

    class FakeWalletModule:
        def __init__(self, module):
            self.module = module

        def execute_module(self):
            captured["run_called"] = True

    monkeypatch.setattr(module_obj, "AnsibleModule", fake_ansible_module)
    monkeypatch.setattr(module_obj, "OciAutonomousDatabaseWalletModule", FakeWalletModule)

    module_obj.main()

    spec = captured["argument_spec"]
    assert captured["run_called"] is True
    assert captured["supports_check_mode"] is True
    assert captured["add_file_common_args"] is True
    assert spec["password"] == {"type": "str", "required": True, "no_log": True}
    assert spec["dest"] == {"type": "path", "required": True}
    assert spec["generate_type"]["choices"] == ["single", "all"]
    assert spec["force"] == {"type": "bool", "default": False}


def test_check_mode_reports_change_without_calling_oci(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"
    client = DatabaseClient()

    result = run(module_obj, monkeypatch, client, base_params(destination), check_mode=True)

    assert result == {"changed": True, "dest": str(destination)}
    assert client.requests == []
    assert not destination.exists()


def test_download_writes_private_wallet_and_rerun_is_unchanged(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"
    client = DatabaseClient()
    previous_umask = os.umask(0o022)
    try:
        result = run(module_obj, monkeypatch, client, base_params(destination))
        # The module tightens the umask only around the move and restores it.
        assert os.umask(0o022) == 0o022
    finally:
        os.umask(previous_umask)

    assert result == {"changed": True, "dest": str(destination)}
    assert destination.read_bytes() == b"".join(WALLET_CHUNKS)
    assert file_mode(destination) == 0o600
    assert not list(tmp_path.glob(".ansible-oci-wallet-*"))
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request["autonomous_database_id"] == ADB_ID
    assert vars(request["generate_autonomous_database_wallet_details"]) == {
        "password": "WalletPass1",
    }

    for check_mode in (False, True):
        rerun = run(module_obj, monkeypatch, client, base_params(destination), check_mode=check_mode)
        assert rerun["changed"] is False
    assert len(client.requests) == 1


def test_download_sends_generate_type_and_is_regional(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    client = DatabaseClient()

    run(
        module_obj,
        monkeypatch,
        client,
        base_params(tmp_path / "wallet.zip", generate_type="all", is_regional=False),
    )

    assert vars(client.requests[0]["generate_autonomous_database_wallet_details"]) == {
        "password": "WalletPass1",
        "generate_type": "ALL",
        "is_regional": False,
    }


def test_download_applies_requested_mode(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"

    result = run(module_obj, monkeypatch, DatabaseClient(), base_params(destination, mode="0640"))

    assert result["changed"] is True
    assert file_mode(destination) == 0o640


def test_existing_dest_is_kept_but_file_attributes_are_applied(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"
    destination.write_bytes(b"existing")
    os.chmod(destination, 0o644)
    client = DatabaseClient()
    params = base_params(destination, mode="0600")

    checked = run(module_obj, monkeypatch, client, params, check_mode=True)
    assert checked["changed"] is True
    assert file_mode(destination) == 0o644

    result = run(module_obj, monkeypatch, client, params)
    assert result["changed"] is True
    assert file_mode(destination) == 0o600

    rerun = run(module_obj, monkeypatch, client, params)
    assert rerun["changed"] is False
    assert destination.read_bytes() == b"existing"
    assert client.requests == []


def test_force_replaces_existing_dest(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"
    destination.write_bytes(b"existing")
    client = DatabaseClient()
    params = base_params(destination, force=True)

    checked = run(module_obj, monkeypatch, client, params, check_mode=True)
    assert checked["changed"] is True
    assert destination.read_bytes() == b"existing"
    assert client.requests == []

    result = run(module_obj, monkeypatch, client, params)
    assert result["changed"] is True
    assert destination.read_bytes() == b"".join(WALLET_CHUNKS)
    assert len(client.requests) == 1


def test_failed_download_preserves_dest_and_removes_temporary_file(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"
    destination.write_bytes(b"existing")
    client = DatabaseClient(error=ConnectionError("stream interrupted"))

    with pytest.raises(FailJsonCalled) as result:
        run(module_obj, monkeypatch, client, base_params(destination, force=True))

    assert result.value.payload["msg"] == (
        f"Failed to write the Autonomous Database wallet to {destination}: "
        "stream interrupted"
    )
    assert destination.read_bytes() == b"existing"
    assert not list(tmp_path.glob(".ansible-oci-wallet-*"))
    assert client.bodies[0].closed is True


def test_successful_download_closes_response_body(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    client = DatabaseClient()

    run(module_obj, monkeypatch, client, base_params(tmp_path / "wallet.zip"))

    assert client.bodies[0].closed is True


def test_service_error_fails_cleanly(monkeypatch, tmp_path):
    module_obj, service_error = load_wallet_module_with_errors(monkeypatch)
    destination = tmp_path / "wallet.zip"
    client = DatabaseClient(service_error=service_error(400, "invalid password"))

    with pytest.raises(FailJsonCalled) as result:
        run(module_obj, monkeypatch, client, base_params(destination))

    assert result.value.payload["msg"] == (
        "Failed to generate the Autonomous Database wallet: invalid password"
    )
    assert not destination.exists()
    assert not list(tmp_path.glob(".ansible-oci-wallet-*"))


def test_unsafe_writes_is_passed_to_atomic_move(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    modules = []

    class RecordingFileModule(FileModule):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            modules.append(self)

    run(
        module_obj,
        monkeypatch,
        DatabaseClient(),
        base_params(tmp_path / "wallet.zip", force=True, unsafe_writes=True),
        file_module=RecordingFileModule,
    )

    assert modules[0].unsafe_writes == [True]


def test_new_wallet_is_private_even_if_atomic_move_ignores_umask(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"

    class PermissiveFileModule(FileModule):
        def atomic_move(self, src, dest, unsafe_writes=False):
            os.replace(src, dest)
            os.chmod(dest, 0o644)

    run(
        module_obj,
        monkeypatch,
        DatabaseClient(),
        base_params(destination, force=True),
        file_module=PermissiveFileModule,
    )

    assert file_mode(destination) == 0o600


def test_force_writes_through_symlink(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    target = tmp_path / "wallets" / "current.zip"
    target.parent.mkdir()
    target.write_bytes(b"existing")
    link = tmp_path / "wallet.zip"
    link.symlink_to(target)

    result = run(
        module_obj, monkeypatch, DatabaseClient(), base_params(link, force=True, mode="0640")
    )

    assert result == {"changed": True, "dest": str(link)}
    assert link.is_symlink()
    assert target.read_bytes() == b"".join(WALLET_CHUNKS)
    assert file_mode(target) == 0o640


def test_dangling_symlink_downloads_to_target(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    target = tmp_path / "current.zip"
    link = tmp_path / "wallet.zip"
    link.symlink_to(target)
    client = DatabaseClient()

    result = run(module_obj, monkeypatch, client, base_params(link))

    assert result["changed"] is True
    assert link.is_symlink()
    assert target.read_bytes() == b"".join(WALLET_CHUNKS)
    assert file_mode(target) == 0o600
    assert len(client.requests) == 1


def test_directory_dest_fails(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)

    with pytest.raises(FailJsonCalled) as result:
        run(module_obj, monkeypatch, DatabaseClient(), base_params(tmp_path))

    assert result.value.payload["msg"] == "dest must be a file path, not a directory"


def test_missing_parent_directory_fails(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "missing" / "wallet.zip"

    with pytest.raises(FailJsonCalled) as result:
        run(module_obj, monkeypatch, DatabaseClient(), base_params(destination))

    assert result.value.payload["msg"] == (
        f"Destination directory {tmp_path / 'missing'} does not exist"
    )
    assert not destination.parent.exists()


def test_temporary_file_creation_error_fails_cleanly(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"
    client = DatabaseClient()

    def deny(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(module_obj.tempfile, "mkstemp", deny)

    with pytest.raises(FailJsonCalled) as result:
        run(module_obj, monkeypatch, client, base_params(destination))

    assert result.value.payload["msg"] == (
        f"Failed to write the Autonomous Database wallet to {destination}: "
        "[Errno 13] Permission denied"
    )
    assert not destination.exists()
    assert client.bodies[0].closed is True


def test_dest_created_during_download_is_kept_without_force(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"

    def chunks_racing_another_writer():
        yield WALLET_CHUNKS[0]
        destination.write_bytes(b"created by another task")
        yield WALLET_CHUNKS[1]

    class FailingMoveFileModule(FileModule):
        def atomic_move(self, src, dest, unsafe_writes=False):
            raise AssertionError("atomic_move must not replace dest when force is false")

    result = run(
        module_obj,
        monkeypatch,
        DatabaseClient(chunks=chunks_racing_another_writer()),
        base_params(destination),
        file_module=FailingMoveFileModule,
    )

    assert result == {"changed": False, "dest": str(destination)}
    assert destination.read_bytes() == b"created by another task"
    assert not list(tmp_path.glob(".ansible-oci-wallet-*"))


def test_new_wallet_without_force_is_private_regardless_of_umask(monkeypatch, tmp_path):
    module_obj = load_wallet_module(monkeypatch)
    destination = tmp_path / "wallet.zip"
    previous_umask = os.umask(0)
    try:
        run(module_obj, monkeypatch, DatabaseClient(), base_params(destination))
    finally:
        os.umask(previous_umask)

    assert file_mode(destination) == 0o600
    assert os.stat(destination).st_nlink == 1
