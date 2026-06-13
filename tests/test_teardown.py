from __future__ import annotations

from pathlib import Path

from torhubgen.lifecycle import ApplianceState
from torhubgen.teardown import teardown


SERVICE_ID = "a" * 56


class FakeController:
    def __init__(self, *, fail_del: bool = False, fail_shutdown: bool = False) -> None:
        self.fail_del = fail_del
        self.fail_shutdown = fail_shutdown
        self.commands: list[str] = []
        self.closed = False

    def msg(self, command: str) -> None:
        self.commands.append(command)
        if command.startswith("DEL_ONION") and self.fail_del:
            raise RuntimeError("DEL failed")
        if command == "SIGNAL SHUTDOWN" and self.fail_shutdown:
            raise RuntimeError("shutdown failed")

    def close(self) -> None:
        self.closed = True


class FakeWebServer:
    def __init__(self, *, fail_stop: bool = False, fail_clear: bool = False) -> None:
        self.fail_stop = fail_stop
        self.fail_clear = fail_clear
        self.stop_called = False
        self.clear_called = False

    def stop(self, *, timeout: float = 5.0) -> None:
        self.stop_called = True
        if self.fail_stop:
            raise RuntimeError("stop failed")

    def clear(self) -> None:
        self.clear_called = True
        if self.fail_clear:
            raise RuntimeError("clear failed")


class FakeTorProcess:
    def __init__(self, *, poll_value=None, wait_error: Exception | None = None) -> None:
        self._poll_value = poll_value
        self.returncode = poll_value
        self.wait_error = wait_error
        self.terminated = False
        self.killed = False

    def poll(self):
        return self._poll_value

    def wait(self, timeout: float) -> int:
        if self.wait_error is not None:
            raise self.wait_error
        if self.returncode is None:
            self.returncode = 0
            self._poll_value = 0
        return self.returncode

    def terminate(self) -> None:
        self.terminated = True
        self.returncode = 0
        self._poll_value = 0

    def kill(self) -> None:
        self.killed = True
        self.returncode = -9
        self._poll_value = -9


def test_teardown_attempts_required_steps_and_deletes_tempdir(tmp_path: Path) -> None:
    data_dir = tmp_path / "tor-data"
    data_dir.mkdir()

    controller = FakeController()
    web_server = FakeWebServer()
    tor_process = FakeTorProcess()
    state = ApplianceState(
        data_dir=str(data_dir),
        tor_process=tor_process,
        control_port=9051,
        controller=controller,
        onion_service_id=SERVICE_ID,
        web_server=web_server,
    )

    report = teardown(state)

    assert report.exit_code == 0
    assert report.step("onion_service_removal").status == "ok"
    assert report.step("web_server_stop").status == "ok"
    assert report.step("message_memory_clear").status == "ok"
    assert report.step("tor_process_stop").status == "ok"
    assert report.step("temp_data_dir_deletion").status == "ok"
    assert controller.commands == [f"DEL_ONION {SERVICE_ID}", "SIGNAL SHUTDOWN"]
    assert controller.closed is True
    assert web_server.stop_called is True
    assert web_server.clear_called is True
    assert not data_dir.exists()


def test_teardown_failure_is_loud_and_visible(tmp_path: Path, monkeypatch, capsys) -> None:
    data_dir = tmp_path / "tor-data"
    data_dir.mkdir()

    state = ApplianceState(
        data_dir=str(data_dir),
        tor_process=FakeTorProcess(),
        control_port=9051,
        controller=FakeController(fail_del=True),
        onion_service_id=SERVICE_ID,
        web_server=FakeWebServer(),
    )

    def fail_rmtree(path: str, *, ignore_errors: bool = False) -> None:
        raise PermissionError("locked")

    monkeypatch.setattr("torhubgen.teardown.shutil.rmtree", fail_rmtree)

    report = teardown(state)
    stderr = capsys.readouterr().err

    assert report.exit_code == 2
    assert report.step("onion_service_removal").status == "failed"
    assert report.step("web_server_stop").status == "ok"
    assert report.step("message_memory_clear").status == "ok"
    assert report.step("tor_process_stop").status == "ok"
    assert report.step("temp_data_dir_deletion").status == "failed"
    assert state.controller.commands == [f"DEL_ONION {SERVICE_ID}", "SIGNAL SHUTDOWN"]
    assert "TEARDOWN FAILURE" in stderr
    assert "DEL failed" in stderr
    assert "locked" in stderr


def test_teardown_skips_onion_removal_after_tor_exit(tmp_path: Path) -> None:
    data_dir = tmp_path / "tor-data"
    data_dir.mkdir()

    state = ApplianceState(
        data_dir=str(data_dir),
        tor_process=FakeTorProcess(poll_value=0),
        control_port=9051,
        controller=FakeController(),
        onion_service_id=SERVICE_ID,
        web_server=FakeWebServer(),
    )

    report = teardown(state)

    assert report.step("onion_service_removal").status == "skipped"
