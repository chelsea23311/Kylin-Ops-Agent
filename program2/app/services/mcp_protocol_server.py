import asyncio
import json
import logging
from typing import Any, Dict

from app.core.config import settings
from app.services.mcp_tools import KylinMCP, MCP_TOOLS_REGISTRY

logger = logging.getLogger(__name__)


def _jsonrpc_result(rid: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def _jsonrpc_error(rid: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": rid, "error": err}


def _tool_schema(name: str) -> Dict[str, Any]:
    cfg = MCP_TOOLS_REGISTRY.get(name, {})
    required = KylinMCP.get_required_args_for_tool(name)
    allowed = KylinMCP.get_allowed_args_for_tool(name)
    properties = {a: {"type": "string"} for a in allowed}
    return {
        "name": name,
        "description": cfg.get("reason", ""),
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": True,
        },
    }


async def _handle(req: Dict[str, Any]) -> Dict[str, Any]:
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    if method == "initialize":
        return _jsonrpc_result(
            rid,
            {
                "protocolVersion": "2025-03-26",
                "serverInfo": {"name": "kylin-mcp-server", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        )

    if method == "tools/list":
        tools = [_tool_schema(n) for n in MCP_TOOLS_REGISTRY.keys()]
        return _jsonrpc_result(rid, {"tools": tools})

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        if not tool_name:
            return _jsonrpc_error(rid, -32602, "Missing tool name")

        try:
            result = await KylinMCP.call_local(str(tool_name), **arguments)
            return _jsonrpc_result(
                rid,
                {
                    "isError": result.get("status") != "success",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False),
                        }
                    ],
                    "structuredContent": result,
                },
            )
        except Exception as e:
            return _jsonrpc_error(rid, -32000, "Tool execution failed", str(e))

    return _jsonrpc_error(rid, -32601, f"Method not found: {method}")


async def _client_loop(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info("peername")
    logger.info("MCP client connected: %s", peer)
    try:
        while True:
            raw = await reader.readline()
            if not raw:
                break
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            try:
                req = json.loads(line)
            except Exception as e:
                resp = _jsonrpc_error(None, -32700, "Parse error", str(e))
                writer.write((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
                await writer.drain()
                continue

            try:
                resp = await _handle(req)
            except Exception as e:
                resp = _jsonrpc_error(req.get("id"), -32000, "Internal error", str(e))

            writer.write((json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8"))
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()
        logger.info("MCP client disconnected: %s", peer)


async def run_server(host: str, port: int):
    server = await asyncio.start_server(_client_loop, host=host, port=port)
    logger.info("MCP TCP server listening on %s:%s", host, port)
    async with server:
        await server.serve_forever()


def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server(settings.MCP_SERVER_HOST, settings.MCP_SERVER_PORT))


if __name__ == "__main__":
    main()
