"""Appliance lifecycle orchestration."""

from __future__ import annotations

import signal
import subprocess
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Optional

from .board_server import DEFAULT_BIND_HOST, WebServerHandle, launch_local_web_server
from .config import RunConfig
from .errors import ShutdownRequested
from .output import info, loud, warn
from .teardown import teardown
from .tor_controller import (
    add_ephemeral_v3_onion,
    connect_controller,
    launch_private_tor,
    pick_free_port,
)


@dataclass
class ApplianceState:
    data_dir: str
    tor_process: Optional[subprocess.Popen]
    control_port: int
    controller: Optional[object]
    onion_service_id: Optional[str]
    web_server: Optional[WebServerHandle]


class ShutdownSignal:
    def __init__(self) -> None:
        self._event = threading.Event()
        self.reason: Optional[str] = None

    def request(self, reason: str) -> None:
        self.reason = reason
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float) -> bool:
        return self._event.wait(timeout)


def format_returncode(rc: Optional[int]) -> str:
    if rc is None:
        return "<running>"
    if rc == 0:
        return "0 (clean exit)"
    return f"{rc} (abnormal exit)"


def make_signal_handler(shutdown: ShutdownSignal, signal_module=signal):
    def handle_signal(signum: int, _frame) -> None:
        signals_enum = getattr(signal_module, "Signals", None)
        if signals_enum is not None:
            try:
                label = signals_enum(signum).name
            except Exception:
                label = str(signum)
        else:
            label = str(signum)
        shutdown.request(f"signal {label}")

    return handle_signal


def install_signal_handlers(shutdown: ShutdownSignal, signal_module=signal):
    handler = make_signal_handler(shutdown, signal_module=signal_module)
    for sig in (
        getattr(signal_module, "SIGINT", None),
        getattr(signal_module, "SIGTERM", None),
        getattr(signal_module, "SIGBREAK", None),
    ):
        if sig is not None:
            try:
                signal_module.signal(sig, handler)
            except Exception:
                pass
    return handler


def enforce_lifetime(
    *,
    lifetime_seconds: int,
    shutdown: ShutdownSignal,
    tor_process: subprocess.Popen,
    web_server: WebServerHandle,
    controller,
) -> None:
    start = time.monotonic()
    last_controller_heartbeat = start
    controller_disconnected = False
    controller_disconnect_logged = False

    if controller is not None:
        info("Control connection will remain open until teardown")

    while True:
        if shutdown.is_set():
            raise ShutdownRequested(shutdown.reason or "shutdown requested")

        if tor_process.poll() is not None:
            rc = tor_process.returncode
            if controller_disconnected and not controller_disconnect_logged:
                warn(
                    "Control connection was lost before Tor exit "
                    "(possible ownership-triggered termination)"
                )
                controller_disconnect_logged = True
            warn(f"Tor exited unexpectedly with code: {format_returncode(rc)}")
            raise RuntimeError(f"Tor process exited unexpectedly (returncode={rc})")

        if controller is not None and not controller_disconnected:
            if (time.monotonic() - last_controller_heartbeat) >= 2.0:
                last_controller_heartbeat = time.monotonic()
                try:
                    if not controller.is_alive():
                        raise RuntimeError("controller.is_alive() returned False")
                    controller.get_info("version")
                except Exception as exc:
                    controller_disconnected = True
                    controller_disconnect_logged = True
                    warn(f"Control connection lost while Tor is still running: {exc}")

        if not web_server.is_alive():
            raise RuntimeError("Local web server stopped unexpectedly")

        elapsed = time.monotonic() - start
        if elapsed >= lifetime_seconds:
            raise ShutdownRequested("lifetime expired")

        time.sleep(0.25)


def run_appliance(config: RunConfig) -> int:
    shutdown = ShutdownSignal()
    install_signal_handlers(shutdown)

    data_dir = tempfile.mkdtemp(prefix="torhubgen_phase1_")
    state = ApplianceState(
        data_dir=data_dir,
        tor_process=None,
        control_port=0,
        controller=None,
        onion_service_id=None,
        web_server=None,
    )

    exit_code = 0
    try:
        info(f"Starting appliance (lifetime={config.lifetime_seconds}s)")
        info(f"Temporary DataDirectory: {data_dir}")

        tor_process, control_port = launch_private_tor(
            tor_cmd=config.tor_cmd,
            data_dir=data_dir,
        )
        state.tor_process = tor_process
        state.control_port = control_port

        web_port = pick_free_port(DEFAULT_BIND_HOST)
        state.web_server = launch_local_web_server(bind_host=DEFAULT_BIND_HOST, port=web_port)
        info(f"Local web server listening on http://127.0.0.1:{web_port}")

        try:
            state.controller = connect_controller(control_port)
        except Exception as exc:
            raise RuntimeError(f"Failed to connect to Tor ControlPort on {control_port}: {exc}") from exc

        try:
            state.onion_service_id = add_ephemeral_v3_onion(
                controller=state.controller,
                target_port=web_port,
            )
        except Exception as exc:
            raise RuntimeError(f"Ephemeral onion creation failed (fail-closed): {exc}") from exc

        onion_address = f"{state.onion_service_id}.onion"
        info(f"Ephemeral onion service created: {onion_address}")
        info("No onion keys are written to disk (ephemeral v3 onion with discarded private key)")

        enforce_lifetime(
            lifetime_seconds=config.lifetime_seconds,
            shutdown=shutdown,
            tor_process=state.tor_process,
            web_server=state.web_server,
            controller=state.controller,
        )
        raise AssertionError("unreachable")

    except ShutdownRequested as exc:
        info(f"Shutdown requested: {exc}")
        exit_code = 0
    except Exception as exc:
        loud(f"{type(exc).__name__}: {exc}")
        warn(traceback.format_exc().rstrip())
        exit_code = 2
    finally:
        try:
            teardown_report = teardown(state)
            exit_code = max(exit_code, teardown_report.exit_code)
        except Exception as exc:
            loud(f"TEARDOWN FAILURE: unhandled exception during cleanup: {exc}")
            exit_code = max(exit_code, 2)

    return exit_code
