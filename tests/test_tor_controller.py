from __future__ import annotations

from pathlib import Path

from torhubgen.tor_controller import add_ephemeral_v3_onion
import torhubgen.tor_controller as tor_controller


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
