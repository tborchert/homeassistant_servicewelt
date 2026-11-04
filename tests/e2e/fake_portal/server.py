"""
Fake Servicewelt (ISG web) portal for end-to-end tests.

Serves the captured pages from ``sample_pages/`` the same way the real device
does: ``GET /?s=1,0`` returns ``s_1_0.html``. A small control API under
``/_control`` lets tests change what the portal returns while Home Assistant
is polling it.

Control API:
    POST /_control/reset                      restore all pages to the samples
    POST /_control/pages/{page}  (JSON)       override one page, e.g. page "1,0"
        {"replace": [["26,3°C", "12,0°C"]]}   string substitutions on the sample
        {"status": 500}                       respond with this HTTP status
        {"delay": 15}                         sleep before responding (seconds)
    GET  /_control/requests                   pages requested so far
    DELETE /_control/requests                 clear the request log
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from aiohttp import web

PAGES_DIR = Path(os.environ.get("PAGES_DIR", "/pages"))

overrides: dict[str, dict] = {}
request_log: list[str] = []


def _sample_for(page: str) -> Path:
    return PAGES_DIR / f"s_{page.replace(',', '_')}.html"


async def portal(request: web.Request) -> web.StreamResponse:
    """Serve a portal page selected by the ``s`` query parameter."""
    page = request.query.get("s", "0")
    request_log.append(page)

    override = overrides.get(page, {})
    if delay := override.get("delay"):
        await asyncio.sleep(delay)
    if status := override.get("status"):
        return web.Response(status=status, text=f"forced status {status}")

    sample = _sample_for(page)
    if not sample.is_file():
        return web.Response(status=404, text=f"no sample page for s={page}")

    html = sample.read_text(encoding="utf-8")
    for old, new in override.get("replace", []):
        html = html.replace(old, new)
    return web.Response(text=html, content_type="text/html", charset="utf-8")


async def reset(_: web.Request) -> web.Response:
    overrides.clear()
    request_log.clear()
    return web.json_response({"ok": True})


async def set_override(request: web.Request) -> web.Response:
    page = request.match_info["page"]
    overrides[page] = await request.json()
    return web.json_response({"ok": True, "page": page})


async def get_requests(_: web.Request) -> web.Response:
    return web.json_response(request_log)


async def clear_requests(_: web.Request) -> web.Response:
    request_log.clear()
    return web.json_response({"ok": True})


async def health(_: web.Request) -> web.Response:
    return web.json_response({"ok": True})


def make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", portal)
    app.router.add_get("/_control/health", health)
    app.router.add_post("/_control/reset", reset)
    app.router.add_post("/_control/pages/{page}", set_override)
    app.router.add_get("/_control/requests", get_requests)
    app.router.add_delete("/_control/requests", clear_requests)
    return app


if __name__ == "__main__":
    web.run_app(make_app(), port=int(os.environ.get("PORT", "80")))
