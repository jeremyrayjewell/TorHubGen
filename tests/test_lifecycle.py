from __future__ import annotations

import signal

import pytest

from torhubgen.errors import ShutdownRequested
from torhubgen.lifecycle import (
    ShutdownSignal,
    enforce_lifetime,
    install_signal_handlers,
)


class FakeSignalModule:
    SIGINT = signal.SIGINT
    SIGTERM = signal.SIGTERM
    SIGBREAK = None
    Signals = signal.Signals

    def __init__(self) -> None:
        self.handlers = {}

    def signal(self, signum, handler) -> None:
        self.handlers[signum] = handler


class FakeTorProcess:
    def __init__(self, returncode=None) -> None:
        self.returncode = returncode

    def poll(self):
        return self.returncode


class FakeWebServer:
    def __init__(self, *, alive: bool = True) -> None:
        self.alive = alive

    def is_alive(self) -> bool:
        return self.alive


def test_signal_handlers_request_shutdown_for_sigint_and_sigterm() -> None:
    fake_signal_module = FakeSignalModule()
    shutdown = ShutdownSignal()
    install_signal_handlers(shutdown, signal_module=fake_signal_module)

    fake_signal_module.handlers[signal.SIGINT](signal.SIGINT, None)
    assert shutdown.reason == "signal SIGINT"

    shutdown = ShutdownSignal()
    fake_signal_module = FakeSignalModule()
    install_signal_handlers(shutdown, signal_module=fake_signal_module)
    fake_signal_module.handlers[signal.SIGTERM](signal.SIGTERM, None)
    assert shutdown.reason == "signal SIGTERM"


def test_enforce_lifetime_rejects_unexpected_tor_exit() -> None:
    shutdown = ShutdownSignal()
    tor_process = FakeTorProcess(returncode=17)
    web_server = FakeWebServer(alive=True)

    with pytest.raises(RuntimeError, match="Tor process exited unexpectedly"):
        enforce_lifetime(
            lifetime_seconds=10,
            shutdown=shutdown,
            tor_process=tor_process,
            web_server=web_server,
            controller=None,
        )


def test_enforce_lifetime_expires_cleanly() -> None:
    shutdown = ShutdownSignal()
    tor_process = FakeTorProcess(returncode=None)
    web_server = FakeWebServer(alive=True)

    with pytest.raises(ShutdownRequested, match="lifetime expired"):
        enforce_lifetime(
            lifetime_seconds=0,
            shutdown=shutdown,
            tor_process=tor_process,
            web_server=web_server,
            controller=None,
        )
