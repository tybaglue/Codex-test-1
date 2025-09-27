"""Minimal adapter to run a Flask (WSGI) app on Vercel's Python runtime."""

from __future__ import annotations

import base64
from io import BytesIO
from typing import Callable, Dict, Iterable, Tuple
from urllib.parse import urlencode

WSGIApp = Callable[[Dict[str, str], Callable], Iterable[bytes]]


def _build_environ(event: dict) -> Dict[str, str]:
    request_context = event.get("requestContext", {}) or {}
    http = request_context.get("http", {}) or {}

    method = http.get("method") or event.get("httpMethod") or "GET"
    raw_path = event.get("rawPath") or event.get("path") or "/"
    raw_query = event.get("rawQueryString")
    if raw_query is None:
        params = event.get("queryStringParameters") or {}
        raw_query = urlencode(params, doseq=True)

    headers = event.get("headers") or {}
    lower_headers = {k.lower(): v for k, v in headers.items()}

    body = event.get("body") or b""
    if event.get("isBase64Encoded"):
        body_bytes = base64.b64decode(body)
    elif isinstance(body, str):
        body_bytes = body.encode("utf-8")
    else:
        body_bytes = body

    environ: Dict[str, str] = {
        "REQUEST_METHOD": method,
        "SCRIPT_NAME": "",
        "PATH_INFO": raw_path or "/",
        "QUERY_STRING": raw_query or "",
        "SERVER_NAME": lower_headers.get("host", "127.0.0.1"),
        "SERVER_PORT": lower_headers.get("x-forwarded-port", "80"),
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": lower_headers.get("x-forwarded-proto", "https"),
        "wsgi.input": BytesIO(body_bytes),
        "wsgi.errors": BytesIO(),
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": True,
        "CONTENT_LENGTH": str(len(body_bytes)),
        "CONTENT_TYPE": lower_headers.get("content-type", ""),
    }

    for key, value in headers.items():
        header_name = "HTTP_" + key.upper().replace("-", "_")
        if header_name in ("HTTP_CONTENT_TYPE", "HTTP_CONTENT_LENGTH"):
            continue
        environ[header_name] = value

    return environ


def _collect_body(result: Iterable[bytes]) -> bytes:
    chunks = []
    for piece in result:
        chunks.append(piece)
    if hasattr(result, "close"):
        result.close()  # type: ignore[attr-defined]
    return b"".join(chunks)


def handle(app: WSGIApp, event: dict, context: dict) -> dict:
    environ = _build_environ(event)

    status_holder: Dict[str, str] = {}
    header_list = []
    write_chunks = []

    def start_response(status: str, response_headers: list, exc_info=None):  # type: ignore[no-untyped-def]
        status_holder["status"] = status
        header_list.extend(response_headers)
        return write_chunks.append

    result = app(environ, start_response)
    body_bytes = _collect_body(result)
    if write_chunks:
        body_bytes += b"".join(write_chunks)

    status_code = int(status_holder.get("status", "200").split(" ")[0])

    headers: Dict[str, str] = {}
    for key, value in header_list:
        if key in headers:
            headers[key] = f"{headers[key]}, {value}"
        else:
            headers[key] = value

    try:
        body_text = body_bytes.decode("utf-8")
        is_base64 = False
    except UnicodeDecodeError:
        body_text = base64.b64encode(body_bytes).decode("utf-8")
        is_base64 = True

    return {
        "statusCode": status_code,
        "headers": headers,
        "body": body_text,
        "isBase64Encoded": is_base64,
    }
