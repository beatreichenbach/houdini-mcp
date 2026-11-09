from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, cast

import httpx

from houdini_mcp_protocol import (
    PLUGIN_COMMANDS,
    PROTOCOL_VERSION,
    ApiCommand,
    ErrorCode,
    Request,
    Response,
    ResponseStatus,
    request_headers,
)

from .config import Settings
from .errors import HoudiniCommandError, HoudiniConnectionError

logger = logging.getLogger(__name__)

PORT_SEARCH_RANGE = 16


class HoudiniBridge:
    def __init__(self, settings: Settings) -> None:
        self._host = settings.host
        self._port = settings.port
        self._timeout = settings.timeout
        self._client = httpx.AsyncClient(timeout=self._timeout)

    @property
    def base_url(self) -> str:
        return f'http://{self._host}:{self._port}'

    @property
    def api_url(self) -> str:
        return f'{self.base_url}/api'

    async def discover(self) -> None:
        """Find and connect to a running Houdini plugin."""

        servers = await find_servers(self._host, self._port)
        if not servers:
            logger.warning(
                'No Houdini plugin found on ports %d-%d',
                self._port,
                self._port + PORT_SEARCH_RANGE - 1,
            )
            return
        server = servers[0]
        self._port = int(server['port'])
        logger.info(
            'Connected to Houdini %s on port %d',
            server.get('houdini_version', 'unknown'),
            self._port,
        )
        if len(servers) > 1:
            logger.warning(
                '%d Houdini sessions found; using port %d',
                len(servers),
                self._port,
            )

        protocol_version = server.get('protocol_version')
        if protocol_version != PROTOCOL_VERSION:
            logger.warning(
                'Plugin protocol version %s does not match server %s',
                protocol_version,
                PROTOCOL_VERSION,
            )

        commands = set(await self.list_commands())
        missing = PLUGIN_COMMANDS - commands
        if missing:
            logger.warning('Plugin is missing commands: %s', ', '.join(sorted(missing)))

    async def health_check(self) -> dict[str, Any]:
        """Return the plugin health payload."""

        return await self._post(ApiCommand.HEALTH, {})

    async def list_commands(self) -> list[str]:
        """Return the commands registered by the plugin."""

        payload = await self._post(ApiCommand.LIST_COMMANDS, {})
        commands = payload.get('commands')
        if not isinstance(commands, list):
            return []
        return [str(command) for command in commands]

    async def execute(
        self,
        command: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:  # noqa: ANN401
        """Run a command in Houdini and return its result."""

        logger.debug('Calling Houdini command %s', command)
        request = Request(command=command, params=params or {})
        payload = await self._post(
            ApiCommand.EXECUTE, request.to_payload(), timeout=timeout
        )
        response = Response.from_payload(payload)
        if response.status is ResponseStatus.ERROR:
            error = response.error or {}
            raise HoudiniCommandError(
                message=str(error.get('message', 'unknown houdini error')),
                code=str(error.get('code', ErrorCode.COMMAND_ERROR)),
                details=error,
            )
        return response.data

    async def close(self) -> None:
        """Close the HTTP client."""

        await self._client.aclose()

    async def _post(
        self,
        endpoint: str,
        params: dict[str, Any],
        timeout: float | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.post(
                self.api_url,
                data=_rpc_body(endpoint, params),
                headers=request_headers(),
                timeout=timeout or self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HoudiniConnectionError(
                f'houdini returned HTTP {exc.response.status_code}'
            ) from exc
        except httpx.TimeoutException as exc:
            raise HoudiniConnectionError(
                f'houdini request timed out after {timeout or self._timeout}s'
            ) from exc
        except httpx.TransportError as exc:
            raise HoudiniConnectionError(
                f'cannot reach houdini at {self.base_url} ({type(exc).__name__})'
            ) from exc
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise HoudiniConnectionError('houdini returned invalid JSON') from exc
        if not isinstance(payload, dict):
            raise HoudiniConnectionError(
                f'unexpected houdini response type: {type(payload).__name__}'
            )
        return cast(dict[str, Any], payload)


def _rpc_body(endpoint: str, params: dict[str, Any]) -> dict[str, str]:
    """
    Build the form body hwebserver expects for an API function call.

    hwebserver reads ``json=["namespace.function", [args], {keywords}]`` from a
    form field rather than a JSON request body.
    """

    return {'json': json.dumps([endpoint, [], params])}


async def find_servers(
    host: str,
    base_port: int,
    max_tries: int = PORT_SEARCH_RANGE,
    timeout: float = 1.0,
) -> list[dict[str, Any]]:
    """
    Probe a port range for live Houdini plugins.

    A second Houdini session moves itself to the next free port, so the server
    scans the range instead of assuming the configured port.
    """

    async def probe(client: httpx.AsyncClient, port: int) -> dict[str, Any] | None:
        try:
            response = await client.post(
                f'http://{host}:{port}/api',
                data=_rpc_body(ApiCommand.HEALTH, {}),
                headers=request_headers(),
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError):
            return None
        if isinstance(payload, dict) and payload.get('status') == 'ok':
            return {**cast(dict[str, Any], payload), 'port': port}
        return None

    async with httpx.AsyncClient(timeout=timeout) as client:
        results = await asyncio.gather(
            *(probe(client, port) for port in range(base_port, base_port + max_tries))
        )
    return [result for result in results if result is not None]


_bridge: HoudiniBridge | None = None


def set_bridge(bridge: HoudiniBridge | None) -> None:
    """Set the process bridge, or clear it when the server stops."""

    global _bridge
    _bridge = bridge


def current_bridge() -> HoudiniBridge:
    """Return the process bridge for callers without a request context."""

    if _bridge is None:
        raise RuntimeError('no Houdini bridge; the server has not started')
    return _bridge
