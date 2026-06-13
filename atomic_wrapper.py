"""Compatibility entrypoint for the TorHubGen appliance."""

from pathlib import Path

from torhubgen.__main__ import main as package_main


if __name__ == "__main__":
    raise SystemExit(package_main(prog_name=Path(__file__).name))
