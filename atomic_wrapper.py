
import argparse
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Optional


try:
	from stem import SocketError
	from stem.control import Controller
	from stem.process import launch_tor_with_config
except Exception as exc:  # pragma: no cover
	raise SystemExit(
		"stem is required for Phase 1. Install with: pip install stem\n"
		f"Import error: {exc}"
	)


# Phase 1 requirement: lifetime MUST be explicit and capped (no indefinite mode).
MAX_LIFETIME_SECONDS = 60 * 60  # hard safety cap: 1 hour


def _loud(msg: str) -> None:
	print(f"[TorHubGen][FATAL] {msg}", file=sys.stderr, flush=True)


def _warn(msg: str) -> None:
	print(f"[TorHubGen][WARNING] {msg}", file=sys.stderr, flush=True)


def _info(msg: str) -> None:
	print(f"[TorHubGen] {msg}", file=sys.stderr, flush=True)


def _pick_free_port(bind_host: str = "127.0.0.1") -> int:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.bind((bind_host, 0))
		sock.listen(1)
		return int(sock.getsockname()[1])


@dataclass
class ApplianceState:
	data_dir: str
	tor_process: Optional[subprocess.Popen]
	control_port: int
	controller: Optional[Controller]
	onion_service_id: Optional[str]
	web_process: Optional[subprocess.Popen]


class ShutdownRequested(Exception):
	pass


class ShutdownSignal:
	def __init__(self) -> None:
		self._event = threading.Event()
		self.reason: Optional[str] = None

	def request(self, reason: str) -> None:
		self.reason = reason
		self._event.set()

	def is_set(self) -> bool:
		return self._event.is_set()

	def wait(self, timeout: float) -> bool:
		return self._event.wait(timeout)


# --- Tor launch (private instance with isolated, temporary DataDirectory) ---
def launch_private_tor(*, tor_cmd: Optional[str], data_dir: str) -> tuple[subprocess.Popen, int]:
	control_port = _pick_free_port("127.0.0.1")

	# Threat model alignment:
	# - Tor state is isolated to a temporary DataDirectory.
	# - ControlPort binds to localhost only.
	# - SocksPort is disabled because Phase 1 is control-plane only.
	config = {
		"DataDirectory": data_dir,
		"ControlListenAddress": "127.0.0.1",
		"ControlPort": str(control_port),
		"CookieAuthentication": "1",
		"SocksPort": "0",
	}

	try:
		# stem expects a string for tor_cmd; do not pass None.
		if tor_cmd is None:
			proc = launch_tor_with_config(
				config=config,
				take_ownership=True,
				init_msg_handler=lambda line: _info(f"tor: {line}"),
			)
		else:
			proc = launch_tor_with_config(
				config=config,
				tor_cmd=tor_cmd,
				take_ownership=True,
				init_msg_handler=lambda line: _info(f"tor: {line}"),
			)
	except OSError as exc:
		raise RuntimeError(
			"Failed to launch Tor. Ensure 'tor' is installed and on PATH, or pass --tor-cmd. "
			f"Error: {exc}"
		)

	return proc, control_port


def connect_controller(control_port: int) -> Controller:
	controller = Controller.from_port(address="127.0.0.1", port=control_port)
	controller.authenticate()  # cookie auth
	return controller


# --- Ephemeral onion creation (V3 only, ephemeral only via ADD_ONION) ---
def add_ephemeral_v3_onion(*, controller: Controller, target_port: int) -> str:
	# Requirement: onion private key MUST NOT be written to disk.
	# We request a new in-memory key and discard returning private key material.
	# Port mapping is explicit to 127.0.0.1 only.
	command = f"ADD_ONION NEW:ED25519-V3 Flags=DiscardPK Port=80,127.0.0.1:{target_port}"
	try:
		response = controller.msg(command)
	except Exception as exc:
		raise RuntimeError(f"ADD_ONION failed: {exc}")

	if not response.is_ok():
		raise RuntimeError(f"ADD_ONION failed: {response}")

	service_id: Optional[str] = None

	def _normalize_service_id(candidate: str) -> Optional[str]:
		match = re.search(r"[a-z2-7]{56}", candidate.lower())
		return match.group(0) if match else None

	def _extract_service_id(text: str) -> Optional[str]:
		for raw_line in text.splitlines():
			line = raw_line.strip()
			if not line:
				continue
			# Some Stem variants may include the status code/prefix.
			if line.startswith("250-"):
				line = line[4:]
			elif line.startswith("250 "):
				line = line[4:]
			if line.startswith("ServiceID="):
				remainder = line.split("=", 1)[1].strip()
				# Defend against combined lines like: "ServiceID=abc... OK"
				candidate = remainder.split()[0] if remainder else ""
				return _normalize_service_id(candidate) if candidate else None
			# As a last resort, look for an embedded token.
			marker = "ServiceID="
			idx = line.find(marker)
			if idx != -1:
				remainder = line[idx + len(marker) :].strip()
				candidate = remainder.split()[0] if remainder else ""
				return _normalize_service_id(candidate) if candidate else None
		return None

	for item in response.content():
		# Case 1: structured tuples
		if isinstance(item, tuple) and len(item) == 2:
			key, value = item
			if key == "ServiceID":
				service_id = _normalize_service_id(str(value).strip())
				if service_id:
					break

		# Case 2 or 3: string responses (possibly multiline)
		else:
			item_text = item if isinstance(item, str) else str(item)
			service_id = _extract_service_id(item_text)

		if service_id:
			break

	# Some Stem versions have response.content() that doesn't surface the key/value cleanly,
	# but str(response) does. Parse it as a final fallback.
	if not service_id:
		service_id = _extract_service_id(str(response))

	if not service_id:
		raise RuntimeError(f"ADD_ONION did not return a ServiceID: {response}")

	return service_id


# --- Local web process (binds to 127.0.0.1 only) ---
def launch_local_web_process(*, bind_host: str, port: int) -> subprocess.Popen:
	if bind_host != "127.0.0.1":
		raise ValueError("Phase 1 requires binding to 127.0.0.1 only")

	# This is intentionally minimal (no UI, no files, no persistence). It exists only to
	# prove the atomic process lifecycle: tor + onion + local web share one lifetime.
	code = (
		"import http.server, socketserver, sys\n"
		"host=sys.argv[1]; port=int(sys.argv[2])\n"
		"class H(http.server.BaseHTTPRequestHandler):\n"
		"  def do_GET(self):\n"
		"    body=b'OK'\n"
		"    self.send_response(200)\n"
		"    self.send_header('Content-Type','text/plain')\n"
		"    self.send_header('Content-Length', str(len(body)))\n"
		"    self.end_headers()\n"
		"    self.wfile.write(body)\n"
		"  def log_message(self, fmt, *args):\n"
		"    pass\n"
		"with socketserver.TCPServer((host, port), H) as httpd:\n"
		"  httpd.serve_forever()\n"
	)

	return subprocess.Popen(
		[sys.executable, "-c", code, bind_host, str(port)],
		stdin=subprocess.DEVNULL,
		stdout=subprocess.DEVNULL,
		stderr=subprocess.DEVNULL,
	)


# --- Lifetime enforcement + atomic shutdown monitoring ---
def enforce_lifetime(
	*,
	lifetime_seconds: int,
	shutdown: ShutdownSignal,
	tor_process: subprocess.Popen,
	web_process: subprocess.Popen,
) -> None:
	start = time.monotonic()

	while True:
		if shutdown.is_set():
			raise ShutdownRequested(shutdown.reason or "shutdown requested")

		# Requirement: unexpected Tor exit MUST terminate immediately.
		if tor_process.poll() is not None:
			raise RuntimeError("Tor process exited unexpectedly")

		if web_process.poll() is not None:
			raise RuntimeError("Local web process exited unexpectedly")

		elapsed = time.monotonic() - start
		if elapsed >= lifetime_seconds:
			raise ShutdownRequested("lifetime expired")

		time.sleep(0.25)


# --- Teardown (loud, best-effort, never silent) ---
def teardown(state: ApplianceState) -> int:
	# Return code indicates whether teardown was fully successful (0) or had failures (nonzero).
	teardown_failed = False

	tor_already_exited = (
		state.tor_process is not None and state.tor_process.poll() is not None
	)
	if tor_already_exited:
		_info("Tor already exited; control-channel cleanup skipped.")

	# Best effort: remove onion before stopping Tor (not required for ephemerality, but clearer).
	# If Tor already exited, the ControlPort is expected to be unavailable; skip control-channel cleanup.
	if (not tor_already_exited) and state.controller is not None and state.onion_service_id is not None:
		try:
			state.controller.msg(f"DEL_ONION {state.onion_service_id}")
		except Exception as exc:
			teardown_failed = True
			_warn(f"Failed to DEL_ONION {state.onion_service_id}: {exc}")

	# Stop web process.
	if state.web_process is not None:
		try:
			state.web_process.terminate()
			state.web_process.wait(timeout=5)
		except Exception as exc:
			teardown_failed = True
			_warn(f"Failed to stop local web process cleanly: {exc}")
			try:
				state.web_process.kill()
			except Exception as exc2:
				teardown_failed = True
				_warn(f"Failed to kill local web process: {exc2}")

	# Stop Tor via ControlPort if possible; otherwise terminate the process.
	if state.controller is not None:
		if tor_already_exited:
			# Tor already exited; control connection may already be broken. Closing is best-effort and
			# must not be classified as a teardown failure in this expected scenario.
			try:
				state.controller.close()
			except Exception as exc:
				_warn(f"Failed to close controller after Tor exit: {exc}")
		else:
			try:
				state.controller.msg("SIGNAL SHUTDOWN")
			except Exception as exc:
				teardown_failed = True
				_warn(f"Failed to send Tor SHUTDOWN via ControlPort: {exc}")
			finally:
				try:
					state.controller.close()
				except Exception as exc:
					teardown_failed = True
					_warn(f"Failed to close controller: {exc}")

	if state.tor_process is not None:
		try:
			state.tor_process.wait(timeout=10)
		except Exception as exc:
			teardown_failed = True
			_warn(f"Tor did not exit cleanly: {exc}")
			try:
				state.tor_process.terminate()
				state.tor_process.wait(timeout=5)
			except Exception as exc2:
				teardown_failed = True
				_warn(f"Failed to terminate Tor process: {exc2}")
				try:
					state.tor_process.kill()
				except Exception as exc3:
					teardown_failed = True
					_warn(f"Failed to kill Tor process: {exc3}")

	# Remove temporary DataDirectory.
	try:
		shutil.rmtree(state.data_dir, ignore_errors=False)
	except Exception as exc:
		teardown_failed = True
		_warn(f"Failed to delete temporary DataDirectory '{state.data_dir}': {exc}")

	if teardown_failed:
		_loud("TEARDOWN FAILURE: one or more cleanup steps failed")
		return 2
	return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		prog="TorHubGen Phase 1",
		description="Atomic process lifecycle wrapper: Tor + ephemeral onion + local web + mandatory lifetime.",
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
	return parser.parse_args(argv)


def main(argv: list[str]) -> int:
	args = parse_args(argv)

	lifetime_seconds = int(args.lifetime_seconds)
	if lifetime_seconds <= 0:
		_loud("--lifetime-seconds must be > 0")
		return 2
	if lifetime_seconds > MAX_LIFETIME_SECONDS:
		_loud(
			f"--lifetime-seconds exceeds hard maximum ({MAX_LIFETIME_SECONDS}). Refusing to start."
		)
		return 2

	shutdown = ShutdownSignal()

	def _handle_signal(signum: int, _frame) -> None:
		name = getattr(signal, "Signals", None)
		if name is not None:
			try:
				label = signal.Signals(signum).name
			except Exception:
				label = str(signum)
		else:
			label = str(signum)
		shutdown.request(f"signal {label}")

	# Phase 1 requirement: teardown must occur via try/finally and signal handlers.
	for sig in [getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None), getattr(signal, "SIGBREAK", None)]:
		if sig is not None:
			try:
				signal.signal(sig, _handle_signal)
			except Exception:
				pass

	data_dir = tempfile.mkdtemp(prefix="torhubgen_phase1_")
	state = ApplianceState(
		data_dir=data_dir,
		tor_process=None,
		control_port=0,
		controller=None,
		onion_service_id=None,
		web_process=None,
	)

	exit_code = 0
	try:
		_info(f"Starting Phase 1 appliance (lifetime={lifetime_seconds}s)")
		_info(f"Temporary DataDirectory: {data_dir}")

		# 1) Launch Tor.
		tor_process, control_port = launch_private_tor(tor_cmd=args.tor_cmd, data_dir=data_dir)
		state.tor_process = tor_process
		state.control_port = control_port

		# 2) Start local web process (127.0.0.1 only).
		web_port = _pick_free_port("127.0.0.1")
		state.web_process = launch_local_web_process(bind_host="127.0.0.1", port=web_port)

		# 3) Connect to Tor ControlPort and create V3 ephemeral onion service.
		try:
			state.controller = connect_controller(control_port)
		except SocketError as exc:
			raise RuntimeError(f"Failed to connect to Tor ControlPort on {control_port}: {exc}")

		try:
			state.onion_service_id = add_ephemeral_v3_onion(controller=state.controller, target_port=web_port)
		except Exception as exc:
			# Fail closed: ephemeral onion creation failure is fatal.
			raise RuntimeError(f"Ephemeral onion creation failed (fail-closed): {exc}")

		onion_address = f"{state.onion_service_id}.onion"
		_info(f"Ephemeral onion service created: {onion_address}")
		_info("No onion keys are written to disk (ephemeral ADD_ONION NEW:ED25519-V3)")

		# 4) Enforce lifetime and atomicity.
		enforce_lifetime(
			lifetime_seconds=lifetime_seconds,
			shutdown=shutdown,
			tor_process=state.tor_process,
			web_process=state.web_process,
		)

		# enforce_lifetime always raises on expiry/signal/error.
		raise AssertionError("unreachable")

	except ShutdownRequested as exc:
		_info(f"Shutdown requested: {exc}")
		exit_code = 0
	except Exception as exc:
		_loud(f"{type(exc).__name__}: {exc}")
		_warn(traceback.format_exc().rstrip())
		exit_code = 2
	finally:
		# Teardown is mandatory and must be loud on failure.
		try:
			teardown_code = teardown(state)
			exit_code = max(exit_code, teardown_code)
		except Exception as exc:
			_loud(f"TEARDOWN FAILURE: unhandled exception during cleanup: {exc}")
			exit_code = max(exit_code, 2)

	return exit_code


if __name__ == "__main__":
	raise SystemExit(main(sys.argv[1:]))
