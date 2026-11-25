import asyncio
import json
import logging
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class MCPProtocolClient:
    """MCP TCP client using JSON-RPC 2.0 over newline-delimited frames."""

    def __init__(self, host: str | None = None, port: int | None = None):
        self.host = host or settings.MCP_SERVER_HOST
        self.port = int(port or settings.MCP_SERVER_PORT)
        self._request_id = 0
        self._io_lock = asyncio.Lock()
        self._initialized = False
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def start(self):
        if self._writer is not None and not self._writer.is_closing() and self._reader is not None:
            return

        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=settings.MCP_CONNECT_TIMEOUT_SEC,
        )
        self._initialized = False

    async def stop(self):
        if self._writer is not None:
            self._writer.close()
            await self._writer.wait_closed()
        self._reader = None
        self._writer = None
        self._initialized = False

    async def _send_request(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        async with self._io_lock:
            await self.start()
            assert self._writer is not None
            assert self._reader is not None

            self._request_id += 1
            rid = self._request_id
            payload = {
                "jsonrpc": "2.0",
                "id": rid,
                "method": method,
                "params": params or {},
            }
            self._writer.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
            await self._writer.drain()

            raw = await asyncio.wait_for(
                self._reader.readline(),
                timeout=settings.MCP_REQUEST_TIMEOUT_SEC,
            )
            if not raw:
                raise RuntimeError("MCP server disconnected")

            msg = json.loads(raw.decode("utf-8", errors="ignore"))
            if msg.get("id") != rid:
                raise RuntimeError(f"MCP response id mismatch: expected {rid}, got {msg.get('id')}")
            if "error" in msg:
                raise RuntimeError(f"MCP error: {msg['error']}")
            return msg.get("result") or {}

    async def initialize(self):
        if self._initialized:
            return
        await self.start()
        await self._send_request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "kylin-ops-backend", "version": "1.0.0"},
            },
        )
        self._initialized = True

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        result = await self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": arguments,
            },
        )
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured

        content = result.get("content") or []
        if content and isinstance(content[0], dict) and isinstance(content[0].get("text"), str):
            try:
                return json.loads(content[0]["text"])
            except Exception:
                pass
        return {
            "status": "error",
            "message": "MCP tools/call returned unexpected payload",
        }


_default_client: Optional[MCPProtocolClient] = None
_default_client_lock = asyncio.Lock()


async def get_default_mcp_client() -> MCPProtocolClient:
    global _default_client
    async with _default_client_lock:
        if _default_client is None:
            _default_client = MCPProtocolClient()
        await _default_client.start()
        await _default_client.initialize()
        return _default_client
