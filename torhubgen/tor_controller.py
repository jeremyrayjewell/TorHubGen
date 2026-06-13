"""Tor process and control-plane helpers."""

from __future__ import annotations

import re
import socket
import subprocess
from typing import Optional

from .errors import StemDependencyMissing
from .output import info


def load_stem_dependencies():
    try:
        from stem.control import Controller
        from stem.process import launch_tor_with_config
    except Exception as exc:  # pragma: no cover
        raise StemDependencyMissing(
            "stem is required to launch TorHubGen. Install with: pip install stem\n"
            f"Import error: {exc}"
        ) from exc
    return Controller, launch_tor_with_config


def pick_free_port(bind_host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((bind_host, 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def launch_private_tor(
    *,
    tor_cmd: Optional[str],
    data_dir: str,
) -> tuple[subprocess.Popen, int]:
    _, launch_tor_with_config = load_stem_dependencies()
    control_port = pick_free_port("127.0.0.1")
    config = {
        "DataDirectory": data_dir,
        "ControlListenAddress": "127.0.0.1",
        "ControlPort": str(control_port),
        "CookieAuthentication": "1",
        "SocksPort": "0",
    }

    try:
        if tor_cmd is None:
            proc = launch_tor_with_config(
                config=config,
                take_ownership=True,
                init_msg_handler=lambda line: info(f"tor: {line}"),
            )
        else:
            proc = launch_tor_with_config(
                config=config,
                tor_cmd=tor_cmd,
                take_ownership=True,
                init_msg_handler=lambda line: info(f"tor: {line}"),
            )
    except OSError as exc:
        raise RuntimeError(
            "Failed to launch Tor. Ensure 'tor' is installed and on PATH, or pass --tor-cmd. "
            f"Error: {exc}"
        ) from exc

    return proc, control_port


def connect_controller(control_port: int):
    Controller, _ = load_stem_dependencies()
    controller = Controller.from_port(address="127.0.0.1", port=control_port)
    # This currently relies on Stem's authenticate() abstraction rather than a
    # hand-rolled SAFECOOKIE-only flow. In Stem 1.8.x that negotiates methods
    # from PROTOCOLINFO and prefers SAFECOOKIE before COOKIE when both are
    # offered, but TorHubGen does not yet assert SAFECOOKIE-only behavior itself.
    # TODO: Once Stem usage is part of the validated environment, evaluate
    # whether TorHubGen should require an explicit SAFECOOKIE-only flow here.
    controller.authenticate()
    info(
        "Connected to Tor ControlPort on 127.0.0.1:"
        f"{control_port} using Stem authenticate()"
    )
    return controller


def add_ephemeral_v3_onion(*, controller, target_port: int) -> str:
    command = f"ADD_ONION NEW:ED25519-V3 Flags=DiscardPK Port=80,127.0.0.1:{target_port}"
    try:
        response = controller.msg(command)
    except Exception as exc:
        raise RuntimeError(f"ADD_ONION failed: {exc}") from exc

    if not response.is_ok():
        raise RuntimeError(f"ADD_ONION failed: {response}")

    service_id: Optional[str] = None

    def normalize_service_id(candidate: str) -> Optional[str]:
        match = re.search(r"[a-z2-7]{56}", candidate.lower())
        return match.group(0) if match else None

    def extract_service_id(text: str) -> Optional[str]:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("250-"):
                line = line[4:]
            elif line.startswith("250 "):
                line = line[4:]
            if line.startswith("ServiceID="):
                remainder = line.split("=", 1)[1].strip()
                candidate = remainder.split()[0] if remainder else ""
                return normalize_service_id(candidate) if candidate else None
            marker = "ServiceID="
            idx = line.find(marker)
            if idx != -1:
                remainder = line[idx + len(marker) :].strip()
                candidate = remainder.split()[0] if remainder else ""
                return normalize_service_id(candidate) if candidate else None
        return None

    for item in response.content():
        if isinstance(item, tuple) and len(item) == 2:
            key, value = item
            if key == "ServiceID":
                service_id = normalize_service_id(str(value).strip())
                if service_id:
                    break
        else:
            item_text = item if isinstance(item, str) else str(item)
            service_id = extract_service_id(item_text)
        if service_id:
            break

    if not service_id:
        service_id = extract_service_id(str(response))

    if not service_id:
        raise RuntimeError(f"ADD_ONION did not return a ServiceID: {response}")

    return service_id
