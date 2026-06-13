"""Local preflight checks for the narrow appliance lifecycle."""

from __future__ import annotations

import shutil
import socket
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .config import MAX_LIFETIME_SECONDS


REQUIRED_DOCS = (
    "readme.md",
    "docs/threat-model.md",
    "docs/development_process.md",
)


@dataclass(frozen=True)
class SelfcheckItem:
    name: str
    status: str
    detail: str

    @property
    def failed(self) -> bool:
        return self.status == "failed"


@dataclass
class SelfcheckReport:
    items: list[SelfcheckItem] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str) -> SelfcheckItem:
        item = SelfcheckItem(name=name, status=status, detail=detail)
        self.items.append(item)
        return item

    def item(self, name: str) -> SelfcheckItem:
        for item in self.items:
            if item.name == name:
                return item
        raise KeyError(name)

    @property
    def has_failures(self) -> bool:
        return any(item.failed for item in self.items)

    @property
    def exit_code(self) -> int:
        return 2 if self.has_failures else 0


def perform_selfcheck(
    *,
    project_root: Path,
    tor_cmd: Optional[str] = None,
    which: Callable[[str], Optional[str]] = shutil.which,
) -> SelfcheckReport:
    report = SelfcheckReport()

    tor_target = tor_cmd or "tor"
    tor_path = which(tor_target)
    if tor_path:
        report.add("tor_binary", "ok", f"Found Tor binary at '{tor_path}'")
    else:
        report.add(
            "tor_binary",
            "failed",
            f"Tor binary '{tor_target}' was not found on PATH",
        )

    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp(prefix="torhubgen_selfcheck_")
    except Exception as exc:
        report.add("temp_directory", "failed", f"Temporary directory creation failed: {exc}")
    else:
        report.add("temp_directory", "ok", f"Temporary directory creation worked: '{temp_dir}'")
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
    except Exception as exc:
        report.add("localhost_binding", "failed", f"Failed to bind localhost socket: {exc}")
    else:
        report.add("localhost_binding", "ok", "Loopback bind to 127.0.0.1 succeeded")
    finally:
        sock.close()

    if 0 < MAX_LIFETIME_SECONDS <= 60 * 60:
        report.add(
            "lifetime_cap",
            "ok",
            f"Maximum lifetime is set to {MAX_LIFETIME_SECONDS} seconds",
        )
    else:
        report.add(
            "lifetime_cap",
            "failed",
            f"Maximum lifetime is not sane: {MAX_LIFETIME_SECONDS}",
        )

    missing_docs = [rel_path for rel_path in REQUIRED_DOCS if not (project_root / rel_path).exists()]
    if missing_docs:
        report.add("required_docs", "failed", f"Missing required docs: {', '.join(missing_docs)}")
    else:
        report.add("required_docs", "ok", "All required lifecycle docs are present")

    report.add(
        "persistent_onion_keys",
        "ok",
        "No persistent onion key path is configurable in this build",
    )

    return report


def run_selfcheck(*, project_root: Path, tor_cmd: Optional[str] = None) -> int:
    report = perform_selfcheck(project_root=project_root, tor_cmd=tor_cmd)
    for item in report.items:
        print(f"[TorHubGen][selfcheck] {item.name}: {item.status} - {item.detail}")
    return report.exit_code
