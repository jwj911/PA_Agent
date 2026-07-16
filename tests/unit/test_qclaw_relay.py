"""Tests for the local QClaw relay HTTP helper."""
from __future__ import annotations

import http.server
import json
import socket
import threading
import urllib.request

from pa_agent.ai import qclaw_relay


def _serve_relay() -> tuple[http.server.HTTPServer, str]:
    server = http.server.HTTPServer((qclaw_relay.LISTEN_HOST, 0), qclaw_relay.ProxyHandler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://{host}:{port}"


def test_find_free_port_skips_occupied_port() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((qclaw_relay.LISTEN_HOST, 0))
        sock.listen()
        occupied = sock.getsockname()[1]

        assert qclaw_relay._find_free_port(occupied) == occupied + 1


def test_relay_health_endpoint_returns_service_metadata() -> None:
    server, base_url = _serve_relay()
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        assert payload == {
            "ok": True,
            "upstream": qclaw_relay.UPSTREAM,
            "service": "pa-agent-qclaw-relay",
        }
    finally:
        server.shutdown()
        server.server_close()


def test_relay_models_endpoint_returns_supported_pool_models() -> None:
    server, base_url = _serve_relay()
    try:
        with urllib.request.urlopen(f"{base_url}/v1/models", timeout=5) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        assert payload == {
            "object": "list",
            "data": [
                {"id": "pool-deepseek-v4-pro", "object": "model"},
                {"id": "pool-deepseek-v4-flash", "object": "model"},
            ],
        }
    finally:
        server.shutdown()
        server.server_close()
