from __future__ import annotations

import json
import urllib.error
import urllib.request
from contextlib import contextmanager

import pytest

from torhubgen.board_server import (
    DEFAULT_BIND_HOST,
    MAX_MESSAGE_CHARS,
    MAX_REQUEST_BODY_BYTES,
    WebServerHandle,
    launch_local_web_server,
)
from torhubgen.memory_store import TokenBucketRateLimiter


def request(method: str, url: str, payload=None, headers=None) -> tuple[int, bytes]:
    request_headers = {} if headers is None else dict(headers)
    data = None
    if payload is not None:
        if isinstance(payload, (bytes, bytearray)):
            data = bytes(payload)
        else:
            data = json.dumps(payload).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


@contextmanager
def running_server(*, rate_limiter=None) -> WebServerHandle:
    handle = launch_local_web_server(
        bind_host=DEFAULT_BIND_HOST,
        port=0,
        rate_limiter=rate_limiter,
    )
    try:
        yield handle
    finally:
        handle.stop()
        handle.clear()


def test_local_http_server_binds_only_to_loopback() -> None:
    with running_server() as handle:
        assert handle.server.server_address[0] == DEFAULT_BIND_HOST


def test_local_http_server_rejects_non_loopback_binding() -> None:
    with pytest.raises(ValueError, match="127.0.0.1 only"):
        launch_local_web_server(bind_host="0.0.0.0", port=0)


def test_only_expected_endpoints_are_valid() -> None:
    with running_server() as handle:
        base_url = f"http://127.0.0.1:{handle.port}"

        status, body = request("GET", f"{base_url}/messages")
        assert status == 200
        assert json.loads(body) == {"messages": []}

        status, body = request("POST", f"{base_url}/message", payload={"content": "hello"})
        assert status == 201
        assert json.loads(body) == {"ok": True}

        status, _ = request("GET", f"{base_url}/")
        assert status == 404

        status, _ = request("POST", f"{base_url}/messages", payload={"content": "hello"})
        assert status == 404


def test_unknown_routes_fail_closed() -> None:
    with running_server() as handle:
        base_url = f"http://127.0.0.1:{handle.port}"

        status, _ = request("GET", f"{base_url}/nope")
        assert status == 404

        status, _ = request("POST", f"{base_url}/nope", payload={"content": "hello"})
        assert status == 404


def test_unknown_post_with_oversized_body_fails_closed_cleanly() -> None:
    with running_server() as handle:
        base_url = f"http://127.0.0.1:{handle.port}"
        status, _ = request(
            "POST",
            f"{base_url}/nope",
            payload=b"x" * (MAX_REQUEST_BODY_BYTES + 1),
        )
        assert status == 404


def test_oversized_posts_are_rejected() -> None:
    with running_server() as handle:
        base_url = f"http://127.0.0.1:{handle.port}"
        status, body = request(
            "POST",
            f"{base_url}/message",
            payload={"content": "x" * (MAX_MESSAGE_CHARS + 1)},
        )
        assert status == 413
        assert json.loads(body)["error"] == "Message too long"


def test_basic_rate_limiting_blocks_second_post() -> None:
    limiter = TokenBucketRateLimiter(capacity=1.0, refill_per_second=0.01)
    with running_server(rate_limiter=limiter) as handle:
        base_url = f"http://127.0.0.1:{handle.port}"

        first_status, _ = request(
            "POST",
            f"{base_url}/message",
            payload={"content": "hello", "pseudonym": "alice"},
        )
        second_status, _ = request(
            "POST",
            f"{base_url}/message",
            payload={"content": "again", "pseudonym": "alice"},
        )

        assert first_status == 201
        assert second_status == 429
