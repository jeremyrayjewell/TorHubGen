"""Minimal localhost-only bulletin board HTTP surface."""

from __future__ import annotations

import datetime
import html
import json
import threading
from dataclasses import dataclass
from typing import Optional

import http.server

from .memory_store import MessageStore, TokenBucketRateLimiter


DEFAULT_BIND_HOST = "127.0.0.1"
MAX_MESSAGES = 100
MAX_MESSAGE_CHARS = 2000
MAX_PSEUDONYM_CHARS = 32
MAX_REQUEST_BODY_BYTES = 4096


class BulletinHTTPServer(http.server.HTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        request_handler_class,
        *,
        store: MessageStore,
        rate_limiter: TokenBucketRateLimiter,
        max_body_bytes: int,
    ) -> None:
        super().__init__(server_address, request_handler_class)
        self.store = store
        self.rate_limiter = rate_limiter
        self.max_body_bytes = int(max_body_bytes)


class BulletinHandler(http.server.BaseHTTPRequestHandler):
    server: BulletinHTTPServer

    def log_message(self, fmt: str, *args) -> None:
        return

    def _format_message_timestamp(self, raw_timestamp: object) -> tuple[str, str]:
        raw_text = str(raw_timestamp or "")
        try:
            parsed = datetime.datetime.fromisoformat(raw_text)
        except ValueError:
            return raw_text, raw_text

        if parsed.tzinfo is None:
            return parsed.strftime("%Y-%m-%d %H:%M:%S"), raw_text

        display = parsed.astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        return display, raw_text

    def _render_home_page(self) -> bytes:
        messages_html: list[str] = []
        for message in self.server.store.list():
            timestamp_display, timestamp_raw = self._format_message_timestamp(
                message.get("timestamp", "")
            )
            timestamp_display = html.escape(timestamp_display)
            timestamp_raw = html.escape(timestamp_raw)
            pseudonym_raw = message.get("pseudonym")
            pseudonym = html.escape(str(pseudonym_raw)) if pseudonym_raw else "anon"
            content = html.escape(str(message.get("content", "")))
            messages_html.append(
                "<li class='message-card'>"
                "<div class='message-meta'>"
                f"<strong>{pseudonym}</strong>"
                f"<time datetime='{timestamp_raw}' title='Original timestamp: {timestamp_raw}'>"
                f"{timestamp_display}</time>"
                "</div>"
                f"<div class='message-content'>{content}</div>"
                "</li>"
            )

        if not messages_html:
            messages_html.append(
                "<li class='message-card empty-state'>"
                "<div>No messages yet. This board starts empty each time TorHubGen runs.</div>"
                "</li>"
            )

        page = (
            "<!doctype html>"
            "<html lang='en'>"
            "<head>"
            "<meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>TorHubGen Bulletin Board</title>"
            "<style>"
            "body{font-family:system-ui,sans-serif;max-width:760px;margin:2rem auto;"
            "padding:0 1rem;line-height:1.5;background:#f7f7f7;color:#111;}"
            "main{background:#fff;border:1px solid #d7d7d7;border-radius:8px;padding:1rem 1.25rem;}"
            ".warning{background:#fff8d8;border:1px solid #e3d28b;padding:.75rem;border-radius:6px;}"
            ".subtle{color:#444;font-size:.95rem;}"
            "form{display:grid;gap:.75rem;margin-top:1rem;}"
            "label{display:grid;gap:.25rem;font-weight:600;}"
            "input,textarea,button{font:inherit;}"
            "input,textarea{padding:.5rem;border:1px solid #999;border-radius:4px;}"
            "textarea{min-height:8rem;resize:vertical;}"
            "button{width:max-content;padding:.55rem .9rem;border:1px solid #444;border-radius:4px;"
            "background:#111;color:#fff;cursor:pointer;}"
            "button[disabled]{opacity:.65;cursor:wait;}"
            "ul{list-style:none;padding:0;display:grid;gap:.75rem;}"
            ".message-card{border:1px solid #ddd;border-radius:6px;padding:.8rem .9rem;background:#fafafa;}"
            ".message-meta{display:flex;justify-content:space-between;gap:1rem;align-items:baseline;"
            "margin-bottom:.5rem;flex-wrap:wrap;}"
            ".message-meta time{font-size:.9rem;color:#555;}"
            ".message-content{white-space:pre-wrap;word-break:break-word;}"
            ".empty-state{background:#fcfcfc;color:#444;font-style:italic;}"
            "#status{min-height:1.25rem;font-size:.95rem;margin-top:.5rem;}"
            "#status.success{color:#0b5d1e;}"
            "#status.error{color:#8b1e1e;}"
            "</style>"
            "</head>"
            "<body>"
            "<main>"
            "<h1>TorHubGen Bulletin Board</h1>"
            "<p class='warning'>This board is ephemeral and exists only for the lifetime "
            "of the current TorHubGen process. It is not a safety, anonymity, or "
            "confidentiality guarantee.</p>"
            "<h2>Messages</h2>"
            f"<ul>{''.join(messages_html)}</ul>"
            "<h2>Post Message</h2>"
            "<p class='subtle'>Messages are stored only in memory and disappear when the "
            "TorHubGen process ends.</p>"
            "<form id='message-form'>"
            "<label>Pseudonym (optional)"
            "<input id='pseudonym' name='pseudonym' maxlength='32' autocomplete='off'>"
            "</label>"
            "<label>Content"
            "<textarea id='content' name='content' maxlength='2000' required></textarea>"
            "</label>"
            "<button id='submit-button' type='submit'>Post</button>"
            "</form>"
            "<p id='status' aria-live='polite'></p>"
            "<script>"
            "const form=document.getElementById('message-form');"
            "const status=document.getElementById('status');"
            "const submitButton=document.getElementById('submit-button');"
            "form.addEventListener('submit',async(event)=>{"
            "event.preventDefault();"
            "if(submitButton.disabled){return;}"
            "submitButton.disabled=true;"
            "status.className='';"
            "status.textContent='Submitting...';"
            "const pseudonym=document.getElementById('pseudonym').value;"
            "const content=document.getElementById('content').value;"
            "const payload={content:content};"
            "if(pseudonym.trim()){payload.pseudonym=pseudonym;}"
            "try{"
            "const response=await fetch('/message',{method:'POST',headers:{'Content-Type':'application/json'},"
            "body:JSON.stringify(payload)});"
            "if(!response.ok){"
            "const data=await response.json().catch(()=>({error:'Request failed'}));"
            "status.className='error';"
            "status.textContent=data.error||'Request failed';"
            "submitButton.disabled=false;"
            "return;}"
            "form.reset();"
            "status.className='success';"
            "status.textContent='Message posted. Refreshing the message list...';"
            "window.setTimeout(()=>window.location.reload(),450);"
            "}catch(error){"
            "status.className='error';"
            "status.textContent='Submission failed';"
            "submitButton.disabled=false;"
            "}"
            "});"
            "</script>"
            "</main>"
            "</body>"
            "</html>"
        )
        return page.encode("utf-8")

    def _discard_known_body(self) -> None:
        content_length_raw = self.headers.get("Content-Length")
        if content_length_raw is None:
            return
        try:
            content_length = int(content_length_raw)
        except ValueError:
            return
        if content_length <= 0:
            return
        remaining = content_length
        if remaining > self.server.max_body_bytes:
            # We won't spend arbitrary time draining oversized unknown-route
            # bodies. Consume a bounded amount and close the connection.
            self.close_connection = True
            remaining = self.server.max_body_bytes
        try:
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 4096))
                if not chunk:
                    break
                remaining -= len(chunk)
        except Exception:
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
        self._send_bytes(
            status=status,
            body=body,
            content_type="application/json; charset=utf-8",
        )

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
            self._send_bytes(
                status=200,
                body=self._render_home_page(),
                content_type="text/html; charset=utf-8",
            )
            return

        if self.path == "/messages":
            if not self.server.rate_limiter.allow("GET:/messages"):
                self._send_error_json(status=429, message="Rate limit exceeded")
                return
            self._send_json(status=200, obj={"messages": self.server.store.list()})
            return

        self._send_error_json(status=404, message="Not found")

    def do_POST(self) -> None:
        if self.path != "/message":
            self._discard_known_body()
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

    @property
    def port(self) -> int:
        return int(self.server.server_address[1])

    def is_alive(self) -> bool:
        return self.thread.is_alive()

    def stop(self, *, timeout: float = 5.0) -> None:
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


def launch_local_web_server(
    *,
    bind_host: str,
    port: int,
    max_messages: int = MAX_MESSAGES,
    rate_limiter: Optional[TokenBucketRateLimiter] = None,
    max_body_bytes: int = MAX_REQUEST_BODY_BYTES,
) -> WebServerHandle:
    if bind_host != DEFAULT_BIND_HOST:
        raise ValueError("TorHubGen requires binding to 127.0.0.1 only")

    store = MessageStore(max_messages=max_messages)
    if rate_limiter is None:
        rate_limiter = TokenBucketRateLimiter(capacity=10.0, refill_per_second=1.0)

    server = BulletinHTTPServer(
        (bind_host, int(port)),
        BulletinHandler,
        store=store,
        rate_limiter=rate_limiter,
        max_body_bytes=max_body_bytes,
    )

    thread = threading.Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.2},
        name="torhubgen_web",
        daemon=False,
    )
    thread.start()
    return WebServerHandle(server=server, thread=thread, store=store)
