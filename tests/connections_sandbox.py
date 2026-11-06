"""Opt-in pytest safety fixture for in-process connection tests.

Load with `-p tests.connections_sandbox`. Provider fakes are injected by the
tests. The guard covers the urllib transport shared by both real adapters.
"""

from urllib.parse import urlsplit
from urllib.request import AbstractHTTPHandler

import pytest


@pytest.fixture(autouse=True)
def isolate_connections(tmp_path, monkeypatch):
    """Keep connection tests on disposable paths and permit loopback callbacks."""
    monkeypatch.setenv("BEARPLANS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BEARPLANS_SECRETS_FILE", str(tmp_path / "secrets" / "none.env"))
    monkeypatch.setenv("no_proxy", "127.0.0.1,::1")
    original = AbstractHTTPHandler.do_open

    def loopback_only(handler, http_class, request, **options):
        if urlsplit(request.full_url).hostname not in {"127.0.0.1", "::1"}:
            raise AssertionError("Unexpected outbound HTTP request in a connection test.")
        return original(handler, http_class, request, **options)

    monkeypatch.setattr(AbstractHTTPHandler, "do_open", loopback_only)
