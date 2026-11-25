# app/services/mcp_tools.py
import subprocess
import shlex
import logging
import hashlib
import os
import signal
from datetime import datetime
from typing import Dict, Any, List, Optional

# 配置日志，方便调试
logger = logging.getLogger(__name__)

# ==================== 完整工具配置表 (声明式配置，单一真相源) ====================
MCP_TOOLS_REGISTRY: Dict[str, Dict[str, Any]] = {
    # ==================== 只读类 (Level 0.0) ====================
    "read_file": {
        "cmd": "cat {path}",
        "level": 0.0,
        "reason": "只读行为，查看内容无写入风险，适合审计查看意图。",
        "type": "file_reader",
        "supports_partial": True,
        "need_root": 0,
    },
    "list_dir": {
        "cmd": "ls -la --color=auto {path}",
        "level": 0.0,
        "reason": "目录/文件清单读取，无破坏性，常用于盘点与定位。",
        "type": "file_reader",
        "need_root": 0,
    },
    "network_config_show": {
        "cmd": "ip addr show",
        "level": 0.0,
        "reason": "查看网络状态只读，安全且用于审计与排障。",
        "type": "network_reader",
        "need_root": 0,
    },
    "show_service_status": {
        "cmd": "systemctl status {service_name}",
        "level": 0.0,
        "reason": "查看服务当前运行状态，无破坏性，用于审计和故障排查。",
        "type": "service_reader",
        "need_root": 0,
    },
    "show_system_log": {
        "cmd": "journalctl -xe | tail -n {lines}",
        "level": 0.0,
        "reason": "读取系统或服务日志，无写入操作，用于排障与状态确认。",
        "type": "log_reader",
        "default_lines": 100,
        "need_root": 0,
    },
    "list_process": {
        "cmd": "ps aux",
        "level": 0.0,
        "reason": "查看运行进程及资源占用，纯只读操作，评估资源瓶颈时必备。",
        "type": "process_reader",
        "need_root": 0,
    },
    "list_disk": {
        "cmd": "lsblk",
        "level": 0.0,
        "reason": "仅查看物理磁盘与分区表结构，纯读取动作，无风险。",
        "type": "disk_reader",
        "need_root": 0,
    },
    "disk_usage": {
        "cmd": "df -h",
        "level": 0.0,
        "reason": "查看所有挂载点的容量、已用空间和使用率，定位空间不足的文件系统。",
        "type": "disk_reader",
        "need_root": 0,
    },
    "directory_usage": {
        "cmd": "du -x -h --max-depth=1 -- {path} | sort -hr",
        "level": 0.0,
        "reason": "统计指定文件系统内一级目录的实际磁盘占用，按大小降序定位热点目录。",
        "type": "disk_reader",
        "need_root": 0,
    },
    "find_large_files": {
        "cmd": "find {path} -xdev -type f -size +100M -printf '%s\\t%p\\n' | sort -nr | sed -n '1,30p'",
        "level": 0.0,
        "reason": "只读查找同一文件系统内超过 100 MiB 的大文件，列出最大的 30 项及字节大小。",
        "type": "disk_reader",
        "need_root": 0,
    },
    "list_open_files": {
        "cmd": "lsof -i",
        "level": 0.0,
        "reason": "查看哪些进程打开了哪些文件，只读操作。",
        "type": "process_reader",
        "need_root": 1,          # 需要 root 才能看到所有进程的打开文件
    },
    "show_network_connections": {
        "cmd": "ss -tunlp",
        "level": 0.0,
        "reason": "查看端口监听和连接，只读操作。",
        "type": "network_reader",
        "need_root": 0,
    },

    # ==================== 低风险类 (Level 0.1 - 0.2) ====================
    "create_file": {
        "cmd": "touch {path}",
        "level": 0.1,
        "reason": "创建空文件或占位文件，低风险但改变文件系统状态。",
        "type": "file_writer",
        "need_root": 0,
    },
    "append_file": {
        "cmd": ">> {path}",
        "level": 0.2,
        "reason": "追加通常是维护性操作，低至中等风险（日志污染/配置重复）。",
        "type": "file_writer",
        "requires_content": True,
        "need_root": 0,
    },
    "copy_file": {
        "cmd": "cp -a {src} {dst}",
        "level": 0.2,
        "reason": "复制为数据备份或部署，通常为低风险，但可能泄露敏感数据。",
        "type": "file_operator",
        "need_root": 0,
    },
    "manage_process_priority": {
        "cmd": "renice {priority} {pid}",
        "level": 0.2,
        "reason": "调整优先级为性能调优，通常低风险但影响调度。",
        "type": "process_operator",
        "need_root": 1,          # renice 修改其他用户进程需要 root
    },
    "snapshot_backup": {
        "cmd": "rsync -a --delete {src} {dst}",
        "level": 0.1,
        "reason": "创建快照/备份为保护性操作，低风险且为恢复保障，应鼓励。",
        "type": "backup",
        "need_root": 1,          # rsync 备份系统文件可能需要 root
    },
    "archive_backup": {
        "cmd": "tar -czvf {archive_name} {path}",
        "level": 0.1,
        "reason": "将已有文件打包归档或执行第三方备份，操作行为只读，风险极低。",
        "type": "backup",
        "need_root": 1,
    },

    # ==================== 中等风险类 (Level 0.4 - 0.5) ====================
    "system_update": {
        "cmd": "apt-get update && apt-get upgrade -y",
        "level": 0.4,
        "reason": "系统升级涉及包变动与重启风险，中等破坏性，需评估兼容性。",
        "type": "system_operator",
        "need_root": 1,
    },
    "manage_logrotate": {
        "cmd": "logrotate -f {config_file}",
        "level": 0.4,
        "reason": "强制日志轮转可能导致当前的排障日志或审计记录被提早归档。",
        "type": "log_operator",
        "need_root": 1,
    },
    "move_rename": {
        "cmd": "mv {src} {dst}",
        "level": 0.5,
        "reason": "移动/重命名可能导致服务失效或数据位置变化，中高风险。",
        "type": "file_operator",
        "need_root": 0,
    },
    "manage_service_control": {
        "cmd": "systemctl {action} {service_name}",
        "level": 0.5,
        "reason": "服务启停控制，影响服务可用性，中等风险。",
        "type": "service_operator",
        "allowed_actions": ["start", "stop", "restart", "reload", "status"],
        "need_root": 1,
    },
    "manage_service_enable": {
        "cmd": "systemctl {action} {service_name}",
        "level": 0.5,
        "reason": "设置服务开机自启状态，影响服务持久化，中等风险。",
        "type": "service_operator",
        "allowed_actions": ["enable", "disable"],
        "need_root": 1,
    },
    "user_manage": {
        "cmd": "user{action} {username}",
        "level": 0.5,
        "reason": "用户/组管理影响权限与审计，错误操作可导致账号丢失或权限泄露。",
        "type": "user_operator",
        "allowed_actions": ["add", "del", "mod"],
        "need_root": 1,
    },
    "write_file_overwrite": {
        "cmd": "> {path}",
        "level": 0.6,
        "reason": "覆盖现有文件可能破坏配置或数据，需谨慎审计。",
        "type": "file_writer",
        "requires_content": True,
        "need_root": 0,
    },
    "change_permissions": {
        "cmd": "chmod {mode} {path}",
        "level": 0.6,
        "reason": "权限变更可提升/降低访问，可能造成安全漏洞或中断服务。",
        "type": "security_operator",
        "need_root": 1,
    },
    "package_manage": {
        "cmd": "apt-get {action} -y {package}",
        "level": 0.6,
        "reason": "安装/卸载软件影响系统组成，可能带入风险或移除依赖，需审核来源。",
        "type": "package_operator",
        "allowed_actions": ["install", "remove", "purge"],
        "need_root": 1,
    },
    "manage_cron": {
        "cmd": "crontab {action}",
        "level": 0.6,
        "reason": "新增或修改定时任务可引入后台自动运行脚本，有较高的隐藏执行风险。",
        "type": "scheduler_operator",
        "allowed_actions": ["list", "edit", "remove"],
        "need_root": 0,          # crontab 操作通常以用户身份执行，不需要 root
    },

    # ==================== 高风险类 (Level 0.7 - 0.9) ====================
    "truncate_file": {
        "cmd": "truncate -s 0 {path}",
        "level": 0.7,
        "reason": "清空文件会丢失数据（与delete不同可恢复性更差），高风险。",
        "type": "file_writer",
        "need_root": 0,
    },
    "change_owner": {
        "cmd": "chown {user}:{group} {path}",
        "level": 0.7,
        "reason": "所有权变更影响访问控制，错误设置可能导致服务不可用或权限泄露。",
        "type": "security_operator",
        "need_root": 1,
    },
    "mount_unmount": {
        "cmd": "mount {device} {mount_point}",
        "level": 0.7,
        "reason": "挂载/卸载影响数据可见性和服务访问，错误操作可造成数据损坏。",
        "type": "filesystem_operator",
        "need_root": 1,
    },
    "manage_process_signal": {
        "cmd": "kill -{signal} {pid}",
        "level": 0.8,
        "reason": "发送信号可终止进程，SIGKILL为破坏性强的紧急操作。",
        "type": "process_operator",
        "allowed_signals": ["TERM", "KILL", "HUP", "INT"],
        "need_root": 0,          # kill 自己的进程不需要 root，杀其他用户进程需要，但这里不强制
    },
    "network_config_set": {
        "cmd": "ip addr add {ip}/{mask} dev {interface}",
        "level": 0.8,
        "reason": "改变IP/路由影响连通性，可能导致网络中断或暴露服务。",
        "type": "network_operator",
        "need_root": 1,
    },
    "firewall_modify": {
        "cmd": "iptables -A {chain} {rule}",
        "level": 0.8,
        "reason": "修改防火墙规则直接影响访问控制，错误配置有高安全与可用性风险。",
        "type": "security_operator",
        "need_root": 1,
    },
    "manage_raid": {
        "cmd": "mdadm --manage {device}",
        "level": 0.8,
        "reason": "编辑或破坏软RAID阵列配置可能直接导致底层的数据彻底损坏。",
        "type": "storage_operator",
        "need_root": 1,
    },
    "snapshot_restore": {
        "cmd": "rsync -a {src} {dst}",
        "level": 0.9,
        "reason": "恢复可能覆盖现有数据与状态，具有高风险但为必要恢复手段。",
        "type": "backup",
        "need_root": 1,
    },
    "manage_lvm_remove": {
        "cmd": "lvremove -y {lv_path}",
        "level": 0.9,
        "reason": "移除逻辑卷会直接销毁设备上的文件系统与数据，属于高危操作。",
        "type": "storage_operator",
        "need_root": 1,
    },

    # ==================== 最高风险类 (Level 1.0) ====================
    "delete_file": {
        "cmd": "rm -rf {path}",
        "level": 1.0,
        "reason": "直接删除数据或目录为最高破坏性操作，需严格控制与审计。",
        "type": "file_operator",
        "need_root": 0,
    },
    "disk_format_partition": {
        "cmd": "mkfs.ext4 {device}",
        "level": 1.0,
        "reason": "格式化/分区会擦除或重构数据，属于高破坏性操作，必须严控。",
        "type": "storage_operator",
        "need_root": 1,
    },
}


# ==================== 响应封装类 ====================
class MCPResponse:
    """MCP 工具调用响应封装"""

    @staticmethod
    def for_ml(result: dict) -> dict:
        """
        给 ML/AI Agent 的响应格式
        结构化、包含元数据、便于 AI 决策
        """
        return {
            "success": result["status"] == "success",
            "data": result.get("output") if result["status"] == "success" else None,
            "error": result.get("message") if result["status"] != "success" else None,
            "metadata": {
                "tool_level": result.get("level"),
                "requires_confirmation": result.get("requires_confirmation", False),
                "need_root": result.get("need_root", False),
                "executed_command": result.get("command"),
                "reason": result.get("reason"),
            }
        }

    @staticmethod
    def for_frontend(result: dict, user_friendly: bool = True) -> dict:
        """
        给前端 UI 的响应格式
        """
        if result["status"] == "need_confirmation":
            return {
                "code": "NEED_CONFIRMATION",
                "message": result["message"],
                "data": {
                    "operation": "高风险操作需要确认",
                    "risk_level": result.get("level"),
                    "risk_description": result.get("reason"),
                    "need_root": result.get("need_root", False),
                }
            }

        if result["status"] == "success":
            # 前端展示时截断过长的输出
            output = result.get("output", "")
            if len(output) > 5000:
                output = output[:5000] + "\n... (输出过长，已截断)"

            return {
                "code": "SUCCESS",
                "message": "操作执行成功",
                "data": {
                    "output": output,
                    "risk_level": result.get("level"),
                    "need_root": result.get("need_root", False),
                }
            }

        # 错误响应
        return {
            "code": "ERROR",
            "message": result.get("message", "操作执行失败"),
            "data": {
                "risk_level": result.get("level"),
                "need_root": result.get("need_root", False),
            }
        }

    @staticmethod
    def for_audit_log(result: dict, user_id: str, session_id: str) -> dict:
        """
        给审计日志的响应格式
        完整记录、不可抵赖、包含所有细节
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "session_id": session_id,
            "tool_name": result.get("_tool_name"),
            "command": result.get("command"),
            "status": result["status"],
            "risk_level": result.get("level"),
            "need_root": result.get("need_root", False),
            "output_hash": hashlib.sha256(
                (result.get("output") or "").encode()
            ).hexdigest() if result.get("output") else None,
            "error_message": result.get("message") if result["status"] != "success" else None,
            "execution_time_ms": result.get("_execution_time_ms"),
        }


# ==================== MCP 核心类 ====================
class KylinMCP:
    @staticmethod
    def _extract_placeholders(cmd: str) -> List[str]:
        import re
        return re.findall(r"\{(\w+)\}", cmd or "")

    @staticmethod
    def get_allowed_args_for_tool(tool_name: str) -> List[str]:
        """返回某个工具允许的业务参数（不含以下划线开头的系统参数）。"""
        tool_config = MCP_TOOLS_REGISTRY.get(tool_name, {})
        allowed = set(KylinMCP._extract_placeholders(tool_config.get("cmd", "")))

        # 自定义构建命令里使用到的额外参数
        extras = {
            "read_file": ["mode", "lines", "path"],
            "append_file": ["content", "path"],
            "write_file_overwrite": ["content", "path"],
            "manage_cron": ["action"],
            "manage_service_control": ["action", "service_name"],
            "manage_service_enable": ["action", "service_name"],
            "user_manage": ["action", "username", "group"],
            "package_manage": ["action", "package"],
            "manage_process_signal": ["signal", "pid"],
            "change_permissions": ["mode", "path", "recursive"],
            "change_owner": ["user", "group", "path", "recursive"],
            "firewall_modify": ["action", "chain", "rule"],
            "show_system_log": ["lines"],
        }
        allowed.update(extras.get(tool_name, []))
        return sorted(list(allowed))

    @staticmethod
    def get_required_args_for_tool(tool_name: str, **kwargs) -> List[str]:
        """返回某个工具必填参数（结合工具规则和默认值）。"""
        required_map = {
            "read_file": ["path"],
            "list_dir": ["path"],
            "directory_usage": ["path"],
            "find_large_files": ["path"],
            "create_file": ["path"],
            "append_file": ["path", "content"],
            "copy_file": ["src", "dst"],
            "snapshot_backup": ["src", "dst"],
            "snapshot_restore": ["src", "dst"],
            "archive_backup": ["archive_name", "path"],
            "show_service_status": ["service_name"],
            "manage_service_control": ["service_name"],
            "manage_service_enable": ["service_name"],
            "user_manage": ["username"],
            "write_file_overwrite": ["path", "content"],
            "change_permissions": ["path"],
            "package_manage": ["package"],
            "truncate_file": ["path"],
            "change_owner": ["user", "group", "path"],
            "mount_unmount": ["device", "mount_point"],
            "manage_process_signal": ["pid"],
            "network_config_set": ["ip", "mask", "interface"],
            "firewall_modify": ["rule"],
            "manage_raid": ["device"],
            "manage_lvm_remove": ["lv_path"],
            "delete_file": ["path"],
            "disk_format_partition": ["device"],
        }
        required = list(required_map.get(tool_name, []))

        # 条件必填：user_manage 的 mod 需要 group
        if tool_name == "user_manage" and kwargs.get("action") == "mod" and "group" not in required:
            required.append("group")

        return required

    @staticmethod
    async def call_local(tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        本地执行入口（供 MCP Server 调用）。
        """
        tool_config = MCP_TOOLS_REGISTRY.get(tool_name)
        if not tool_config:
            logger.error(f"工具 {tool_name} 不在注册表中")
            return {"status": "error", "message": f"Tool {tool_name} not found"}

        try:
            # 1. 预检
            validation = KylinMCP.validate_operation(tool_name, **kwargs)
            if not validation["valid"]:
                return {
                    "status": "error",
                    "message": validation["message"],
                    "level": tool_config["level"],
                    "requires_confirmation": validation["need_confirmation"],
                    "need_root": tool_config.get("need_root", 0),
                }

            # 2. 二次确认检查
            if validation["need_confirmation"] and not kwargs.get("_confirmed", False):
                return {
                    "status": "need_confirmation",
                    "message": f"高风险操作 [{tool_name}] 需要二次确认。",
                    "level": tool_config["level"],
                    "reason": tool_config["reason"],
                    "requires_confirmation": True,
                    "need_root": tool_config.get("need_root", 0),
                }

            # 3. 组装命令
            raw_cmd = KylinMCP._build_command(tool_name, **kwargs)
            if not raw_cmd:
                return {"status": "error", "message": f"无法组装命令: {tool_name}"}

            exec_cmd = raw_cmd
            need_root_exec = bool(kwargs.get("_need_root", False) or tool_config.get("need_root", 0))
            if need_root_exec and os.geteuid() != 0:
                # 非交互提权：依赖 sudoers 配置（NOPASSWD）。
                exec_cmd = f"sudo -n {raw_cmd}"
            
            timeout_val = kwargs.get("_timeout", 30)

            # 4. 【关键修改】执行异步子进程
            import asyncio
            process = await asyncio.create_subprocess_shell(
                exec_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                start_new_session=True,
            )

            try:
                # 等待命令执行结果
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_val)
            except asyncio.TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    await process.communicate()
                except ProcessLookupError:
                    pass
                return {"status": "error", "message": "Command execution timeout", "level": tool_config["level"]}

            # 解码函数保持不变
            def smart_decode(data: bytes) -> str:
                if not data: return ""
                try:
                    return data.decode('utf-8').strip()
                except UnicodeDecodeError:
                    return data.decode('gbk', errors='ignore').strip()

            stdout_str = smart_decode(stdout)
            stderr_str = smart_decode(stderr)

            if process.returncode == 0:
                return {
                    "status": "success",
                    "output": stdout_str,
                    "level": tool_config["level"],
                    "reason": tool_config["reason"],
                    "command": exec_cmd,
                    "requires_confirmation": validation["need_confirmation"],
                    "need_root": need_root_exec,
                }
            else:
                return {
                    "status": "error",
                    "message": stderr_str if stderr_str else f"Exit code: {process.returncode}",
                    "output": (stdout_str + "\n统计未完成：" + stderr_str).strip() if tool_name in {"directory_usage", "find_large_files"} else "",
                    "level": tool_config["level"],
                    "command": exec_cmd,
                    "requires_confirmation": validation["need_confirmation"],
                    "need_root": need_root_exec,
                }

        except Exception as e:
            logger.exception(f"执行工具 {tool_name} 出错")
            return {"status": "error", "message": str(e), "level": tool_config["level"]}

    @staticmethod
    async def call(tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        统一执行入口：优先走标准 MCP Client/Server 协议，失败时回退本地执行。
        """
        # 允许显式绕过 MCP（例如单元测试或排障）
        if kwargs.get("_local_only", False):
            return await KylinMCP.call_local(tool_name, **kwargs)

        try:
            from app.services.mcp_protocol_client import get_default_mcp_client

            client = await get_default_mcp_client()
            result = await client.call_tool(tool_name, kwargs)
            if isinstance(result, dict) and result.get("status"):
                return result
            logger.warning("MCP tools/call 返回结构异常，回退本地执行")
        except Exception as e:
            logger.warning(f"MCP 客户端调用失败，回退本地执行: {e}")

        return await KylinMCP.call_local(tool_name, **kwargs)
    # @staticmethod
    # def call(tool_name: str, **kwargs) -> Dict[str, Any]:
    #     """
    #     统一工具调用入口

    #     Args:
    #         tool_name: 工具名称（必须在 MCP_TOOLS_REGISTRY 中）
    #         **kwargs: 命令参数，支持特殊参数：
    #             - _confirmed: bool, 是否已确认（绕过二次确认）
    #             - _timeout: int, 超时时间（秒）
    #             - _user_id: str, 用户ID（用于审计）
    #             - _session_id: str, 会话ID（用于审计）

    #     Returns:
    #         dict: {"status": "success/error/need_confirmation", "output/message": str,
    #                "level": float, "reason": str, "command": str, "requires_confirmation": bool,
    #                "need_root": bool}
    #     """
    #     tool_config = MCP_TOOLS_REGISTRY.get(tool_name)
    #     if not tool_config:
    #         logger.error(f"工具 {tool_name} 不在注册表中")
    #         return {"status": "error", "message": f"Tool {tool_name} not found"}

    #     try:
    #         # 1. 预检操作（参数验证 + 路径安全检查 + root权限检查）
    #         validation = KylinMCP.validate_operation(tool_name, **kwargs)
    #         if not validation["valid"]:
    #             return {
    #                 "status": "error",
    #                 "message": validation["message"],
    #                 "level": tool_config["level"],
    #                 "requires_confirmation": validation["need_confirmation"],
    #                 "need_root": tool_config.get("need_root", 0),
    #             }

    #         # 2. 如果需要二次确认且调用方未确认，返回等待确认状态
    #         if validation["need_confirmation"] and not kwargs.get("_confirmed", False):
    #             return {
    #                 "status": "need_confirmation",
    #                 "message": f"高风险操作 [{tool_name}] 需要二次确认。{validation['message']}",
    #                 "level": tool_config["level"],
    #                 "reason": tool_config["reason"],
    #                 "requires_confirmation": True,
    #                 "need_root": tool_config.get("need_root", 0),
    #             }

    #         # 3. 组装命令
    #         raw_cmd = KylinMCP._build_command(tool_name, **kwargs)
    #         if not raw_cmd:
    #             return {"status": "error", "message": f"无法组装命令: {tool_name}"}
    #         timeout_val = kwargs.get("_timeout", 30)

    #         # 4. 执行命令
    #         process = subprocess.run(
    #             raw_cmd,
    #             shell=True,
    #             capture_output=True,
    #             text=False,  # 先不自动转文本，拿原始字节数据
    #             timeout=timeout_val,
    #         )

    #         # 手动解码函数
    #         def smart_decode(data: bytes) -> str:
    #             if not data: return ""
    #             try:
    #                 return data.decode('gbk').strip()  # 优先尝试 Windows 默认 GBK
    #             except UnicodeDecodeError:
    #                 return data.decode('utf-8', errors='ignore').strip()  # 失败则尝试 utf-8

    #         stdout_str = smart_decode(process.stdout)
    #         stderr_str = smart_decode(process.stderr)

    #         if process.returncode == 0:
    #             return {
    #                 "status": "success",
    #                 "output": stdout_str,
    #                 "level": tool_config["level"],
    #                 "reason": tool_config["reason"],
    #                 "command": raw_cmd,
    #                 "requires_confirmation": validation["need_confirmation"],
    #                 "need_root": tool_config.get("need_root", 0),
    #             }
    #         else:
    #             return {
    #                 "status": "error",
    #                 "message": stderr_str if stderr_str else f"Exit code: {process.returncode}",
    #                 "level": tool_config["level"],
    #                 "command": raw_cmd,
    #                 "requires_confirmation": validation["need_confirmation"],
    #                 "need_root": tool_config.get("need_root", 0),
    #             }

    #     except subprocess.TimeoutExpired:
    #         logger.error(f"工具 {tool_name} 执行超时 (30s)")
    #         return {"status": "error", "message": "Command execution timeout", "level": tool_config["level"]}
    #     except Exception as e:
    #         logger.exception(f"执行工具 {tool_name} 出错")
    #         return {"status": "error", "message": str(e), "level": tool_config["level"]}

    @staticmethod
    async def call_with_response(tool_name: str, target: str = "ml", **kwargs):
        """
        统一调用入口，根据目标返回不同格式

        Args:
            tool_name: 工具名称
            target: "ml" | "frontend" | "audit"
            **kwargs: 命令参数
        """
        import time
        start_time = time.time()

        # 执行工具
        # result = KylinMCP.call(tool_name, **kwargs)
        result = await KylinMCP.call(tool_name, **kwargs)
        result["_tool_name"] = tool_name
        result["_execution_time_ms"] = int((time.time() - start_time) * 1000)

        # 根据目标返回不同格式
        if target == "ml":
            return MCPResponse.for_ml(result)
        elif target == "frontend":
            return MCPResponse.for_frontend(result)
        elif target == "audit":
            user_id = kwargs.get("_user_id", "unknown")
            session_id = kwargs.get("_session_id", "unknown")
            return MCPResponse.for_audit_log(result, user_id, session_id)
        else:
            return result  # 原始格式

    @staticmethod
    def _build_command(tool_name: str, **kwargs) -> str:
        """根据工具名和参数组装命令"""
        tool_config = MCP_TOOLS_REGISTRY.get(tool_name, {})
        base_cmd = tool_config.get("cmd", "")

        if tool_name in {"directory_usage", "find_large_files"}:
            path = kwargs.get("path")
            if not isinstance(path, str) or not os.path.isabs(path):
                return ""
            # Quote paths before shell interpolation, including spaces and metacharacters.
            return "bash -o pipefail -c " + shlex.quote(base_cmd.format(path=shlex.quote(path)))

        # ==================== 文件读取类（支持 head/tail） ====================
        if tool_name == "read_file":
            mode = kwargs.get("mode", "tail")
            lines = kwargs.get("lines", 100)
            path = kwargs.get("path", "")
            path_str = str(path or "").strip()
            if path_str in {"/var/log/redis/redis-server.log", "/var/log/redis/redis.log", "/var/log/redis.log"}:
                safe_lines = shlex.quote(str(lines))
                candidates = " ".join(shlex.quote(p) for p in [
                    "/var/log/redis/redis-server.log",
                    "/var/log/redis/redis.log",
                    "/var/log/redis.log",
                    "/var/log/redis/redis-server/redis.log",
                ])
                return (
                    "sh -c 'for p in " + candidates + "; do "
                    "if [ -f \"$p\" ]; then tail -n " + safe_lines + " \"$p\"; exit 0; fi; "
                    "done; journalctl -u redis-server -u redis -n " + safe_lines + " --no-pager 2>/dev/null || "
                    "{ echo \"redis log file not found; checked common paths and journalctl\" >&2; exit 3; }'"
                )
            if mode == "head":
                return f"head -n {lines} {path}"
            elif mode == "tail":
                return f"tail -n {lines} {path}"
            return f"cat {path}"

        if tool_name == "list_dir":
            path = str(kwargs.get("path", "") or "").strip()
            if path == "/etc/redis":
                candidates = " ".join(shlex.quote(p) for p in ["/etc/redis", "/etc/redis-stack", "/usr/local/etc/redis"])
                return (
                    "sh -c 'for d in " + candidates + "; do "
                    "if [ -d \"$d\" ]; then ls -la --color=auto \"$d\"; exit 0; fi; "
                    "done; find /etc -maxdepth 2 \( -iname \"*redis*\" -o -iname \"redis*.conf\" \) "
                    "-print 2>/dev/null | head -n 50'"
                )

        if tool_name == "show_service_status":
            raw_service = str(kwargs.get("service_name", "") or "").strip()
            service = "".join(ch for ch in raw_service if ch.isalnum() or ch in "_.@-")
            if not service:
                return ""
            base_service = service[:-8] if service.endswith(".service") else service
            candidates = [base_service, f"{base_service}.service"]
            if base_service == "redis":
                candidates.extend(["redis-server", "redis-server.service"])
            if base_service == "mysql":
                candidates.extend(["mysqld", "mysqld.service", "mariadb", "mariadb.service"])
            seen = []
            for item in candidates:
                if item and item not in seen:
                    seen.append(item)
            candidate_words = " ".join(shlex.quote(item) for item in seen)
            checked = ", ".join(seen)
            return (
                "sh -c 'for s in " + candidate_words + "; do "
                "systemctl status \"$s\" 2>/dev/null && exit 0; "
                "done; for s in " + candidate_words + "; do "
                "service \"$s\" status 2>/dev/null && exit 0; "
                "done; for s in " + candidate_words + "; do "
                "p=\"${s%.service}\"; pgrep -x \"$p\" >/dev/null && { ps -C \"$p\" -o pid=,comm=,args=; exit 0; }; "
                "done; "
                "echo \"service not found or not running; checked: " + checked + "\" >&2; exit 3'"
            )

        # ==================== 文件写入类（需要内容参数） ====================
        if tool_name == "append_file":
            content = kwargs.get("content", "")
            path = str(kwargs.get("path", "") or "").strip()
            if path == "/etc/sudoers":
                path = "/etc/sudoers.d/kylin-managed"
            safe_content = shlex.quote(str(content))
            safe_path = shlex.quote(path)
            if path.startswith("/etc/sudoers.d/"):
                return (
                    f"sh -c \"printf '%s\\n' {safe_content} | tee -a {safe_path} >/dev/null "
                    f"&& chmod 0440 {safe_path}\""
                )
            return f"sh -c \"printf '%s\\n' {safe_content} | tee -a {safe_path} >/dev/null\""

        if tool_name == "write_file_overwrite":
            content = kwargs.get("content", "")
            path = str(kwargs.get("path", "") or "").strip()
            if path == "/etc/sudoers":
                path = "/etc/sudoers.d/kylin-managed"
            safe_content = shlex.quote(str(content))
            safe_path = shlex.quote(path)
            if path.startswith("/etc/sudoers.d/"):
                return (
                    f"sh -c \"printf '%s\\n' {safe_content} | tee {safe_path} >/dev/null "
                    f"&& chmod 0440 {safe_path}\""
                )
            return f"sh -c \"printf '%s\\n' {safe_content} | tee {safe_path} >/dev/null\""

        # ==================== 定时任务管理 ====================
        if tool_name == "manage_cron":
            action = kwargs.get("action", "list")
            if action == "list":
                return "crontab -l"
            elif action == "edit":
                return "crontab -e"
            elif action == "remove":
                return "crontab -r"
            return "crontab -l"

        # ==================== 服务管理 ====================
        if tool_name in ["manage_service_control", "manage_service_enable"]:
            action = kwargs.get("action", "status")
            service = kwargs.get("service_name", "")
            return f"systemctl {action} {service}"

        # ==================== 用户管理 ====================
        if tool_name == "user_manage":
            action = kwargs.get("action", "add")
            username = kwargs.get("username", "")
            if action == "add":
                return f"useradd {username}"
            elif action == "del":
                return f"userdel -r {username}"
            elif action == "mod":
                group = kwargs.get("group", "")
                return f"usermod -aG {group} {username}"
            return f"useradd {username}"

        # ==================== 包管理 ====================
        if tool_name == "package_manage":
            action = kwargs.get("action", "install")
            package = kwargs.get("package", "")
            if action == "install":
                return f"apt-get install -y {package}"
            elif action == "remove":
                return f"apt-get remove -y {package}"
            elif action == "purge":
                return f"apt-get purge -y {package}"
            return f"apt-get install -y {package}"

        # ==================== 进程信号 ====================
        if tool_name == "manage_process_signal":
            signal = kwargs.get("signal", "TERM")
            pid = kwargs.get("pid", "")
            return f"kill -{signal} {pid}"

        # ==================== 权限变更 ====================
        if tool_name == "change_permissions":
            mode = kwargs.get("mode", "755")
            path = kwargs.get("path", "")
            recursive = kwargs.get("recursive", False)
            if recursive:
                return f"chmod -R {mode} {path}"
            return f"chmod {mode} {path}"

        # ==================== 所有者变更 ====================
        if tool_name == "change_owner":
            user = kwargs.get("user", "")
            group = kwargs.get("group", "")
            path = kwargs.get("path", "")
            recursive = kwargs.get("recursive", False)
            if recursive:
                return f"chown -R {user}:{group} {path}"
            return f"chown {user}:{group} {path}"

        # ==================== 防火墙修改 ====================
        if tool_name == "firewall_modify":
            action = kwargs.get("action", "add")
            chain = kwargs.get("chain", "INPUT")
            rule = kwargs.get("rule", "")
            if action == "add":
                return f"iptables -A {chain} {rule}"
            elif action == "delete":
                return f"iptables -D {chain} {rule}"
            return ""

        # ==================== 系统日志（支持行数） ====================
        if tool_name == "show_system_log":
            lines = kwargs.get("lines", tool_config.get("default_lines", 100))
            return f"journalctl -xe | tail -n {lines}"

        # ==================== 默认命令组装 ====================
        try:
            return base_cmd.format(**kwargs)
        except KeyError as e:
            logger.error(f"命令参数缺失: {e}, kwargs={kwargs}")
            return ""

    @staticmethod
    def get_tools_by_permission(role: str):
        """
        核心逻辑：根据用户角色，从 MCP_TOOLS_REGISTRY 过滤出可见工具
        """
        # admin 和 operator 都能看到所有工具
        if role in ("admin", "operator"):
            return list(MCP_TOOLS_REGISTRY.keys())

        # 其他角色只看 0.1 以下的只读工具
        return [name for name, info in MCP_TOOLS_REGISTRY.items() if info["level"] <= 0.1]

    @staticmethod
    def validate_operation(tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        预检操作：验证工具是否存在、参数是否合法、是否需要二次确认、root权限是否满足

        Returns:
            dict: {"valid": bool, "level": float, "need_confirmation": bool, "message": str}
        """
        tool_config = MCP_TOOLS_REGISTRY.get(tool_name)
        if not tool_config:
            return {"valid": False, "need_confirmation": False, "level": 0, "message": f"Tool {tool_name} not found"}

        level = tool_config["level"]
        need_root = tool_config.get("need_root", 0)
        # 核心规则：level >= 0.5 需要二次确认
        need_confirmation = level >= 0.5

        # ========== 参数白名单检查（确保 args 来自注册表） ==========
        allowed_args = set(KylinMCP.get_allowed_args_for_tool(tool_name))
        biz_args = {k for k in kwargs.keys() if not str(k).startswith("_")}
        unknown_args = sorted(list(biz_args - allowed_args))
        if unknown_args:
            return {
                "valid": False,
                "need_confirmation": need_confirmation,
                "level": level,
                "message": f"工具 {tool_name} 收到未注册参数: {unknown_args}。允许参数: {sorted(list(allowed_args))}",
            }

        # ========== 必填参数检查 ==========
        required_args = KylinMCP.get_required_args_for_tool(tool_name, **kwargs)
        missing_args = [k for k in required_args if k not in kwargs or kwargs.get(k) in [None, ""]]
        if missing_args:
            return {
                "valid": False,
                "need_confirmation": need_confirmation,
                "level": level,
                "message": f"工具 {tool_name} 缺少必填参数: {missing_args}",
            }

        # ========== root 权限检查 ==========
        # 执行层会对 need_root 操作自动走 sudo -n 非交互链路，
        # 因此这里不再因当前非 root 直接拦截。

        # 检查必需参数
        if tool_config.get("requires_content", False):
            if "content" not in kwargs or not kwargs["content"]:
                return {
                    "valid": False,
                    "need_confirmation": need_confirmation,
                    "level": level,
                    "message": f"工具 {tool_name} 需要 content 参数",
                }

        # 检查路径参数是否存在
        path_params = ["path", "src", "dst", "device", "mount_point"]
        has_path = any(p in kwargs for p in path_params)
        if "{path}" in tool_config.get("cmd", "") and "path" not in kwargs:
            if "path" in str(tool_config.get("cmd")) and "path" not in kwargs:
                return {
                    "valid": False,
                    "need_confirmation": need_confirmation,
                    "level": level,
                    "message": f"工具 {tool_name} 需要 path 参数",
                }

        # 危险路径拦截（仅对 level >= 0.5 的操作检查）
        if level >= 0.5:
            dangerous_paths = ["/", "/boot", "/etc", "/usr", "/var/lib", "/dev", "/proc", "/sys"]
            for param in path_params:
                if param in kwargs:
                    path = kwargs[param]
                    if path in dangerous_paths or (isinstance(path, str) and path.rstrip("/") in dangerous_paths):
                        return {
                            "valid": False,
                            "need_confirmation": True,
                            "level": level,
                            "message": f"禁止在系统关键路径 {path} 执行 {tool_name} 操作",
                        }

        return {
            "valid": True,
            "need_confirmation": need_confirmation,
            "level": level,
            "message": tool_config["reason"],
        }

    @staticmethod
    async def confirm_execution(tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        确认执行需要二次确认的操作

        使用方式：
        result = KylinMCP.confirm_execution("delete_file", path="/tmp/test.txt")

        等价于：
        result = KylinMCP.call("delete_file", path="/tmp/test.txt", _confirmed=True)
        """
        kwargs["_confirmed"] = True
        return await KylinMCP.call(tool_name, **kwargs)
        # return KylinMCP.call(tool_name, **kwargs)

    @staticmethod
    def get_tool_arg_specs(tool_names: list) -> Dict[str, Any]:
        """
        提取指定工具列表中每个工具命令模板的必填占位符，
        格式化为 { tool_name: { required_args: [...] } }，
        直接传给 LLM 作为 tool_arg_specs，告知其每个工具需要填哪些参数字段。
        """
        import re
        specs = {}
        for name in tool_names:
            cfg = MCP_TOOLS_REGISTRY.get(name, {})
            cmd = cfg.get("cmd", "")
            placeholders = re.findall(r'\{(\w+)\}', cmd)
            extra = {}
            if cfg.get("allowed_actions"):
                extra["allowed_actions"] = cfg["allowed_actions"]
            specs[name] = {"required_args": placeholders, "command_template": cmd,
                           "description": cfg.get("reason", ""), **extra}
        return specs

    @staticmethod
    def get_tool_list_for_ai() -> List[Dict[str, Any]]:
        """
        专门给 AI 准备的方法：返回所有工具的描述，作为 Prompt 的一部分
        """
        return [
            {
                "name": name,
                "level": info["level"],
                "description": info["reason"],
                "type": info.get("type", "unknown"),
                "requires_confirmation": info["level"] >= 0.5,
                "need_root": info.get("need_root", 0),
            }
            for name, info in MCP_TOOLS_REGISTRY.items()
        ]

    @staticmethod
    def get_tools_by_risk_level(min_level: float = 0.0, max_level: float = 1.0) -> List[Dict[str, Any]]:
        """
        按风险等级筛选工具

        Args:
            min_level: 最低风险等级
            max_level: 最高风险等级

        Returns:
            list: 符合条件的工具列表
        """
        return [
            {"name": name, "level": info["level"], "reason": info["reason"], "need_root": info.get("need_root", 0)}
            for name, info in MCP_TOOLS_REGISTRY.items()
            if min_level <= info["level"] <= max_level
        ]

    @staticmethod
    def get_confirmation_required_tools() -> List[Dict[str, Any]]:
        """获取所有需要二次确认的工具列表（level >= 0.5）"""
        return KylinMCP.get_tools_by_risk_level(min_level=0.5)

#
# # ==================== 使用示例 ====================
# if __name__ == "__main__":
#     # 示例1：只读操作（不需要确认）
#     result = KylinMCP.call("list_dir", path="/tmp")
#     print(f"只读操作: {result['status']}")
#
#     # 示例2：给 ML/AI 的响应
#     ml_result = KylinMCP.call_with_response("list_dir", target="ml", path="/tmp")
#     print(f"ML响应: {ml_result}")
#
#     # 示例3：给前端的响应
#     frontend_result = KylinMCP.call_with_response("list_dir", target="frontend", path="/tmp")
#     print(f"前端响应: {frontend_result}")
#
#     # 示例4：需要确认的操作（第一次调用返回 need_confirmation）
#     result = KylinMCP.call("delete_file", path="/tmp/test.txt")
#     print(f"需要确认: {result['status']}")
#
#     # 示例5：确认后执行
#     if result["status"] == "need_confirmation":
#         confirmed_result = KylinMCP.confirm_execution("delete_file", path="/tmp/test.txt")
#         print(f"确认执行: {confirmed_result['status']}")
#
#     # 示例6：危险路径拦截
#     result = KylinMCP.call("delete_file", path="/etc")
#     print(f"危险路径: {result['status']}")
#
#     # 示例7：获取所有需要确认的工具
#     tools_need_confirm = KylinMCP.get_confirmation_required_tools()
#     print(f"需要确认的工具数量: {len(tools_need_confirm)}")
#
















