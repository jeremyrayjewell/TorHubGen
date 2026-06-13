"""CLI parsing and runtime configuration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional


MAX_LIFETIME_SECONDS = 60 * 60


@dataclass(frozen=True)
class RunConfig:
    lifetime_seconds: int
    tor_cmd: Optional[str] = None


def build_run_parser(*, prog_name: str = "torhubgen") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog_name,
        description=(
            "Atomic process lifecycle wrapper: Tor + ephemeral onion + local web + "
            "mandatory lifetime."
        ),
    )
    parser.add_argument(
        "--lifetime-seconds",
        type=int,
        required=True,
        help="Mandatory runtime lifetime in seconds (required; no indefinite mode).",
    )
    parser.add_argument(
        "--tor-cmd",
        type=str,
        default=None,
        help="Optional explicit path to tor executable (no fallback).",
    )
    return parser


def build_selfcheck_parser(*, prog_name: str = "torhubgen") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=f"{prog_name} selfcheck",
        description="Run local lifecycle preflight checks without launching TorHubGen.",
    )
    parser.add_argument(
        "--tor-cmd",
        type=str,
        default=None,
        help="Optional explicit path to tor executable (no fallback).",
    )
    return parser


def parse_args(argv: list[str], *, prog_name: str = "torhubgen") -> argparse.Namespace:
    if argv and argv[0] == "selfcheck":
        parser = build_selfcheck_parser(prog_name=prog_name)
        args = parser.parse_args(argv[1:])
        args.command = "selfcheck"
        return args

    parser = build_run_parser(prog_name=prog_name)
    args = parser.parse_args(argv)
    args.command = "run"
    return args


def validate_lifetime_seconds(lifetime_seconds: int) -> int:
    lifetime_seconds = int(lifetime_seconds)
    if lifetime_seconds <= 0:
        raise ValueError("--lifetime-seconds must be > 0")
    if lifetime_seconds > MAX_LIFETIME_SECONDS:
        raise ValueError(
            f"--lifetime-seconds exceeds hard maximum ({MAX_LIFETIME_SECONDS}). "
            "Refusing to start."
        )
    return lifetime_seconds


def build_run_config(args: argparse.Namespace) -> RunConfig:
    return RunConfig(
        lifetime_seconds=validate_lifetime_seconds(args.lifetime_seconds),
        tor_cmd=args.tor_cmd,
    )
