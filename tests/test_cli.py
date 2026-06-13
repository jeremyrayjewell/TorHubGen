from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from torhubgen.config import MAX_LIFETIME_SECONDS, build_run_config, parse_args


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_startup_requires_explicit_lifetime() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_lifetime_above_maximum_is_rejected() -> None:
    args = parse_args(["--lifetime-seconds", str(MAX_LIFETIME_SECONDS + 1)])
    with pytest.raises(ValueError, match="exceeds hard maximum"):
        build_run_config(args)


def test_lifetime_at_hard_maximum_is_accepted() -> None:
    args = parse_args(["--lifetime-seconds", str(MAX_LIFETIME_SECONDS)])
    config = build_run_config(args)
    assert config.lifetime_seconds == MAX_LIFETIME_SECONDS


def test_selfcheck_subcommand_does_not_require_lifetime() -> None:
    args = parse_args(["selfcheck"])
    assert args.command == "selfcheck"


def test_atomic_wrapper_help_preserves_legacy_program_name() -> None:
    result = subprocess.run(
        [sys.executable, "atomic_wrapper.py", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage: atomic_wrapper.py" in result.stdout
