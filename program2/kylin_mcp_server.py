"""
麒麟运维 MCP 标准服务器
基于 Anthropic MCP 官方协议，将 KylinMCP 工具注册表暴露为标准 MCP 服务。

启动方式（stdio 模式，供 MCP 客户端/LangChain/Claude Desktop 接入）：
    python kylin_mcp_server.py

外部客户端可通过标准 MCP 协议调用所有运维工具。
orchestrator.py 内部仍直接使用 KylinMCP 类，本文件仅对外暴露协议层。
"""

import asyncio
import json
import sys
import os

# 把 program2 根目录加入 path，使 app.services 可以导入
sys.path.insert(0, os.path.dirname(__file__))

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from app.services.mcp_tools import KylinMCP, MCP_TOOLS_REGISTRY

# ============================================================
# 初始化 MCP Server
# ============================================================
server = Server("kylin-ops-mcp")


# ============================================================
# list_tools：向客户端暴露工具清单
# ============================================================
@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """返回所有注册工具的元数据，客户端据此知道能调用什么。"""
    tools = []
    for tool_name, config in MCP_TOOLS_REGISTRY.items():
        # 根据工具类型生成 inputSchema
        properties = {}
        required = []

        tool_type = config.get("type", "")

        # path 参数（大多数工具都有）
        if "{path}" in config.get("cmd", ""):
            properties["path"] = {
                "type": "string",
                "description": "目标文件或目录的绝对路径",
            }
            required.append("path")

        # content 参数（写入类工具）
        if config.get("requires_content"):
            properties["content"] = {
                "type": "string",
                "description": "要写入的内容",
            }
            required.append("content")

        # action 参数（服务/用户/包管理类）
        allowed_actions = config.get("allowed_actions")
        if allowed_actions:
            properties["action"] = {
                "type": "string",
                "enum": allowed_actions,
                "description": f"操作类型，可选：{', '.join(allowed_actions)}",
            }
            required.append("action")

        # 服务名称
        if "service" in tool_type:
            properties["service_name"] = {
                "type": "string",
                "description": "systemctl 服务名称，如 nginx、sshd",
            }
            required.append("service_name")

        # 用户管理
        if tool_name == "user_manage":
            properties["username"] = {"type": "string", "description": "用户名"}
            required.append("username")
            properties["group"] = {"type": "string", "description": "目标组名（mod 操作时必填）"}

        # 包管理
        if tool_name == "package_manage":
            properties["package"] = {"type": "string", "description": "软件包名称"}
            required.append("package")

        # 进程信号
        if tool_name == "manage_process_signal":
            properties["signal"] = {
                "type": "string",
                "enum": config.get("allowed_signals", ["TERM", "KILL", "HUP", "INT"]),
                "description": "信号类型",
            }
            properties["pid"] = {"type": "integer", "description": "目标进程 PID"}
            required.extend(["signal", "pid"])

        # 权限变更
        if tool_name == "change_permissions":
            properties["mode"] = {"type": "string", "description": "权限模式，如 755、644"}
            properties["recursive"] = {"type": "boolean", "description": "是否递归"}
            required.append("mode")

        # 所有者变更
        if tool_name == "change_owner":
            properties["user"] = {"type": "string", "description": "目标用户名"}
            properties["group"] = {"type": "string", "description": "目标组名"}
            properties["recursive"] = {"type": "boolean", "description": "是否递归"}
            required.extend(["user", "group"])

        # 防火墙
        if tool_name == "firewall_modify":
            properties["chain"] = {"type": "string", "description": "规则链，如 INPUT、OUTPUT"}
            properties["rule"] = {"type": "string", "description": "iptables 规则"}
            properties["action"] = {"type": "string", "enum": ["add", "delete"]}
            required.extend(["chain", "rule", "action"])

        # 日志行数
        if tool_name == "show_system_log":
            properties["lines"] = {
                "type": "integer",
                "description": "显示最后 N 行，默认 100",
                "default": 100,
            }

        # 进程优先级
        if tool_name == "manage_process_priority":
            properties["priority"] = {"type": "integer", "description": "nice 值，-20 到 19"}
            properties["pid"] = {"type": "integer", "description": "目标进程 PID"}
            required.extend(["priority", "pid"])

        # src/dst 类工具（复制、移动、备份）
        if tool_name in ("copy_file", "move_rename", "snapshot_backup", "snapshot_restore"):
            properties["src"] = {"type": "string", "description": "源路径"}
            properties["dst"] = {"type": "string", "description": "目标路径"}
            if "path" in required:
                required.remove("path")
            required.extend(["src", "dst"])
            properties.pop("path", None)

        # 归档备份
        if tool_name == "archive_backup":
            properties["archive_name"] = {"type": "string", "description": "归档文件名，如 backup.tar.gz"}
            required.extend(["archive_name"])

        tools.append(
            types.Tool(
                name=tool_name,
                description=(
                    f"[风险等级: {config['level']}] "
                    f"{'⚠️ 需要 root ' if config.get('need_root') else ''}"
                    f"{config['reason']}"
                ),
                inputSchema={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            )
        )
    return tools


# ============================================================
# call_tool：执行具体工具
# ============================================================
@server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent]:
    """接收客户端工具调用请求，路由到 KylinMCP 执行。"""

    if name not in MCP_TOOLS_REGISTRY:
        return [
            types.TextContent(
                type="text",
                text=json.dumps(
                    {"status": "error", "message": f"工具 {name} 不存在"},
                    ensure_ascii=False,
                ),
            )
        ]

    # 高风险操作通过 MCP 协议调用时，默认要求已确认（由客户端/用户侧负责）
    arguments["_confirmed"] = arguments.pop("confirmed", True)

    result = await KylinMCP.call(name, **arguments)

    return [
        types.TextContent(
            type="text",
            text=json.dumps(result, ensure_ascii=False, indent=2),
        )
    ]


# ============================================================
# 启动入口
# ============================================================
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
