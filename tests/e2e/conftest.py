"""
Fixtures for the end-to-end tests.

The tests run against two real containers (see docker-compose.yml): Home
Assistant with this integration mounted, and a fake Servicewelt portal that
serves ``sample_pages/``. Everything is driven over HTTP, exactly as a user
or the HA frontend would: onboarding, config flow, states API.

Environment variables:
    E2E_KEEP_STACK=1   leave the containers running after the session
    E2E_NO_BUILD=1     skip ``--build`` (faster reruns)
    HA_PORT / PORTAL_PORT / HA_VERSION   override compose defaults
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import pytest_socket

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from datetime import datetime

E2E_DIR = Path(__file__).parent
COMPOSE_FILE = E2E_DIR / "docker-compose.yml"
LOG_DIR = E2E_DIR / "logs"

HA_URL = f"http://localhost:{os.environ.get('HA_PORT', '18123')}"
PORTAL_URL = f"http://localhost:{os.environ.get('PORTAL_PORT', '18080')}"
# Address of the fake portal as seen from inside the HA container
PORTAL_HOST_FOR_HA = "http://servicewelt"
CLIENT_ID = f"{HA_URL}/"

# Test-only HA owner account, created fresh in each throwaway container
HA_USERNAME = "e2e"
HA_PASSWORD = "e2e-password"  # noqa: S105


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if E2E_DIR in Path(item.fspath).parents:
            item.add_marker(pytest.mark.e2e)


def wait_for[T](
    probe: Callable[[], T | None],
    timeout: float = 30,
    interval: float = 0.5,
    message: str = "condition",
) -> T:
    """Call ``probe`` until it returns a truthy value or ``timeout`` expires."""
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if result := probe():
                return result
        except (httpx.HTTPError, AssertionError, KeyError) as err:
            last_error = err
        time.sleep(interval)
    msg = f"Timed out after {timeout}s waiting for {message}"
    if last_error:
        msg += f" (last error: {last_error!r})"
    raise TimeoutError(msg)


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        ["docker", "compose", "-f", str(COMPOSE_FILE), *args],  # noqa: S607
        check=check,
        capture_output=True,
        text=True,
    )


def allow_network() -> None:
    pytest_socket.enable_socket()
    # The connect() allowlist is a separate patch; localhost may resolve to
    # either loopback address. Must come after enable_socket().
    pytest_socket.socket_allow_hosts(["127.0.0.1", "::1"])


@pytest.fixture(autouse=True)
def _allow_network() -> None:
    """
    Undo pytest-homeassistant-custom-component's socket block.

    That plugin blocks sockets before every test, but these tests talk to
    real containers. ``stack`` calls this too, because session fixtures are
    set up before this one on the first test.
    """
    allow_network()


@pytest.fixture(scope="session")
def stack() -> Iterator[None]:
    """Start the compose stack for the test session and tear it down after."""
    allow_network()
    if shutil.which("docker") is None:
        pytest.skip("docker is not installed")
    if subprocess.run(["docker", "info"], capture_output=True, check=False).returncode:  # noqa: S607
        pytest.skip("docker daemon is not running")

    compose("down", "-v", "--remove-orphans", check=False)
    up = ["up", "-d", "--wait"]
    if not os.environ.get("E2E_NO_BUILD"):
        up.append("--build")
    result = compose(*up, check=False)
    if result.returncode:
        logs = compose("logs", check=False).stdout
        pytest.fail(f"docker compose up failed:\n{result.stderr}\n{logs}")

    yield

    LOG_DIR.mkdir(exist_ok=True)
    (LOG_DIR / "homeassistant.log").write_text(
        compose("logs", "--no-color", "homeassistant", check=False).stdout
    )
    if not os.environ.get("E2E_KEEP_STACK"):
        compose("down", "-v", "--remove-orphans", check=False)


def ha_logs_since(since: datetime) -> str:
    """Return the HA container log written since ``since``."""
    return compose(
        "logs",
        "--no-color",
        "--no-log-prefix",
        "--since",
        since.isoformat(),
        "homeassistant",
        check=False,
    ).stdout


@dataclass
class HomeAssistant:
    """Thin wrapper around an authenticated HA REST client."""

    http: httpx.Client

    def states(self) -> list[dict[str, Any]]:
        response = self.http.get("/api/states")
        response.raise_for_status()
        return response.json()

    def servicewelt_states(self) -> dict[str, dict[str, Any]]:
        """Servicewelt entity states keyed by friendly name."""
        return {
            s["attributes"]["friendly_name"]: s
            for s in self.states()
            if s["entity_id"] in self.servicewelt_entity_ids()
        }

    def servicewelt_entity_ids(self) -> set[str]:
        # The entity registry is only exposed over the websocket API; the
        # template endpoint answers the same question over REST.
        response = self.http.post(
            "/api/template",
            json={"template": "{{ integration_entities('servicewelt') | tojson }}"},
        )
        response.raise_for_status()
        return set(response.json())

    def start_flow(self) -> dict[str, Any]:
        response = self.http.post(
            "/api/config/config_entries/flow",
            json={"handler": "servicewelt", "show_advanced_options": False},
        )
        response.raise_for_status()
        return response.json()

    def submit_flow(self, flow_id: str, user_input: dict[str, Any]) -> dict[str, Any]:
        response = self.http.post(
            f"/api/config/config_entries/flow/{flow_id}", json=user_input
        )
        response.raise_for_status()
        return response.json()

    def config_entries(self) -> list[dict[str, Any]]:
        response = self.http.get(
            "/api/config/config_entries/entry", params={"domain": "servicewelt"}
        )
        response.raise_for_status()
        return response.json()

    def delete_entry(self, entry_id: str) -> None:
        self.http.delete(
            f"/api/config/config_entries/entry/{entry_id}"
        ).raise_for_status()


def _onboard() -> str:
    """Create the owner account on a fresh HA and return an access token."""
    wait_for(
        lambda: httpx.get(f"{HA_URL}/api/onboarding", timeout=5).status_code == 200,
        timeout=120,
        message="Home Assistant onboarding API",
    )
    response = httpx.post(
        f"{HA_URL}/api/onboarding/users",
        json={
            "client_id": CLIENT_ID,
            "name": "E2E",
            "username": HA_USERNAME,
            "password": HA_PASSWORD,
            "language": "en",
        },
        timeout=30,
    )
    response.raise_for_status()
    auth_code = response.json()["auth_code"]

    response = httpx.post(
        f"{HA_URL}/auth/token",
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": CLIENT_ID,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def ha(stack: None) -> Iterator[HomeAssistant]:  # noqa: ARG001
    token = _onboard()
    with httpx.Client(
        base_url=HA_URL,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    ) as client:
        yield HomeAssistant(client)


@dataclass
class Portal:
    """Client for the fake portal's control API."""

    http: httpx.Client

    def reset(self) -> None:
        self.http.post("/_control/reset").raise_for_status()

    def override(self, page: str, **override: Any) -> None:
        self.http.post(f"/_control/pages/{page}", json=override).raise_for_status()

    def requests(self) -> list[str]:
        response = self.http.get("/_control/requests")
        response.raise_for_status()
        return response.json()


@pytest.fixture(scope="session")
def _portal_client(stack: None) -> Iterator[Portal]:  # noqa: ARG001
    with httpx.Client(base_url=PORTAL_URL, timeout=10) as client:
        yield Portal(client)


@pytest.fixture
def portal(_portal_client: Portal) -> Iterator[Portal]:
    """Fake portal, reset to the unmodified sample pages for each test."""
    _portal_client.reset()
    yield _portal_client
    _portal_client.reset()


@pytest.fixture
def entry(ha: HomeAssistant, portal: Portal) -> Iterator[dict[str, Any]]:  # noqa: ARG001
    """Set up the integration through the UI config flow, remove it afterwards."""
    flow = ha.start_flow()
    result = ha.submit_flow(
        flow["flow_id"],
        {"host": PORTAL_HOST_FOR_HA},
    )
    assert result["type"] == "create_entry", result
    entry = result["result"]

    wait_for(
        lambda: [
            s for s in ha.servicewelt_states().values() if s["state"] != "unavailable"
        ],
        timeout=30,
        message="servicewelt entities to appear",
    )

    yield entry

    for existing in ha.config_entries():
        ha.delete_entry(existing["entry_id"])
