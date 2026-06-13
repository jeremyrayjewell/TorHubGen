from __future__ import annotations

from pathlib import Path

import pytest

import torhubgen.tor_controller as tor_controller
from torhubgen.tor_controller import (
    add_ephemeral_v3_onion,
    authenticate_controller_safecookie,
    connect_controller,
)


SERVICE_ID = "a" * 56


class FakeResponse:
    def __init__(self, items, *, ok: bool = True, rendered: str | None = None) -> None:
        self._items = list(items)
        self._ok = ok
        self._rendered = rendered or f"250-ServiceID={SERVICE_ID}\n250 OK"

    def is_ok(self) -> bool:
        return self._ok

    def content(self):
        return list(self._items)

    def __str__(self) -> str:
        return self._rendered


class FakeController:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.commands: list[str] = []

    def msg(self, command: str):
        self.commands.append(command)
        return self.response


class FakeProtocolInfo:
    def __init__(self, auth_methods, *, cookie_path: str | None = "control_auth_cookie") -> None:
        self.auth_methods = tuple(auth_methods)
        self.cookie_path = cookie_path


class FakeAuthController:
    def __init__(self) -> None:
        self.closed = False
        self.post_authenticated = False

    def close(self) -> None:
        self.closed = True

    def _post_authentication(self) -> None:
        self.post_authenticated = True


class FakeStemConnectionModule:
    class AuthMethod:
        SAFECOOKIE = "Safecookie"
        COOKIE = "Cookie"

    def __init__(
        self,
        *,
        protocolinfo: FakeProtocolInfo | None = None,
        protocolinfo_error: Exception | None = None,
        auth_error: Exception | None = None,
    ) -> None:
        self.protocolinfo = protocolinfo
        self.protocolinfo_error = protocolinfo_error
        self.auth_error = auth_error
        self.authenticate_calls: list[tuple[object, str]] = []

    def get_protocolinfo(self, controller):
        if self.protocolinfo_error is not None:
            raise self.protocolinfo_error
        return self.protocolinfo

    def authenticate_safecookie(self, controller, cookie_path: str) -> None:
        self.authenticate_calls.append((controller, cookie_path))
        if self.auth_error is not None:
            raise self.auth_error


def test_add_ephemeral_v3_onion_uses_single_v3_discardpk_command() -> None:
    controller = FakeController(FakeResponse([("ServiceID", SERVICE_ID)]))
    service_id = add_ephemeral_v3_onion(controller=controller, target_port=12345)

    assert service_id == SERVICE_ID
    assert controller.commands == [
        "ADD_ONION NEW:ED25519-V3 Flags=DiscardPK Port=80,127.0.0.1:12345"
    ]


def test_only_one_onion_creation_command_path_exists_in_module() -> None:
    source = Path(tor_controller.__file__).read_text(encoding="utf-8")
    assert source.count("ADD_ONION NEW:ED25519-V3 Flags=DiscardPK Port=80,127.0.0.1:") == 1


def test_add_ephemeral_v3_onion_parses_string_responses() -> None:
    response = FakeResponse(
        ["250-ServiceID=" + SERVICE_ID + "\n250 OK"],
        rendered="250-ServiceID=" + SERVICE_ID + "\n250 OK",
    )
    controller = FakeController(response)

    assert add_ephemeral_v3_onion(controller=controller, target_port=80) == SERVICE_ID


def test_safecookie_auth_is_accepted_when_available() -> None:
    controller = FakeAuthController()
    stem_connection = FakeStemConnectionModule(
        protocolinfo=FakeProtocolInfo(
            [
                FakeStemConnectionModule.AuthMethod.SAFECOOKIE,
                FakeStemConnectionModule.AuthMethod.COOKIE,
            ],
            cookie_path="safe_cookie_path",
        )
    )

    authenticate_controller_safecookie(controller, stem_connection)

    assert stem_connection.authenticate_calls == [(controller, "safe_cookie_path")]
    assert controller.post_authenticated is True


def test_cookie_only_authentication_is_rejected() -> None:
    controller = FakeAuthController()
    stem_connection = FakeStemConnectionModule(
        protocolinfo=FakeProtocolInfo([FakeStemConnectionModule.AuthMethod.COOKIE])
    )

    with pytest.raises(RuntimeError, match="requires SAFECOOKIE"):
        authenticate_controller_safecookie(controller, stem_connection)

    assert stem_connection.authenticate_calls == []
    assert controller.post_authenticated is False


def test_unsupported_control_auth_fails_closed() -> None:
    controller = FakeAuthController()
    stem_connection = FakeStemConnectionModule(
        protocolinfo_error=RuntimeError("protocolinfo failed")
    )

    with pytest.raises(RuntimeError, match="requires SAFECOOKIE authentication"):
        authenticate_controller_safecookie(controller, stem_connection)

    assert stem_connection.authenticate_calls == []
    assert controller.post_authenticated is False


def test_connect_controller_closes_socket_on_safecookie_failure(monkeypatch) -> None:
    created = {}

    class FakeControllerClass(FakeAuthController):
        @classmethod
        def from_port(cls, *, address: str, port: int):
            controller = cls()
            created["controller"] = controller
            created["address"] = address
            created["port"] = port
            return controller

    stem_connection = FakeStemConnectionModule(
        protocolinfo=FakeProtocolInfo(
            [FakeStemConnectionModule.AuthMethod.SAFECOOKIE],
            cookie_path="safe_cookie_path",
        ),
        auth_error=RuntimeError("challenge failed"),
    )

    monkeypatch.setattr(
        tor_controller,
        "load_stem_dependencies",
        lambda: (FakeControllerClass, object()),
    )
    monkeypatch.setattr(
        tor_controller,
        "load_stem_connection",
        lambda: stem_connection,
    )

    with pytest.raises(RuntimeError, match="SAFECOOKIE authentication failed"):
        connect_controller(9051)

    assert created["address"] == "127.0.0.1"
    assert created["port"] == 9051
    assert created["controller"].closed is True
