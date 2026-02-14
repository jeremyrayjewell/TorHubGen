
import argparse
import datetime
import json
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
from collections import deque
from dataclasses import dataclass
from typing import Optional

import http.server


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
	web_server: Optional["WebServerHandle"]


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
	_info(f"Connected to Tor ControlPort on 127.0.0.1:{control_port}")
	return controller


def _format_returncode(rc: Optional[int]) -> str:
	if rc is None:
		return "<running>"
	if rc == 0:
		return "0 (clean exit)"
	return f"{rc} (abnormal exit)"


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
MAX_MESSAGES = 100
MAX_MESSAGE_CHARS = 2000
MAX_PSEUDONYM_CHARS = 32
MAX_REQUEST_BODY_BYTES = 4096


class MessageStore:
	def __init__(self, *, max_messages: int) -> None:
		self._messages: deque[dict] = deque(maxlen=max_messages)
		self._lock = threading.Lock()

	def add(self, message: dict) -> None:
		with self._lock:
			self._messages.append(message)

	def list(self) -> list[dict]:
		with self._lock:
			return list(self._messages)

	def clear(self) -> None:
		with self._lock:
			self._messages.clear()


class TokenBucketRateLimiter:
	"""In-memory, per-process token bucket limiter.

	No IP-based keys are used. Keys are caller-supplied (e.g., pseudonym or a global key).
	"""

	def __init__(self, *, capacity: float, refill_per_second: float) -> None:
		if capacity <= 0 or refill_per_second <= 0:
			raise ValueError("Invalid rate limiter parameters")
		self._capacity = float(capacity)
		self._refill_per_second = float(refill_per_second)
		self._state: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_ts)
		self._lock = threading.Lock()

	def allow(self, key: str, *, cost: float = 1.0) -> bool:
		now = time.monotonic()
		with self._lock:
			tokens, last_ts = self._state.get(key, (self._capacity, now))
			elapsed = max(0.0, now - last_ts)
			tokens = min(self._capacity, tokens + elapsed * self._refill_per_second)
			if tokens < cost:
				self._state[key] = (tokens, now)
				return False
			tokens -= cost
			self._state[key] = (tokens, now)
			return True


class BulletinHTTPServer(http.server.HTTPServer):
	def __init__(
		self,
		server_address: tuple[str, int],
		RequestHandlerClass,
		*,
		store: MessageStore,
		rate_limiter: TokenBucketRateLimiter,
		max_body_bytes: int,
	) -> None:
		super().__init__(server_address, RequestHandlerClass)
		self.store = store
		self.rate_limiter = rate_limiter
		self.max_body_bytes = int(max_body_bytes)


class BulletinHandler(http.server.BaseHTTPRequestHandler):
	server: BulletinHTTPServer  # type: ignore[assignment]

	def log_message(self, fmt: str, *args) -> None:
		# No request logging (and nothing written to disk).
		return

	def _send_bytes(self, *, status: int, body: bytes, content_type: str) -> None:
		self.send_response(status)
		self.send_header("Content-Type", content_type)
		self.send_header("Content-Length", str(len(body)))
		self.send_header("Cache-Control", "no-store")
		self.end_headers()
		self.wfile.write(body)

	def _send_json(self, *, status: int, obj) -> None:
		body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
		self._send_bytes(status=status, body=body, content_type="application/json; charset=utf-8")

	def _send_error_json(self, *, status: int, message: str) -> None:
		self._send_json(status=status, obj={"error": message})

	def _read_body(self) -> Optional[bytes]:
		content_length_raw = self.headers.get("Content-Length")
		if content_length_raw is None:
			self._send_error_json(status=411, message="Content-Length required")
			return None
		try:
			content_length = int(content_length_raw)
		except ValueError:
			self._send_error_json(status=400, message="Invalid Content-Length")
			return None
		if content_length < 0:
			self._send_error_json(status=400, message="Invalid Content-Length")
			return None
		if content_length > self.server.max_body_bytes:
			# Reject early and close the connection; do not attempt to read an oversized payload.
			self._send_error_json(status=413, message="Request body too large")
			self.close_connection = True
			return None
		body = self.rfile.read(content_length)
		if len(body) != content_length:
			self._send_error_json(status=400, message="Incomplete request body")
			return None
		if b"\x00" in body:
			self._send_error_json(status=400, message="Binary payload rejected")
			return None
		return body

	def do_GET(self) -> None:
		if self.path == "/":
			html = (
				"<!doctype html><meta charset='utf-8'>"
				"<title>TorHubGen Phase 2</title>"
				"<h1>TorHubGen Phase 2</h1>"
				"<p>Ephemeral in-memory bulletin surface.</p>"
				"<ul>"
				"<li>GET /messages</li>"
				"<li>POST /message (JSON: {content, pseudonym?})</li>"
				"</ul>"
			).encode("utf-8")
			self._send_bytes(status=200, body=html, content_type="text/html; charset=utf-8")
			return

		if self.path == "/messages":
			# Basic global rate limit on reads.
			if not self.server.rate_limiter.allow("GET:/messages"):
				self._send_error_json(status=429, message="Rate limit exceeded")
				return
			self._send_json(status=200, obj={"messages": self.server.store.list()})
			return

		self._send_error_json(status=404, message="Not found")

	def do_POST(self) -> None:
		if self.path != "/message":
			self._send_error_json(status=404, message="Not found")
			return

		content_type = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
		if content_type != "application/json":
			self._send_error_json(status=415, message="Content-Type must be application/json")
			return

		body = self._read_body()
		if body is None:
			return
		try:
			text = body.decode("utf-8")
		except UnicodeDecodeError:
			self._send_error_json(status=400, message="Request body must be UTF-8 JSON")
			return
		try:
			payload = json.loads(text)
		except json.JSONDecodeError:
			self._send_error_json(status=400, message="Invalid JSON")
			return
		if not isinstance(payload, dict):
			self._send_error_json(status=400, message="JSON object required")
			return

		content = payload.get("content")
		pseudonym = payload.get("pseudonym")

		if not isinstance(content, str):
			self._send_error_json(status=400, message="Field 'content' must be a string")
			return
		content = content.strip()
		if not content:
			self._send_error_json(status=400, message="Field 'content' is required")
			return
		if len(content) > MAX_MESSAGE_CHARS:
			self._send_error_json(status=413, message="Message too long")
			return

		pseudo_key = "anon"
		pseudo_value: Optional[str] = None
		if pseudonym is not None:
			if not isinstance(pseudonym, str):
				self._send_error_json(status=400, message="Field 'pseudonym' must be a string")
				return
			pseudonym = pseudonym.strip()
			if pseudonym:
				if len(pseudonym) > MAX_PSEUDONYM_CHARS:
					self._send_error_json(status=413, message="Pseudonym too long")
					return
				pseudo_value = pseudonym
				pseudo_key = f"p:{pseudonym}"

		# Basic rate limiting (no IP usage): global + per pseudonym/anon.
		if not self.server.rate_limiter.allow("POST:/message"):
			self._send_error_json(status=429, message="Rate limit exceeded")
			return
		if not self.server.rate_limiter.allow(pseudo_key):
			self._send_error_json(status=429, message="Rate limit exceeded")
			return

		timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
		message = {
			"timestamp": timestamp,
			"pseudonym": pseudo_value,
			"content": content,
		}
		self.server.store.add(message)
		self._send_json(status=201, obj={"ok": True})


@dataclass
class WebServerHandle:
	server: BulletinHTTPServer
	thread: threading.Thread
	store: MessageStore

	def is_alive(self) -> bool:
		return self.thread.is_alive()

	def stop(self, *, timeout: float = 5.0) -> None:
		# Idempotent best-effort: tolerate already-stopped server/thread.
		try:
			self.server.shutdown()
		except Exception:
			pass
		try:
			self.server.server_close()
		except Exception:
			pass
		if self.thread.is_alive():
			self.thread.join(timeout=timeout)
			if self.thread.is_alive():
				raise RuntimeError("Web server thread did not stop")

	def clear(self) -> None:
		self.store.clear()


def launch_local_web_server(*, bind_host: str, port: int) -> WebServerHandle:
	if bind_host != "127.0.0.1":
		raise ValueError("Phase 2 requires binding to 127.0.0.1 only")

	store = MessageStore(max_messages=MAX_MESSAGES)
	# Keep this conservative: allows small bursts but bounds abuse.
	rate_limiter = TokenBucketRateLimiter(capacity=10.0, refill_per_second=1.0)

	server = BulletinHTTPServer(
		(bind_host, int(port)),
		BulletinHandler,
		store=store,
		rate_limiter=rate_limiter,
		max_body_bytes=MAX_REQUEST_BODY_BYTES,
	)

	thread = threading.Thread(
		target=server.serve_forever,
		kwargs={"poll_interval": 0.2},
		name="torhubgen_web",
		daemon=False,
	)
	thread.start()
	return WebServerHandle(server=server, thread=thread, store=store)


# --- Lifetime enforcement + atomic shutdown monitoring ---
def enforce_lifetime(
	*,
	lifetime_seconds: int,
	shutdown: ShutdownSignal,
	tor_process: subprocess.Popen,
	web_server: WebServerHandle,
	controller: Optional[Controller],
) -> None:
	start = time.monotonic()
	last_controller_heartbeat = start
	controller_disconnected = False
	controller_disconnect_logged = False
	if controller is not None:
		_info("Control connection will remain open until teardown")

	while True:
		if shutdown.is_set():
			raise ShutdownRequested(shutdown.reason or "shutdown requested")

		# Requirement: unexpected Tor exit MUST terminate immediately.
		if tor_process.poll() is not None:
			rc = tor_process.returncode
			if controller_disconnected and not controller_disconnect_logged:
				# This should already have been logged, but ensure we surface it even if the
				# disconnect and exit happen back-to-back.
				_warn("Control connection was lost before Tor exit (possible ownership-triggered termination)")
				controller_disconnect_logged = True
			_warn(f"Tor exited unexpectedly with code: {_format_returncode(rc)}")
			raise RuntimeError(f"Tor process exited unexpectedly (returncode={rc})")

		# Defensive handling: detect unexpected control-channel loss while Tor is alive.
		# Do not treat this as a normal condition; log it so ownership-triggered termination is diagnosable.
		if controller is not None and not controller_disconnected:
			# Heartbeat at a low rate to keep the control connection active and detect drops.
			if (time.monotonic() - last_controller_heartbeat) >= 2.0:
				last_controller_heartbeat = time.monotonic()
				try:
					if not controller.is_alive():
						raise RuntimeError("controller.is_alive() returned False")
					# A minimal NOOP-style call to verify the control channel is responsive.
					controller.get_info("version")
				except Exception as exc:
					controller_disconnected = True
					controller_disconnect_logged = True
					_warn(f"Control connection lost while Tor is still running: {exc}")

		# Requirement: local HTTP surface must not outlive Tor.
		if not web_server.is_alive():
			raise RuntimeError("Local web server stopped unexpectedly")

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

	# Stop web server and clear in-memory state.
	if state.web_server is not None:
		try:
			state.web_server.stop(timeout=5.0)
		except Exception as exc:
			teardown_failed = True
			_warn(f"Failed to stop local web server cleanly: {exc}")
		try:
			state.web_server.clear()
		except Exception as exc:
			teardown_failed = True
			_warn(f"Failed to clear in-memory message buffer: {exc}")

	# Stop Tor via ControlPort if possible; otherwise terminate the process.
	if state.controller is not None:
		if tor_already_exited:
			# Tor already exited; control connection may already be broken. Closing is best-effort and
			# must not be classified as a teardown failure in this expected scenario.
			_info("Closing controller (Tor already exited)")
			try:
				state.controller.close()
			except Exception as exc:
				_warn(f"Failed to close controller after Tor exit: {exc}")
			else:
				_info("Controller disconnected")
		else:
			_info("Sending Tor SHUTDOWN via ControlPort")
			try:
				state.controller.msg("SIGNAL SHUTDOWN")
			except Exception as exc:
				teardown_failed = True
				_warn(f"Failed to send Tor SHUTDOWN via ControlPort: {exc}")
			finally:
				_info("Closing controller")
				try:
					state.controller.close()
				except Exception as exc:
					teardown_failed = True
					_warn(f"Failed to close controller: {exc}")
				else:
					_info("Controller disconnected")

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
		# Returncode is known after wait/terminate/kill attempts.
		_info(f"Tor exit code: {_format_returncode(state.tor_process.returncode)}")

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
		web_server=None,
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
		state.web_server = launch_local_web_server(bind_host="127.0.0.1", port=web_port)
		_info(f"Local web server listening on http://127.0.0.1:{web_port}")

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
			web_server=state.web_server,
			controller=state.controller,
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
