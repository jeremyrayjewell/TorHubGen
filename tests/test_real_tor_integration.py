from __future__ import annotations

import importlib.util
import os
import shutil
import tempfile

import pytest

from torhubgen.tor_controller import add_ephemeral_v3_onion, connect_controller, launch_private_tor


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.getenv("TORHUBGEN_RUN_TOR_INTEGRATION") != "1",
    reason="Set TORHUBGEN_RUN_TOR_INTEGRATION=1 to enable real-Tor integration tests.",
)
def test_real_tor_launch_and_ephemeral_onion_creation() -> None:
    if shutil.which("tor") is None:
        pytest.skip("tor binary is not available")
    if importlib.util.find_spec("stem") is None:
        pytest.skip("stem is not installed")

    data_dir = tempfile.mkdtemp(prefix="torhubgen_integration_")
    tor_process = None
    controller = None
    try:
        tor_process, control_port = launch_private_tor(tor_cmd=None, data_dir=data_dir)
        controller = connect_controller(control_port)
        service_id = add_ephemeral_v3_onion(controller=controller, target_port=1)
        assert len(service_id) == 56
    finally:
        if controller is not None:
            try:
                controller.close()
            except Exception:
                pass
        if tor_process is not None:
            try:
                tor_process.terminate()
                tor_process.wait(timeout=5)
            except Exception:
                pass
        shutil.rmtree(data_dir, ignore_errors=True)
