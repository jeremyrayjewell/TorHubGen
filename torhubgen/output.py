"""Small stderr logging helpers used across the appliance."""

from __future__ import annotations

import sys


def loud(msg: str) -> None:
    print(f"[TorHubGen][FATAL] {msg}", file=sys.stderr, flush=True)


def warn(msg: str) -> None:
    print(f"[TorHubGen][WARNING] {msg}", file=sys.stderr, flush=True)


def info(msg: str) -> None:
    print(f"[TorHubGen] {msg}", file=sys.stderr, flush=True)
