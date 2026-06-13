"""Package CLI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

from .config import build_run_config, parse_args
from .lifecycle import run_appliance
from .output import loud
from .selfcheck import run_selfcheck


def main(
    argv: list[str] | None = None,
    *,
    prog_name: str = "torhubgen",
    project_root: Path | None = None,
) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent

    args = parse_args(list(argv), prog_name=prog_name)

    if args.command == "selfcheck":
        return run_selfcheck(project_root=project_root, tor_cmd=args.tor_cmd)

    try:
        config = build_run_config(args)
    except ValueError as exc:
        loud(str(exc))
        return 2

    return run_appliance(config)


if __name__ == "__main__":
    raise SystemExit(main())
