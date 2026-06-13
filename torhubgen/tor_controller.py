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


def load_stem_connection():
    try:
        import stem.connection as stem_connection
    except Exception as exc:  # pragma: no cover
        raise StemDependencyMissing(
            "stem is required to launch TorHubGen. Install with: pip install stem\n"
            f"Import error: {exc}"
        ) from exc
    return stem_connection


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


def authenticate_controller_safecookie(controller, stem_connection) -> None:
    try:
        protocolinfo = stem_connection.get_protocolinfo(controller)
    except Exception as exc:
        raise RuntimeError(
            "Failed to query Tor ControlPort authentication methods. "
            "TorHubGen requires SAFECOOKIE authentication. "
            f"Error: {exc}"
        ) from exc

    auth_methods = tuple(protocolinfo.auth_methods)
    if stem_connection.AuthMethod.SAFECOOKIE not in auth_methods:
        offered = ", ".join(str(method) for method in auth_methods) if auth_methods else "none"
        raise RuntimeError(
            "Tor ControlPort did not advertise SAFECOOKIE authentication "
            f"(offered: {offered}). TorHubGen requires SAFECOOKIE and refuses "
            "to fall back to COOKIE authentication."
        )

    if not protocolinfo.cookie_path:
        raise RuntimeError(
            "Tor ControlPort advertised SAFECOOKIE but did not provide a cookie path. "
            "TorHubGen requires SAFECOOKIE and refuses to continue."
        )

    try:
        stem_connection.authenticate_safecookie(controller, protocolinfo.cookie_path)
    except Exception as exc:
        raise RuntimeError(
            "SAFECOOKIE authentication failed. TorHubGen requires SAFECOOKIE "
            "and refuses to fall back to COOKIE authentication. "
            f"Error: {exc}"
        ) from exc

    post_authentication = getattr(controller, "_post_authentication", None)
    if callable(post_authentication):
        post_authentication()


def connect_controller(control_port: int):
    Controller, _ = load_stem_dependencies()
    stem_connection = load_stem_connection()
    controller = Controller.from_port(address="127.0.0.1", port=control_port)
    try:
        authenticate_controller_safecookie(controller, stem_connection)
    except Exception:
        try:
            controller.close()
        except Exception:
            pass
        raise
    info(
        "Connected to Tor ControlPort on 127.0.0.1:"
        f"{control_port} using explicit SAFECOOKIE authentication"
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
