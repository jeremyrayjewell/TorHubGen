"""Explicit teardown reporting for the appliance lifecycle."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field

from .output import info, loud, warn


@dataclass(frozen=True)
class TeardownStepResult:
    name: str
    status: str
    detail: str

    @property
    def failed(self) -> bool:
        return self.status == "failed"


@dataclass
class TeardownReport:
    steps: list[TeardownStepResult] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str) -> TeardownStepResult:
        step = TeardownStepResult(name=name, status=status, detail=detail)
        self.steps.append(step)
        if status == "failed":
            warn(f"teardown.{name}: {detail}")
        else:
            info(f"teardown.{name}: {status} - {detail}")
        return step

    def step(self, name: str) -> TeardownStepResult:
        for step in self.steps:
            if step.name == name:
                return step
        raise KeyError(name)

    @property
    def has_failures(self) -> bool:
        return any(step.failed for step in self.steps)

    @property
    def exit_code(self) -> int:
        return 2 if self.has_failures else 0


def teardown(state) -> TeardownReport:
    report = TeardownReport()
    tor_already_exited = (
        state.tor_process is not None and state.tor_process.poll() is not None
    )

    if state.controller is not None and state.onion_service_id is not None and not tor_already_exited:
        try:
            state.controller.msg(f"DEL_ONION {state.onion_service_id}")
        except Exception as exc:
            report.add(
                "onion_service_removal",
                "failed",
                f"Failed to DEL_ONION {state.onion_service_id}: {exc}",
            )
        else:
            report.add(
                "onion_service_removal",
                "ok",
                f"Removed onion service {state.onion_service_id}",
            )
    elif state.onion_service_id is None:
        report.add(
            "onion_service_removal",
            "skipped",
            "No onion service was created",
        )
    else:
        report.add(
            "onion_service_removal",
            "skipped",
            "Tor already exited; DEL_ONION skipped",
        )

    if state.web_server is not None:
        try:
            state.web_server.stop(timeout=5.0)
        except Exception as exc:
            report.add(
                "web_server_stop",
                "failed",
                f"Failed to stop local web server cleanly: {exc}",
            )
        else:
            report.add("web_server_stop", "ok", "Local web server stopped")

        try:
            state.web_server.clear()
        except Exception as exc:
            report.add(
                "message_memory_clear",
                "failed",
                f"Failed to clear in-memory message buffer: {exc}",
            )
        else:
            report.add("message_memory_clear", "ok", "In-memory message buffer cleared")
    else:
        report.add("web_server_stop", "skipped", "No local web server was started")
        report.add("message_memory_clear", "skipped", "No local message buffer was started")

    if state.tor_process is None:
        report.add("tor_process_stop", "skipped", "No Tor process was started")
    else:
        tor_failed = False
        tor_notes: list[str] = []

        if state.controller is not None:
            if tor_already_exited:
                tor_notes.append("Tor already exited before teardown")
                try:
                    state.controller.close()
                except Exception as exc:
                    tor_notes.append(f"Controller close after Tor exit raised: {exc}")
                else:
                    tor_notes.append("Controller closed after Tor exit")
            else:
                try:
                    state.controller.msg("SIGNAL SHUTDOWN")
                    tor_notes.append("Sent SIGNAL SHUTDOWN via ControlPort")
                except Exception as exc:
                    tor_failed = True
                    tor_notes.append(f"Failed to send Tor SHUTDOWN via ControlPort: {exc}")
                try:
                    state.controller.close()
                except Exception as exc:
                    tor_failed = True
                    tor_notes.append(f"Failed to close controller: {exc}")
                else:
                    tor_notes.append("Controller disconnected")

        try:
            state.tor_process.wait(timeout=10)
        except Exception as exc:
            tor_failed = True
            tor_notes.append(f"Tor did not exit cleanly: {exc}")
            try:
                state.tor_process.terminate()
                state.tor_process.wait(timeout=5)
            except Exception as exc2:
                tor_failed = True
                tor_notes.append(f"Failed to terminate Tor process: {exc2}")
                try:
                    state.tor_process.kill()
                except Exception as exc3:
                    tor_failed = True
                    tor_notes.append(f"Failed to kill Tor process: {exc3}")

        tor_notes.append(f"Tor exit code: {state.tor_process.returncode}")
        report.add(
            "tor_process_stop",
            "failed" if tor_failed else "ok",
            "; ".join(tor_notes),
        )

    try:
        shutil.rmtree(state.data_dir, ignore_errors=False)
    except Exception as exc:
        report.add(
            "temp_data_dir_deletion",
            "failed",
            f"Failed to delete temporary DataDirectory '{state.data_dir}': {exc}",
        )
    else:
        report.add(
            "temp_data_dir_deletion",
            "ok",
            f"Deleted temporary DataDirectory '{state.data_dir}'",
        )

    if report.has_failures:
        loud("TEARDOWN FAILURE: one or more cleanup steps failed")

    return report
