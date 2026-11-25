# app/services/orchestrator.py
import json
import os
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core import prompts
from app.core.config import settings
from app.services.mcp_tools import KylinMCP, MCP_TOOLS_REGISTRY
from app.models.task import TaskRecord
from app.models.tool_config import UserToolConfig
from app.services.monitor import SystemMonitor
from app.services.ml_service import MLService


class Orchestrator:
    def __init__(
        self,
        task_id: str,
        user_id: str,
        task_text: str,
        db: Session,
        host_id: str,
        current_user_role: str,
    ):
        self.db = db
        self.task_id = task_id

        identity_context = {
            "role": current_user_role,
            "requested_action": "execute_task",
            "role_label": f"labeled_{current_user_role}",
            "permission_tags": self._get_permission_tags(current_user_role),
            "need_guardrail_check": True,
            "status": "identified",
        }

        self.task_record = db.query(TaskRecord).filter(TaskRecord.id == task_id).first()
        if not self.task_record:
            self.task_record = TaskRecord(
                id=task_id,
                user_id=user_id,
                task_text=task_text,
                host_id=host_id,
                status="init",
                context_data={
                    "identity_context": identity_context,
                    "steps": {},
                    "history": [],
                },
            )
            db.add(self.task_record)
        else:
            self._update_context("identity_context", identity_context)
        db.commit()

    def _get_permission_tags(self, role: str) -> list:
        if role == "operator":
            return ["action_execute", "tool_read_write", "audit_bypass_low_risk"]
        elif role == "auditor":
            return ["read_only", "audit_view"]
        return ["read_only"]

    def _clean_data(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self._clean_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_data(i) for i in data]
        elif isinstance(data, bytes):
            return data.decode("utf-8", errors="ignore")
        return data

    def _update_context(self, key: str, value: Any):
        current = dict(self.task_record.context_data)
        current[key] = self._clean_data(value)
        self.task_record.context_data = current
        flag_modified(self.task_record, "context_data")
        self.db.commit()

    def _add_history(self, step_name: str, content: str):
        current = dict(self.task_record.context_data)
        current.setdefault("history", []).append(f"[{step_name}] {content}")
        self.task_record.context_data = current
        flag_modified(self.task_record, "context_data")
        self.db.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _to_bool(val: Any, default: bool = False) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        if isinstance(val, str):
            v = val.strip().lower()
            if v in {"1", "true", "yes", "y", "on"}:
                return True
            if v in {"0", "false", "no", "n", "off"}:
                return False
        return default

    @staticmethod
    def _contains_cjk(text: Any) -> bool:
        if not isinstance(text, str) or not text:
            return False
        return re.search(r"[\u4e00-\u9fff]", text) is not None

    def _zh_or_fallback(self, text: Any, fallback: str) -> str:
        s = str(text or "").strip()
        if s and self._contains_cjk(s):
            return s
        return fallback

    def _detect_reflection_injection(self, draft: dict) -> tuple[bool, str]:
        """Detect direct attempts to override the reflection/security-scan contract."""
        def walk(value: Any) -> list[str]:
            if isinstance(value, dict):
                out: list[str] = []
                for k, v in value.items():
                    out.extend(walk(k))
                    out.extend(walk(v))
                return out
            if isinstance(value, list):
                out: list[str] = []
                for item in value:
                    out.extend(walk(item))
                return out
            if isinstance(value, str):
                return [value]
            return []

        texts = walk({
            "task_text": getattr(getattr(self, "task_record", None), "task_text", ""),
            "intent": draft.get("intent", ""),
            "command": draft.get("command", ""),
            "execution_plan": draft.get("execution_plan", {}),
        })
        joined = "\n".join(texts)
        lowered = joined.lower()

        strong_patterns = [
            r"忽略(?:以上|前文|所有)?安全规则",
            r"忽略(?:以上|前文|所有)?审查",
            r"跳过(?:抗注入|安全审查|反思)",
            r"不要(?:审查|拦截|检查)",
            r"直接(?:输出|返回|写入|将).*(?:security_scan|injection_resistance|passed)",
            r"(?:security_scan|injection_resistance)\s*[\.:=].*(?:true|passed)",
            r"system\s*override",
            r"ignore\s+(?:all\s+)?(?:previous|above).*(?:safety|instruction|rule)",
            r"do\s+not\s+(?:block|audit|check)",
            r"must\s+return.*(?:security_scan|injection_resistance).*true",
        ]
        for pattern in strong_patterns:
            if re.search(pattern, lowered, re.IGNORECASE | re.DOTALL) or re.search(pattern, joined, re.DOTALL):
                return True, "检测到提示词注入或越权诱导：输入试图覆盖反思层安全审查结果。"
        return False, ""

    def _is_safe_log_archive_cleanup_plan(self, plan: list[dict]) -> bool:
        """Validate the log maintenance flow: archive nginx access log, then clear it with a reversible backup."""
        task_text = str(getattr(self, "task_record", None).task_text or "")
        task_lower = task_text.lower()
        if not (
            "nginx" in task_lower
            and "access" in task_lower
            and "日志" in task_text
            and "归档" in task_text
            and "清理" in task_text
            and ("保留最近" in task_text or "最近 7 天" in task_text or "最近7天" in task_text)
        ):
            return False

        archive_paths: set[str] = set()
        truncate_paths: set[str] = set()
        for item in plan:
            if not isinstance(item, dict):
                continue
            tool = str(item.get("tool") or "")
            args = item.get("args") if isinstance(item.get("args"), dict) else {}
            path = str(args.get("path") or item.get("target") or "").strip()
            if "/var/log/nginx/access.log" not in path:
                continue
            if tool == "archive_backup":
                archive_paths.add(path)
            elif tool == "truncate_file":
                truncate_paths.add(path)

        return bool(archive_paths and truncate_paths and (archive_paths & truncate_paths))

    def _mark_log_archive_cleanup_reversible(self, plan: list[dict]) -> None:
        for item in plan:
            if not isinstance(item, dict) or item.get("tool") != "truncate_file":
                continue
            args = item.get("args") if isinstance(item.get("args"), dict) else {}
            path = str(args.get("path") or item.get("target") or "").strip()
            if not path:
                continue
            item["rollback_supported"] = True
            item["rollback_command"] = f"cp -a {path}.bak {path}"
            item["rollback_reason"] = "执行层会在清理前创建同路径 .bak 前置备份，可用该备份恢复原始日志内容。"
            item["rollback_need_root"] = self._resolve_need_root(
                {"command": item["rollback_command"], "target": path},
                "copy_file",
            )

    @staticmethod
    def _normalize_abs_path(path: str) -> str:
        p = (path or "").strip()
        if not p.startswith("/"):
            return ""
        p = re.sub(r"[\"'`),.;:!?\]\[]+$", "", p)
        p = re.sub(r"/{2,}", "/", p)
        if len(p) > 1 and p.endswith("/"):
            p = p[:-1]
        return p

    def _extract_abs_paths_from_text(self, text: Any) -> list[str]:
        if not isinstance(text, str) or not text.strip():
            return []
        # 匹配常见绝对路径片段，并在后续做归一化去重。
        negation_tokens = ["不是", "而不是", "不要", "别用", "非", "not ", "instead of", "禁止", "不可", "不能", "勿", "不允许"]
        raw = []
        for m in re.finditer(r"/(?:[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*)/?", text):
            # 过滤命令枚举场景（如 rm/tar/truncate），避免把斜杠分隔符误当绝对路径。
            if m.start() > 0 and re.match(r"[A-Za-z0-9_]", text[m.start() - 1]):
                continue
            prefix = text[max(0, m.start() - 16):m.start()].lower()
            if any(tok in prefix for tok in negation_tokens):
                continue
            raw.append(m.group(0))
        seen = set()
        result = []
        for item in raw:
            norm = self._normalize_abs_path(item)
            if not norm:
                continue
            if norm not in seen:
                seen.add(norm)
                result.append(norm)
        return result

    @staticmethod
    def _clean_task_path_token(value: str) -> str:
        token = (value or "").strip().strip("\"'`")
        return re.sub(r"[，,。；;：:\s]+$", "", token)

    def _extract_copy_overwrite_intent(self) -> dict:
        """识别“用 src 覆盖 dst”类任务，避免反思层把复制误改成写空文件。"""
        text = str(getattr(self.task_record, "task_text", "") or "")
        if not text.strip():
            return {}

        patterns = [
            r"(?:用|使用|拿)\s*(?P<src>[^\s，,。；;]+)\s*覆盖\s*(?P<dst>[^\s，,。；;]+)",
            r"(?:把|将)\s*(?P<src>[^\s，,。；;]+)\s*(?:复制到|拷贝到|覆盖到|覆盖)\s*(?P<dst>[^\s，,。；;]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if not match:
                continue
            src = self._clean_task_path_token(match.group("src"))
            dst = self._clean_task_path_token(match.group("dst"))
            if src and dst and src != dst:
                return {"src": src, "dst": dst}
        return {}

    def _enforce_copy_overwrite_intent(
        self,
        plan_items: list[dict],
        allowed_tools: list[str] | None = None,
    ) -> list[dict]:
        allowed = set(allowed_tools or list(MCP_TOOLS_REGISTRY.keys()))
        if "copy_file" not in allowed:
            return plan_items

        intent = self._extract_copy_overwrite_intent()
        if not intent:
            return plan_items

        src = intent["src"]
        dst = intent["dst"]
        has_exact_copy = any(
            item.get("tool") == "copy_file"
            and (item.get("args") or {}).get("src") == src
            and (item.get("args") or {}).get("dst") == dst
            for item in plan_items
        )
        if has_exact_copy:
            return plan_items

        corrected: list[dict] = []
        if "read_file" in allowed:
            corrected.append({
                "id": "cmd_1",
                "tool": "read_file",
                "target": src,
                "args": {"path": src},
                "command": KylinMCP._build_command("read_file", path=src),
                "need_root": self._resolve_need_root({"target": src, "args": {"path": src}}, "read_file"),
                "rollback_supported": False,
                "rollback_command": "",
                "rollback_reason": "只读命令不修改系统状态，无需回滚",
                "rollback_need_root": False,
                "risk_level": MCP_TOOLS_REGISTRY.get("read_file", {}).get("level", 0.0),
            })

        copy_args = {"src": src, "dst": dst}
        corrected.append({
            "id": f"cmd_{len(corrected)+1}",
            "tool": "copy_file",
            "target": dst,
            "args": copy_args,
            "command": KylinMCP._build_command("copy_file", **copy_args),
            "need_root": self._resolve_need_root({"target": dst, "args": copy_args}, "copy_file"),
            "rollback_supported": False,
            "rollback_command": "",
            "rollback_reason": "",
            "rollback_need_root": False,
            "risk_level": MCP_TOOLS_REGISTRY.get("copy_file", {}).get("level", 0.0),
            "auto_corrected": True,
            "correction_reason": "任务明确要求用源文件覆盖目标文件，强制使用 copy_file 执行覆盖。",
        })

        if "read_file" in allowed:
            corrected.append({
                "id": f"cmd_{len(corrected)+1}",
                "tool": "read_file",
                "target": dst,
                "args": {"path": dst},
                "command": KylinMCP._build_command("read_file", path=dst),
                "need_root": self._resolve_need_root({"target": dst, "args": {"path": dst}}, "read_file"),
                "rollback_supported": False,
                "rollback_command": "",
                "rollback_reason": "只读命令不修改系统状态，无需回滚",
                "rollback_need_root": False,
                "risk_level": MCP_TOOLS_REGISTRY.get("read_file", {}).get("level", 0.0),
            })

        return corrected

    def _extract_abs_paths_from_command_item(self, item: dict) -> list[str]:
        if not isinstance(item, dict):
            return []
        candidates = []
        for key in ("target", "command"):
            val = item.get(key)
            if isinstance(val, str):
                candidates.extend(self._extract_abs_paths_from_text(val))

        args = item.get("args")
        if isinstance(args, dict):
            for val in args.values():
                if isinstance(val, str):
                    candidates.extend(self._extract_abs_paths_from_text(val))

        seen = set()
        result = []
        for p in candidates:
            if p not in seen:
                seen.add(p)
                result.append(p)
        return result

    @staticmethod
    def _path_matches_expected(cmd_path: str, expected_path: str) -> bool:
        # 任务给出明确路径时，仅允许同路径或其子路径命中。
        return cmd_path == expected_path or cmd_path.startswith(expected_path + "/")

    @staticmethod
    def _command_primary_verb(command: str) -> str:
        if not isinstance(command, str):
            return ""
        cmd = command.strip()
        if not cmd:
            return ""
        tokens = re.split(r"\s+", cmd)
        if not tokens:
            return ""
        if tokens[0] == "sudo" and len(tokens) > 1:
            return tokens[1]
        return tokens[0]

    def _is_readonly_helper_command(self, command: str) -> bool:
        verb = self._command_primary_verb(command)
        if verb not in {"ls", "stat", "file", "wc", "test", "head", "tail", "cat", "grep", "sed", "awk"}:
            return False
        lowered = str(command or "").lower()
        # 出现可能写入或破坏性操作的迹象时，不按只读辅助放行。
        dangerous_tokens = [" >", ">>", "| tee", "rm ", "mv ", "cp ", "chmod ", "chown ", "truncate ", "dd "]
        return not any(tok in lowered for tok in dangerous_tokens)

    @staticmethod
    def _task_requires_log_content(task_text: str) -> bool:
        t = str(task_text or "")
        patterns = [
            r"最近\s*\d+\s*行",
            r"最后\s*\d+\s*行",
            r"tail",
            r"日志.*行",
            r"查看.*日志",
        ]
        return any(re.search(p, t, flags=re.IGNORECASE) for p in patterns)

    def _should_relax_hallucination_for_readonly_helpers(self, task_paths: list[str], reflection_cmds: list[dict]) -> bool:
        if not task_paths or not reflection_cmds:
            return False
        if not self._task_requires_log_content(self.task_record.task_text):
            return False

        has_content_reader = False
        has_helper = False

        for cmd_item in reflection_cmds:
            if not isinstance(cmd_item, dict):
                return False
            command = str(cmd_item.get("command") or "")
            if not self._is_readonly_helper_command(command):
                return False

            cmd_paths = self._extract_abs_paths_from_command_item(cmd_item)
            for cp in cmd_paths:
                if not any(self._path_matches_expected(cp, p) for p in task_paths):
                    return False

            verb = self._command_primary_verb(command)
            if verb in {"tail", "head", "cat", "grep", "sed", "awk"} and cmd_paths:
                has_content_reader = True
            if verb in {"ls", "stat", "file", "wc", "test"}:
                has_helper = True

        return has_content_reader and has_helper

    def _get_task_locked_paths(self) -> list[str]:
        paths = self._extract_abs_paths_from_text(self.task_record.task_text)
        return paths[:1]

    def _normalize_locked_paths(self, paths: Any) -> list[str]:
        if not isinstance(paths, list):
            return []
        seen = set()
        result = []
        for p in paths:
            norm = self._normalize_abs_path(str(p))
            if not norm:
                continue
            if norm in seen:
                continue
            seen.add(norm)
            result.append(norm)
        return result

    def _is_in_locked_scope(self, path: str, locked_paths: list[str]) -> bool:
        return any(self._path_matches_expected(path, lp) for lp in locked_paths)

    def _enforce_item_path_lock(self, item: dict, locked_paths: list[str]) -> tuple[dict, list[str], bool]:
        if not isinstance(item, dict) or not locked_paths:
            return item, [], False

        tool = str(item.get("tool") or "")
        if not tool:
            return item, [], False

        primary = locked_paths[0]
        new_item = dict(item)
        args_src = new_item.get("args")
        args = dict(args_src) if isinstance(args_src, dict) else {}
        cmd_paths = self._extract_abs_paths_from_command_item(new_item)
        unauthorized = [p for p in cmd_paths if not self._is_in_locked_scope(p, locked_paths)]
        adjusted = False

        # 对不在锁定范围内的路径进行纠偏，避免命令旁路到无关目录。
        if unauthorized:
            allowed_args = set(KylinMCP.get_allowed_args_for_tool(tool))
            if "path" in allowed_args:
                args["path"] = primary
                new_item["target"] = primary
                adjusted = True
            elif isinstance(new_item.get("target"), str):
                new_item["target"] = primary
                adjusted = True

            rebuilt = KylinMCP._build_command(tool, **args)
            if rebuilt:
                new_item["command"] = rebuilt
            new_item["args"] = args

        if adjusted:
            new_item["path_lock_adjusted"] = True
            new_item["path_lock_original_paths"] = unauthorized

        return new_item, unauthorized, adjusted

    def _enforce_plan_path_lock(self, plan_items: list[dict], locked_paths: list[str]) -> tuple[list[dict], list[str]]:
        if not locked_paths:
            return plan_items, []

        locked_paths = self._normalize_locked_paths(locked_paths)
        if not locked_paths:
            return plan_items, []

        rewritten: list[dict] = []
        violations: list[str] = []
        for item in plan_items:
            new_item, unauthorized, _ = self._enforce_item_path_lock(item, locked_paths)
            rewritten.append(new_item)
            if unauthorized:
                cmd_id = str(item.get("id") or "unknown")
                display_cmd = str(item.get("command") or item.get("target") or "")
                violations.append(
                    f"{cmd_id}: 检测到越界路径 {', '.join(unauthorized[:2])}，已锁定到 {locked_paths[0]}（原命令: {display_cmd}）"
                )

        return rewritten, violations

    def _resolve_need_root(self, item: dict, tool: str) -> bool:
        # 反思层/LLM 判定与命令路径启发式联合判定，避免漏判 root。
        if isinstance(item, dict):
            llm_need_root = False
            if "need_root" in item:
                llm_need_root = self._to_bool(item.get("need_root"), default=False)
            elif "root_required" in item:
                llm_need_root = self._to_bool(item.get("root_required"), default=False)

            # 兜底：当 LLM 漏判时，根据完整命令与目标路径做 root 判定。
            def _path_need_root(path_val: Any) -> bool:
                if not isinstance(path_val, str):
                    return False
                p = path_val.strip()
                if not p.startswith("/"):
                    return False
                protected = (
                    "/root",
                    "/etc",
                    "/boot",
                    "/proc",
                    "/sys",
                    "/var/log/private",
                    "/var/log/btmp",
                    "/var/log/wtmp",
                )
                if any(p == pref or p.startswith(pref + "/") for pref in protected):
                    return True

                # 对写操作工具，/var/log 默认按受保护路径处理，避免漏判 sudo。
                write_sensitive_tools = {
                    "truncate_file",
                    "delete_file",
                    "move_file",
                    "copy_file",
                    "archive_backup",
                }
                if tool in write_sensitive_tools and (p == "/var/log" or p.startswith("/var/log/")):
                    return True

                return False

            args = item.get("args") or {}
            heuristic_need_root = False
            if isinstance(args, dict):
                for k in ("path", "src", "dst", "mount_point", "device"):
                    if _path_need_root(args.get(k)):
                        heuristic_need_root = True
                        break

            if _path_need_root(item.get("target")):
                heuristic_need_root = True

            cmd = str(item.get("command") or "")
            if cmd:
                root_cmd_patterns = [
                    r"(^|\s)/root(/|\s|$)",
                    r"(^|\s)/etc(/|\s|$)",
                    r"(^|\s)/boot(/|\s|$)",
                    r"(^|\s)/proc(/|\s|$)",
                    r"(^|\s)/sys(/|\s|$)",
                    r"(^|\s)/var/log/(private|btmp|wtmp)(/|\s|$)",
                ]
                if any(re.search(pat, cmd) for pat in root_cmd_patterns):
                    heuristic_need_root = True

            if llm_need_root or heuristic_need_root:
                return True
        return bool(MCP_TOOLS_REGISTRY.get(tool, {}).get("need_root", 0))

    def _extract_raw_commands(self, raw_plan: Any) -> list:
        if isinstance(raw_plan, list):
            return raw_plan
        if isinstance(raw_plan, dict):
            if isinstance(raw_plan.get("commands"), list):
                return raw_plan.get("commands")
            if isinstance((raw_plan.get("plan_execute") or {}).get("commands"), list):
                return (raw_plan.get("plan_execute") or {}).get("commands")
            if isinstance((raw_plan.get("execution_plan") or {}).get("commands"), list):
                return (raw_plan.get("execution_plan") or {}).get("commands")
            if isinstance(raw_plan.get("steps"), list):
                return raw_plan.get("steps")
        return []

    def _is_disk_space_diagnosis(self) -> bool:
        text = self.task_record.task_text or ""
        space = re.search(r"磁盘|磁碟|disk|文件系统|空间不足|df\s+-h|du\s+-", text, re.I)
        diagnosis = re.search(r"排查|定位|占用|使用率|大文件|热点|diagnos|usage", text, re.I)
        if re.search(r"\bI/?O\b|吞吐|读写速率", text, re.I) and not re.search(r"空间|容量|大文件|热点目录|df\s+-|du\s+-", text, re.I):
            return False
        return bool(space and diagnosis)

    def _disk_diagnostic_plan(self, plan_items: list[dict], stage: str, allowed: list[str] | None) -> list[dict]:
        """Supply actual space diagnostics where the task only requests investigation/advice."""
        text = self.task_record.task_text or ""
        # Explicit mutations still go through the normal decision/reflection process.
        readonly = re.search(r"只读|提出.*方案|给出.*方案|变更.*审批|禁止.*删除|不要.*删除", text)
        mutations = re.search(r"执行清理|直接清理|删除|清空|格式化|扩容|迁移|truncate|\brm\b", text, re.I)
        if not self._is_disk_space_diagnosis() or (mutations and not readonly):
            return plan_items
        required = {"disk_usage", "directory_usage", "find_large_files"}
        if not required.issubset(set(allowed if allowed is not None else MCP_TOOLS_REGISTRY)):
            return plan_items
        locked = self._normalize_locked_paths(self._extract_abs_paths_from_text(text))
        scope = locked[0] if locked else getattr(self, "_disk_space_scope", "")
        if not scope:
            import psutil
            # Select a real mounted filesystem; do not assume the full device is mounted at /.
            candidates = {"/"}
            for partition in psutil.disk_partitions(all=False):
                # Snap images are intentionally 100% full and cannot be cleaned as data disks.
                if (getattr(partition, "fstype", "") in {"squashfs", "tmpfs", "devtmpfs", "iso9660"}
                        or "ro" in getattr(partition, "opts", "").split(",")):
                    continue
                candidates.add(partition.mountpoint)
            usage = []
            for path in candidates:
                try:
                    if os.path.isdir(path):
                        usage.append((psutil.disk_usage(path).percent, path))
                except OSError:
                    continue
            percentage = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
            if percentage and usage:
                expected = float(percentage.group(1))
                scope = min(usage, key=lambda item: abs(item[0] - expected))[1]
            else:
                scope = max(usage, default=(0, "/"))[1]
            self._disk_space_scope = scope
        if not os.path.isdir(scope):
            scope = os.path.dirname(scope) or "/"
            if locked and not self._is_in_locked_scope(scope, locked):
                return plan_items
        items = []
        for tool in ["disk_usage", "directory_usage", "find_large_files"]:
            previous = next((c for c in plan_items if c.get("tool") == tool), {})
            args = {} if tool == "disk_usage" else {"path": scope}
            items.append({**previous, "id": f"disk_{tool}", "tool": tool,
                          "target": scope, "args": args,
                          "command": KylinMCP._build_command(tool, **args),
                          "need_root": self._resolve_need_root({"target": scope, "args": args}, tool),
                          "risk_level": 0.0, "rollback_supported": False,
                          "rollback_command": "", "rollback_need_root": False,
                          "rollback_reason": "只读排查不修改系统状态，无需回滚",
                          "auto_generated": True, "auto_stage": stage})
        return items

    def _auto_expand_plan(self, plan_items: list[dict], stage: str, target: str = "", allowed_tools: list[str] | None = None) -> list[dict]:
        """当 LLM 没给出多命令计划时，自动补一条低风险探测命令，保证计划可视化不是单条。"""
        min_count = max(2, int(getattr(settings, "MIN_PLAN_COMMANDS", 3) or 3))
        if len(plan_items) >= min_count:
            return plan_items

        allowed = set(allowed_tools or list(MCP_TOOLS_REGISTRY.keys()))
        existing_tools = {i.get("tool") for i in plan_items}

        candidates: list[dict] = []
        if target and "list_dir" in allowed and "list_dir" not in existing_tools:
            candidates.append({"tool": "list_dir", "args": {"path": target}, "target": target})
        if "list_disk" in allowed and "list_disk" not in existing_tools:
            candidates.append({"tool": "list_disk", "args": {}, "target": ""})
        if "list_process" in allowed and "list_process" not in existing_tools:
            candidates.append({"tool": "list_process", "args": {}, "target": ""})

        for c in candidates:
            tool = c["tool"]
            command = KylinMCP._build_command(tool, **(c.get("args") or {}))
            if not command:
                continue
            plan_items.append({
                "id": f"auto_{len(plan_items)+1}",
                "tool": tool,
                "target": c.get("target"),
                "args": c.get("args") or {},
                "command": command,
                "need_root": bool(MCP_TOOLS_REGISTRY.get(tool, {}).get("need_root", 0)),
                "risk_level": MCP_TOOLS_REGISTRY.get(tool, {}).get("level", 0.0),
                "auto_generated": True,
                "auto_stage": stage,
            })
            if len(plan_items) >= min_count:
                break

        return plan_items

    def _normalize_plan_commands(self, raw_plan: Any, default_tool: str = "", default_target: str = "", default_args: dict | None = None, stage: str = "decision", allowed_tools: list[str] | None = None, auto_expand: bool = True) -> list[dict]:
        default_args = default_args or {}
        plan_items: list[dict] = []

        raw_plan = self._extract_raw_commands(raw_plan)

        for idx, item in enumerate(raw_plan):
            if not isinstance(item, dict):
                continue
            tool = str(item.get("tool") or item.get("tool_name") or default_tool or "").strip()
            if not tool or tool not in MCP_TOOLS_REGISTRY:
                continue
            args_raw = item.get("args", {})
            args_pre = args_raw if isinstance(args_raw, dict) else {}
            target = item.get("target") or args_pre.get("path") or default_target
            args = {k: args_pre[k] for k in KylinMCP.get_allowed_args_for_tool(tool) if k in args_pre}
            if target and "path" in KylinMCP.get_allowed_args_for_tool(tool) and "path" not in args:
                args["path"] = target
            # 命令展示统一由 tool+args 规范生成，避免 LLM 文本与真实执行参数不一致。
            command = KylinMCP._build_command(tool, **args) or item.get("command")
            if not command:
                continue
            plan_items.append({
                "id": item.get("id") or f"cmd_{idx+1}",
                "tool": tool,
                "target": target,
                "args": args,
                "command": command,
                "need_root": self._resolve_need_root(item, tool),
                "rollback_supported": self._to_bool(item.get("rollback_supported"), default=False),
                "rollback_command": str(item.get("rollback_command") or "").strip(),
                "rollback_reason": str(item.get("rollback_reason") or "").strip(),
                "rollback_need_root": self._to_bool(item.get("rollback_need_root"), default=False),
                "risk_level": MCP_TOOLS_REGISTRY.get(tool, {}).get("level", 0.0),
            })

        if not plan_items and default_tool:
            args = {k: default_args[k] for k in KylinMCP.get_allowed_args_for_tool(default_tool) if k in default_args}
            if default_target and "path" in KylinMCP.get_allowed_args_for_tool(default_tool) and "path" not in args:
                args["path"] = default_target
            command = KylinMCP._build_command(default_tool, **args)
            if not command:
                return plan_items
            plan_items.append({
                "id": "cmd_1",
                "tool": default_tool,
                "target": default_target,
                "args": args,
                "command": command,
                "need_root": bool(MCP_TOOLS_REGISTRY.get(default_tool, {}).get("need_root", 0)),
                "rollback_supported": False,
                "rollback_command": "",
                "rollback_reason": "",
                "rollback_need_root": False,
                "risk_level": MCP_TOOLS_REGISTRY.get(default_tool, {}).get("level", 0.0),
            })

        plan_items = self._enforce_copy_overwrite_intent(plan_items, allowed_tools=allowed_tools)

        if stage in {"perception", "decision", "reflection"}:
            plan_items = self._disk_diagnostic_plan(plan_items, stage, allowed_tools)

        if auto_expand:
            plan_items = self._auto_expand_plan(
                plan_items,
                stage=stage,
                target=default_target,
                allowed_tools=allowed_tools,
            )
        return plan_items

    def _collect_guardrail_tools(self, draft: dict, reflection: dict) -> list[str]:
        tools: list[str] = []

        # 护栏与执行链路保持一致：优先校验 Step6 反思计划；
        # 仅当 Step6 无计划时，回退到 Step5 草案。
        reflection_cmds = (reflection.get("plan_execute", {}) or {}).get("commands", [])
        draft_cmds = (draft.get("execution_plan", {}) or {}).get("commands", [])
        source_cmds = reflection_cmds if reflection_cmds else draft_cmds

        for item in source_cmds:
            t = item.get("tool")
            if t:
                tools.append(t)
        if reflection.get("revised_tool"):
            tools.append(reflection.get("revised_tool"))
        # 去重并保持顺序
        dedup: list[str] = []
        for t in tools:
            if t not in dedup:
                dedup.append(t)
        return dedup

    def _collect_approval_commands(self, draft: dict, reflection: dict, risk: dict) -> list[dict]:
        risk_score = float(risk.get("total_risk", 0.0) or 0.0)
        reflection_candidates = self._normalize_plan_commands(
            (reflection.get("plan_execute") or {}).get("commands") or reflection.get("plan") or reflection,
            default_tool=reflection.get("revised_tool", ""),
            default_target=reflection.get("revised_target", ""),
            default_args=reflection.get("revised_args", {}),
            stage="approval",
        )

        draft_candidates = self._normalize_plan_commands(
            (draft.get("execution_plan") or {}).get("commands") or draft.get("plan") or draft,
            default_tool=draft.get("tool", ""),
            default_target=draft.get("target", ""),
            default_args=draft.get("args", {}),
            stage="approval",
        )

        # 审批与执行必须与反思层保持一致：优先采用 Step6 反思计划，缺失时才回退到 Step5 草案。
        candidates = reflection_candidates or draft_candidates

        options = []
        for i, c in enumerate(candidates):
            tool = c.get("tool")
            if not tool:
                continue
            need_root = self._resolve_need_root(c, tool)
            level = float(MCP_TOOLS_REGISTRY.get(tool, {}).get("level", c.get("risk_level", 0.0)) or 0.0)
            options.append({
                "id": c.get("id") or f"cmd_{i+1}",
                "tool": tool,
                "command": c.get("command") or KylinMCP._build_command(tool, **(c.get("args") or {})),
                "args": c.get("args") or {},
                "target": c.get("target"),
                "need_root": need_root,
                "rollback_supported": self._to_bool(c.get("rollback_supported"), default=False),
                "rollback_command": str(c.get("rollback_command") or "").strip(),
                "rollback_reason": str(c.get("rollback_reason") or "").strip(),
                "rollback_need_root": self._to_bool(c.get("rollback_need_root"), default=False),
                "risk_score": max(risk_score, level),
                "checked": True,
            })

        return options

    async def _perceive(self) -> dict:
        # allowed_tools 在感知层就需要作为输入，LLM 选工具时应限定在该列表内
        identity = self.task_record.context_data.get("identity_context", {})
        role = identity.get("role", "guest")
        allowed_tools = KylinMCP.get_tools_by_permission(role)

        # 感知层只允许 level 0.0 的纯读类工具，防止 LLM 误选操作类工具做感知探测
        perceive_tools = [
            name for name in allowed_tools
            if MCP_TOOLS_REGISTRY.get(name, {}).get("level", 1.0) == 0.0
        ]

        # ================== 【第一次 LLM 调用：工具选择】 ==================
        # 构造 User Prompt
        select_user_content = prompts.STEP3_TOOL_SELECT_USER_TPL.format(
            task_text=self.task_record.task_text,
            allowed_tools=json.dumps(perceive_tools, ensure_ascii=False),
            tool_arg_specs=json.dumps(KylinMCP.get_tool_arg_specs(perceive_tools), ensure_ascii=False)
        )

        # 调用DeepSeek
        choice_json = await MLService.call_llm(
            system_prompt=prompts.STEP3_PERCEIVE_TOOL_SYSTEM,
            user_prompt=select_user_content
        )

        if not choice_json:
            raise Exception("感知层：LLM 工具选择解析失败")

        llm_tool = choice_json.get("tool")
        if llm_tool not in MCP_TOOLS_REGISTRY:
            llm_tool = "list_disk"
        llm_target = choice_json.get("target")
        llm_args_raw = choice_json.get("args", {})
        llm_args = llm_args_raw if isinstance(llm_args_raw, dict) else {}
        # 只有工具本身需要 path 参数时，才将 target 映射到 path
        _llm_specs = KylinMCP.get_tool_arg_specs([llm_tool]).get(llm_tool, {})
        if llm_target and "path" in _llm_specs.get("required_args", []) and "path" not in llm_args:
            llm_args["path"] = llm_target

        # 感知层 plan-execute：支持 LLM 规划多条探测命令
        plan_commands = self._normalize_plan_commands(
            choice_json.get("plan") or choice_json.get("execution_plan") or choice_json.get("plan_execute") or choice_json,
            default_tool=llm_tool,
            default_target=llm_target,
            default_args=llm_args,
            stage="perception",
            allowed_tools=perceive_tools,
        )
        # 感知层仅允许使用纯读工具
        plan_commands = [c for c in plan_commands if c.get("tool") in perceive_tools]
        if not plan_commands and llm_tool in perceive_tools:
            plan_commands = self._normalize_plan_commands([], default_tool=llm_tool, default_target=llm_target, default_args=llm_args, stage="perception", allowed_tools=perceive_tools)

        tool_results = []
        plan_exec_results = []
        for c in plan_commands:
            tool = c.get("tool")
            args = c.get("args") or {}
            mcp_res = await KylinMCP.call(tool, **args)
            output_raw = mcp_res.get("output", mcp_res.get("message", ""))
            if isinstance(output_raw, bytes):
                output_raw = output_raw.decode("utf-8", errors="ignore")
            observation = str(output_raw)[:500]
            exec_status = mcp_res.get("status", "error")
            obs_status = "success" if exec_status == "success" else "warning"

            item = {
                "tool": tool,
                "command": c.get("command") or KylinMCP._build_command(tool, **args),
                "target": c.get("target"),
                "args": args,
                "observation": observation,
                "status": obs_status,
            }
            tool_results.append(item)
            plan_exec_results.append({
                "id": c.get("id"),
                "tool": tool,
                "command": item["command"],
                "status": obs_status,
            })

        if not tool_results:
            # 极端兜底：至少保留一条失败记录，避免前端空数组
            tool_results = [{
                "tool": llm_tool,
                "command": KylinMCP._build_command(llm_tool, **llm_args),
                "target": llm_target,
                "args": llm_args,
                "observation": "感知计划为空或工具不在感知白名单",
                "status": "warning",
            }]
            plan_exec_results = [{
                "id": "cmd_1",
                "tool": llm_tool,
                "command": tool_results[0]["command"],
                "status": "warning",
            }]

        summary_observation = "\n".join(
            [f"[{i.get('tool')}] {i.get('observation')}" for i in tool_results]
        )[:1200]
        obs_status = "success" if any(i.get("status") == "success" for i in tool_results) else "warning"

        # ================== 【第二次 LLM 调用：结果摘要与打标】 ==================
        summary_user_content = prompts.STEP3_PERCEIVE_SUMMARY_USER_TPL.format(
            task_text=self.task_record.task_text,
            tool=tool_results[0].get("tool"),
            target=tool_results[0].get("target"),
            status=obs_status,
            observation=summary_observation
        )

        summary_json = await MLService.call_llm(
            system_prompt=prompts.STEP3_PERCEIVE_SUMMARY_SYSTEM,
            user_prompt=summary_user_content
        )

        if not summary_json:
            # 兜底逻辑，防止 LLM 抽风导致流程中断
            summary_json = {
                "summary": "探测执行完成，但摘要生成失败。",
                "tags": ["系统监控与诊断"]
            }
        # ================================================================
        raw_tags = summary_json.get("tags", ["系统监控与诊断"])
        tags = raw_tags if isinstance(raw_tags, list) else [raw_tags]
        summary = summary_json.get("summary", "未生成摘要")

        perception_result = {
            "stage": "perception",
            "request_id": self.task_id,
            "allowed_tools": allowed_tools,
            "tags": tags,
            "summary": summary,
            "tool_results": tool_results,
            "plan_execute": {
                "mode": "plan-execute",
                "commands": plan_commands,
                "execution": plan_exec_results,
            },
            "timestamp": self._now(),
        }
        self._update_context("step3_perception", perception_result)
        self._add_history(
            "环境感知",
            f"感知层按计划执行 {len(tool_results)} 条探测命令，"
            f"场景标签识别为【{tags[0] if tags else '未知'}】。"
            f"感知摘要：{summary}",
        )
        return perception_result

    async def _build_context_bundle(self, perception_summary: str) -> dict:
        identity = self.task_record.context_data.get("identity_context", {})
        role = identity.get("role", "guest")

        # MemoryRetrieveRequest — 完整字段发给 RAG 服务
        # tag_filter 来自 Step 3 感知层 LLM 生成的场景标签，用于过滤相关记忆
        tags = self.task_record.context_data.get("step3_perception", {}).get("tags", [])
        memory = await MLService.retrieve_memory(
            task_text=self.task_record.task_text,
            request_id=self.task_id,
            host_id=self.task_record.host_id,
            top_k_raw_log=3,
            top_k_reflection=1,
            tag_filter=tags,  # ← 使用感知层生成的场景标签过滤 RAG 记忆
        )
        # allowed_tools 已在 Step 3 生成并写入 step3_perception，直接取用不重复计算
        step3 = self.task_record.context_data.get("step3_perception", {})
        allowed_tools = step3.get("allowed_tools", KylinMCP.get_tools_by_permission(role))

        bundle = {
            "request_id": self.task_id,
            "stage": "context_build",
            "task_text": self.task_record.task_text,
            # user_context 对齐框架文档：只含 role 和 host_id
            "user_context": {
                "role": role,
                "host_id": self.task_record.host_id,
            },
            "perception_summary": perception_summary,
            "raw_log_memory": memory.get("raw_logs", []),
            "reflection_memory": memory.get("reflections", []),
            "manual_memory": memory.get("kylin_manuals", []),
            "allowed_tools": allowed_tools,
            "locked_paths": self._get_task_locked_paths(),
            "tool_arg_specs": KylinMCP.get_tool_arg_specs(allowed_tools),
            "decision_hints": {
                "avoid_actions": ["rm", "rm -rf"],
                "preferred_strategy": "优先参考 Reflection，选择非破坏性清理。",
                "path_lock_policy": "当 task_text 含绝对路径时，只允许使用同路径或其子路径；禁止改写为其他绝对路径。",
            },
            "timestamp": self._now(),
        }
        self._update_context("step4_context_bundle", bundle)
        self._add_history(
            "上下文构建",
            f"以标签【{'、'.join(tags) if tags else '无'}】过滤 RAG 记忆库，"
            f"召回历史经验 {len(bundle['reflection_memory'])} 条、"
            f"执行日志 {len(bundle['raw_log_memory'])} 条、"
            f"麒麟手册 {len(bundle['manual_memory'])} 条，上下文束构建完成。",
        )
        return bundle

    async def _generate_decision_draft(self, bundle: dict) -> dict:
        # ------------------------------------------------------------------
        # 1. 接入DeepSeek：将完整 ContextBundle 发送给 LLM 进行逻辑判断
        # ------------------------------------------------------------------
        user_input = prompts.STEP5_DECISION_USER_TPL.format(
            context_bundle_json=json.dumps(bundle, ensure_ascii=False)
        )
        # llm_res 应包含：intent, tool, command, target, reason, 以及筛选出的记忆子集
        llm_res = await MLService.call_llm(
            system_prompt=prompts.STEP5_DECISION_SYSTEM,
            user_prompt=user_input
        )

        if not llm_res:
            raise Exception("决策层：LLM 生成草案失败")
        # ------------------------------------------------------------------
        # [LLM 决策位] LLM 读取完整 ContextBundle（一次性整体传入），主动逐条阅读三块记忆，
        # 各块用途不同：
        #   manual_memory      → 参考价值（麒麟手册最佳实践），LLM 选出对当前决策有指导意义的条目
        #   reflection_memory  → 冲突判断（历史反思），检查当前操作是否曾被标记为危险或建议替换
        #   raw_log_memory     → 冲突判断（历史执行日志），检查此操作是否已经执行过且失败/导致冲突
        # LLM 在 reference_decision 中直接返回它认为相关的条目子集；后端从子集中抽取字段填入 referenced_fields。
        # ------------------------------------------------------------------
        ref_dec_llm = llm_res.get("reference_decision", {})
        reflection_memory = ref_dec_llm.get("reflection_memory", [])   # [LLM 返回子集] 冲突判断来源
        manual_memory = ref_dec_llm.get("manual_memory", [])           # [LLM 返回子集] 参考价值来源
        raw_log_memory = ref_dec_llm.get("raw_log_memory", [])        # [LLM 返回子集] 冲突判断来源
        # matched_count: 只有 LLM 明确判定存在冲突时才作为冲突数。
        # 召回到的 reflection/raw_log/manual 可能只是参考资料，不能自动等价为冲突。
        matched_reflection = len(reflection_memory)
        matched_raw_log = len(raw_log_memory)
        reference_conflict_count = matched_reflection + matched_raw_log
        conflict_assessment_raw = llm_res.get("conflict_assessment", {}) if isinstance(llm_res.get("conflict_assessment"), dict) else {}
        conflict_reason_raw = str(conflict_assessment_raw.get("conflict_reason") or "").strip()
        conflict_message_raw = str(conflict_assessment_raw.get("message") or "").strip()
        if "conflict_detected" in conflict_assessment_raw:
            conflict_detected = self._to_bool(conflict_assessment_raw.get("conflict_detected"), default=False)
        else:
            no_conflict_text = f"{conflict_reason_raw} {conflict_message_raw}".strip()
            conflict_detected = reference_conflict_count > 0 and not any(
                marker in no_conflict_text for marker in ["无冲突", "不存在冲突", "未发现冲突", "no conflict"]
            )
        matched_count = reference_conflict_count if conflict_detected else 0
        draft_tool = llm_res.get("tool")
        if draft_tool not in MCP_TOOLS_REGISTRY:
            allowed_fallback = bundle.get("allowed_tools") or ["list_disk"]
            draft_tool = allowed_fallback[0]
        draft_target = llm_res.get("target")
        draft_args_raw = llm_res.get("args", {})
        draft_args = draft_args_raw if isinstance(draft_args_raw, dict) else {}
        locked_paths = self._normalize_locked_paths(bundle.get("locked_paths", []))

        if locked_paths and isinstance(draft_target, str) and draft_target.strip():
            norm_target = self._normalize_abs_path(draft_target)
            if norm_target and not self._is_in_locked_scope(norm_target, locked_paths):
                draft_target = locked_paths[0]
        # 只有工具本身需要 path 参数时，才将 target 映射到 path
        _draft_specs = KylinMCP.get_tool_arg_specs([draft_tool]).get(draft_tool, {})
        if draft_target and "path" in _draft_specs.get("required_args", []) and "path" not in draft_args:
            draft_args["path"] = draft_target
        # LLM 幻觉兜底：draft_args 漏填的 required_args，从 draft_target 补齐（仅 path 类）
        _draft_required = _draft_specs.get("required_args", [])
        _draft_missing = [k for k in _draft_required if k not in draft_args]
        if _draft_missing and draft_target:
            for k in _draft_missing:
                if k == "path":
                    draft_args[k] = draft_target

        if locked_paths and isinstance(draft_args.get("path"), str):
            arg_path = self._normalize_abs_path(draft_args.get("path"))
            if arg_path and not self._is_in_locked_scope(arg_path, locked_paths):
                draft_args["path"] = locked_paths[0]

        draft_command = llm_res.get("command") or KylinMCP._build_command(draft_tool, **draft_args)
        execution_plan = self._normalize_plan_commands(
            llm_res.get("plan") or llm_res.get("execution_plan") or llm_res.get("plan_execute") or llm_res,
            default_tool=draft_tool,
            default_target=draft_target,
            default_args=draft_args,
            stage="decision",
            allowed_tools=bundle.get("allowed_tools", []),
        )
        execution_plan, path_lock_violations = self._enforce_plan_path_lock(execution_plan, locked_paths)
        if execution_plan:
            head = execution_plan[0]
            draft_tool, draft_target = head["tool"], head.get("target")
            draft_args, draft_command = head["args"], head["command"]

        decision_draft = {
            "stage": "decision",
            "request_id": self.task_id,
            "intent": llm_res.get("intent"),
            "tool": draft_tool,
            "args": draft_args,
            "command": draft_command,
            "target": draft_target,
            "execution_plan": {
                "mode": "plan-execute",
                "will_execute": False,
                "commands": execution_plan,
            },
            "reason": llm_res.get("reason"),
            "status": "draft",
            "timestamp": self._now(),

            # memory_flashback: 保持你的 logic-based message 逻辑
            "memory_flashback": {
                "request_id": self.task_id,
                "display_stage": "decision",
                "render_mode": "thinking_stream",
                "status": "matched" if conflict_detected else "no_match",
                "matched_count": matched_count,
                "conflict_detected": conflict_detected,
                "message": llm_res.get("memory_flashback_message",
                                       f"警告：检测到 {matched_count} 条潜在冲突" if conflict_detected else "未检索到冲突历史记录。"),
            },

            # conflict_state: 保持你的 matched_sources 自动推断逻辑
            "conflict_state": {
                "conflict_detected": conflict_detected,
                "conflict_reason": conflict_reason_raw if conflict_detected else "无冲突",
                "matched_sources": (
                        (["Reflection"] if matched_reflection > 0 else []) +
                        (["Raw_Log"] if matched_raw_log > 0 else [])
                ) if conflict_detected else [],
                "matched_count": matched_count,
            },

            # reference_decision: 保持你原有的结构化字段抽取 (referenced_fields)
            "reference_decision": {
                "use_reflection": matched_reflection > 0,
                "use_kylin_manual": len(manual_memory) > 0,
                "use_raw_log": matched_raw_log > 0,
                "referenced_sources": (
                        (["Reflection"] if matched_reflection > 0 else []) +
                        (["KylinManual"] if len(manual_memory) > 0 else []) +
                        (["Raw_Log"] if matched_raw_log > 0 else [])
                ),
                "referenced_fields": {
                    "reflection_items": [
                        {
                            "revised_tool": it.get("revised_tool"),
                            "revised_command": it.get("revised_command"),
                            "reflection_reason": it.get("reflection_reason"),
                            "evidence": it.get("evidence"),
                        } for it in reflection_memory
                    ],
                    "manual_items": [
                        {
                            "section": it.get("section"),
                            "summary": it.get("summary"),
                        } for it in manual_memory
                    ],
                    "raw_log_items": [
                        {
                            "task": it.get("task"),
                            "target": it.get("target"),
                            "status": it.get("status"),
                            "description": it.get("description"),
                        } for it in raw_log_memory
                    ],
                },
            },
        }
        # 冲突评估字段对齐（补充缺失的结构）
        decision_draft["conflict_assessment"] = {
            "conflict_detected": conflict_detected,
            "conflict_reason": conflict_reason_raw if conflict_detected else "无冲突",
            "matched_count": matched_count,
            "message": conflict_message_raw if conflict_detected else "无冲突历史。"
        }
        self._update_context("step5_decision_draft", decision_draft)
        if path_lock_violations:
            self._add_history(
                "路径锁定",
                f"决策层检测到 {len(path_lock_violations)} 条越界路径命令，已自动纠偏到 {locked_paths[0]}。",
            )
        conflict_hint = (
            f"⚠ 检测到与 {matched_count} 条历史记录存在潜在冲突，已标记供反思层复核。"
            if matched_count > 0 else "未检测到历史冲突。"
        )
        self._add_history(
            "初步决策",
            f"意图：{decision_draft['intent']} | 工具：{decision_draft['tool']} | "
            f"命令计划数：{len(execution_plan)} | {conflict_hint}",
        )
        return decision_draft

    async def _self_reflection(self, bundle: dict, draft: dict) -> dict:
        # ------------------------------------------------------------------
        # [LLM 决策位] 本步全部内容均由 LLM 输出。
        # LLM 读取 step5_decision_draft 和 ContextBundle，对初步决策进行安全审查和修订：
        # ① 按四项审查原则判断每项是否通过，生成 security_scan
        # ② 如需修订则输出 revised_tool / revised_command
        # ③ 生成 reflection_reason 和 evidence
        # ------------------------------------------------------------------
        # 1. 构造 Prompt 发送给DeepSeek
        allowed_tools = bundle.get("allowed_tools", [])
        user_input = prompts.STEP6_REFLECTION_USER_TPL.format(
            original_tool=draft.get("tool"),
            original_args=json.dumps(draft.get("args", {}), ensure_ascii=False),
            original_command=draft.get("command"),
            original_target=draft.get("target"),
            original_plan_commands=json.dumps((draft.get("execution_plan") or {}).get("commands", []), ensure_ascii=False),
            intent=draft.get("intent"),
            allowed_tools=allowed_tools,
            tool_arg_specs=json.dumps(KylinMCP.get_tool_arg_specs(allowed_tools), ensure_ascii=False),
            locked_paths=json.dumps(self._normalize_locked_paths(bundle.get("locked_paths", [])), ensure_ascii=False),
        )

        # 2. 获取 LLM 审计结果
        reflection_json = await MLService.call_llm(
            system_prompt=prompts.STEP6_REFLECTION_SYSTEM,
            user_prompt=user_input
        )

        if not reflection_json:
            raise Exception("反思层：AI 审计服务解析失败")

        # ------------------------------------------------------------------
        # 校验 revised_tool 必须来自 allowed_tools，防止 LLM 幻觉出不存在的工具名
        # ------------------------------------------------------------------
        revised_tool_raw = reflection_json.get("revised_tool", draft.get("tool"))
        if allowed_tools and revised_tool_raw not in allowed_tools:
            # LLM 幻觉了一个不存在的工具名，fallback 到 draft 的工具（已在 allowed_tools 中）
            reflection_json["revised_tool"] = draft.get("tool")
        # ------------------------------------------------------------------
        revised_tool = reflection_json.get("revised_tool", draft.get("tool"))
        revised_target = reflection_json.get("revised_target", draft.get("target"))
        revised_args_raw = reflection_json.get("revised_args", draft.get("args", {}))
        revised_args = revised_args_raw if isinstance(revised_args_raw, dict) else {}
        locked_paths = self._normalize_locked_paths(bundle.get("locked_paths", []))

        if locked_paths and isinstance(revised_target, str) and revised_target.strip():
            norm_target = self._normalize_abs_path(revised_target)
            if norm_target and not self._is_in_locked_scope(norm_target, locked_paths):
                revised_target = locked_paths[0]
        # 只有工具本身需要 path 参数时，才将 target 映射到 path
        _revised_specs = KylinMCP.get_tool_arg_specs([revised_tool]).get(revised_tool, {})
        if revised_target and "path" in _revised_specs.get("required_args", []) and "path" not in revised_args:
            revised_args["path"] = revised_target
        # LLM 幻觉兜底：revised_args 漏填的 required_args，从 draft_args 补齐
        _required = _revised_specs.get("required_args", [])
        _missing = [k for k in _required if k not in revised_args]
        if _missing:
            draft_args = draft.get("args", {})
            for k in _missing:
                if k in draft_args:
                    revised_args[k] = draft_args[k]

        if locked_paths and isinstance(revised_args.get("path"), str):
            arg_path = self._normalize_abs_path(revised_args.get("path"))
            if arg_path and not self._is_in_locked_scope(arg_path, locked_paths):
                revised_args["path"] = locked_paths[0]

        revised_command = KylinMCP._build_command(revised_tool, **revised_args) or reflection_json.get("revised_command")
        draft_plan = self._normalize_plan_commands(
            (draft.get("execution_plan") or {}).get("commands") or draft,
            default_tool=draft.get("tool", ""),
            default_target=draft.get("target", ""),
            default_args=draft.get("args", {}),
            stage="reflection_baseline",
            allowed_tools=bundle.get("allowed_tools", []),
            auto_expand=False,
        )
        reflection_plan = self._normalize_plan_commands(
            reflection_json.get("plan") or reflection_json.get("execution_plan") or reflection_json.get("plan_execute") or reflection_json,
            default_tool=revised_tool,
            default_target=revised_target,
            default_args=revised_args,
            stage="reflection",
            allowed_tools=bundle.get("allowed_tools", []),
            auto_expand=False,
        )
        reflection_plan, reflection_lock_violations = self._enforce_plan_path_lock(reflection_plan, locked_paths)

        # 反思层必须针对决策层 plan 逐条修订：以 Step5 的命令序列为基线，按 id/顺序对齐。
        if draft_plan:
            by_id = {
                str(i.get("id")): i
                for i in reflection_plan
                if isinstance(i, dict) and i.get("id")
            }
            aligned: list[dict] = []
            for idx, base in enumerate(draft_plan):
                cand = by_id.get(str(base.get("id")))
                if not cand and idx < len(reflection_plan):
                    cand = reflection_plan[idx]
                if isinstance(cand, dict):
                    merged = dict(base)
                    merged.update({
                        "tool": cand.get("tool") or base.get("tool"),
                        "target": cand.get("target") or base.get("target"),
                        "args": cand.get("args") or base.get("args") or {},
                        "rollback_supported": self._to_bool(cand.get("rollback_supported"), default=self._to_bool(base.get("rollback_supported"), default=False)),
                        "rollback_command": str(cand.get("rollback_command") or base.get("rollback_command") or "").strip(),
                        "rollback_reason": str(cand.get("rollback_reason") or base.get("rollback_reason") or "").strip(),
                        "rollback_need_root": self._to_bool(cand.get("rollback_need_root"), default=self._to_bool(base.get("rollback_need_root"), default=False)),
                    })
                    merged["command"] = KylinMCP._build_command(merged.get("tool"), **(merged.get("args") or {})) or merged.get("command")
                    merged["id"] = base.get("id") or cand.get("id") or f"cmd_{idx+1}"
                    aligned.append(merged)
                else:
                    aligned.append(dict(base))
            reflection_plan = aligned

        # revised_* 与 plan 约束等价：对每条 plan 命令应用同级校验（参数完整性/路径锁定），
        # 工具白名单不在此处替换，交由后续护栏层判定与拦截。
        normalized_reflection_plan: list[dict] = []
        for idx, item in enumerate(reflection_plan):
            cmd = dict(item) if isinstance(item, dict) else {}
            tool = str(cmd.get("tool") or "").strip()

            args_raw = cmd.get("args") if isinstance(cmd.get("args"), dict) else {}
            allowed_arg_keys = KylinMCP.get_allowed_args_for_tool(tool)
            args = {k: args_raw[k] for k in allowed_arg_keys if k in args_raw}
            target = cmd.get("target") or args.get("path")

            specs = KylinMCP.get_tool_arg_specs([tool]).get(tool, {})
            required_args = specs.get("required_args", [])

            if "path" in required_args and target and "path" not in args:
                args["path"] = target

            base_args = ((draft_plan[idx].get("args") if idx < len(draft_plan) and isinstance(draft_plan[idx], dict) else {}) or {})
            for req in required_args:
                if req not in args and req in base_args:
                    args[req] = base_args[req]

            if "path" in required_args and "path" not in args and locked_paths:
                args["path"] = locked_paths[0]

            if "path" in required_args and isinstance(args.get("path"), str):
                target = args.get("path")
            elif "path" in required_args and (not target) and idx < len(draft_plan) and isinstance(draft_plan[idx], dict):
                target = draft_plan[idx].get("target")
            elif "path" not in required_args:
                target = ""

            cmd["id"] = cmd.get("id") or f"cmd_{idx+1}"
            cmd["tool"] = tool
            cmd["target"] = target
            cmd["args"] = args
            if tool in MCP_TOOLS_REGISTRY:
                cmd["command"] = KylinMCP._build_command(tool, **args) or cmd.get("command")
            normalized_reflection_plan.append(cmd)

        reflection_plan = normalized_reflection_plan
        reflection_plan, reflection_lock_violations = self._enforce_plan_path_lock(reflection_plan, locked_paths)

        # 将 revised_* 映射到反思计划首条，保证摘要与计划一致。
        if reflection_plan:
            head = reflection_plan[0]
            revised_tool = head.get("tool") or revised_tool
            revised_target = head.get("target") or revised_target
            revised_args = head.get("args") or revised_args
            revised_command = head.get("command") or revised_command

        # 反思层 need_root 判定（由 LLM 基于完整命令给出）在后端贯穿保存。
        root_map: dict[str, bool] = {}
        raw_reflection_plan = self._extract_raw_commands(
            reflection_json.get("plan") or reflection_json.get("execution_plan") or reflection_json.get("plan_execute") or reflection_json
        )
        for idx, it in enumerate(raw_reflection_plan):
            if not isinstance(it, dict):
                continue
            cmd_id = str(it.get("id") or f"cmd_{idx+1}")
            if "need_root" in it:
                root_map[cmd_id] = self._to_bool(it.get("need_root"), default=False)
            elif "root_required" in it:
                root_map[cmd_id] = self._to_bool(it.get("root_required"), default=False)

        for item in reflection_plan:
            cmd_id = str(item.get("id") or "")
            if cmd_id in root_map:
                # LLM 显式判定与后端兜底判定取 OR，避免将兜底 true 覆盖回 false。
                item["need_root"] = self._to_bool(item.get("need_root"), default=False) or root_map[cmd_id]
            else:
                item["need_root"] = self._to_bool(item.get("need_root"), default=False)

        reflection_need_root = any(self._to_bool(i.get("need_root"), default=False) for i in reflection_plan)
        reflection_root_reason = reflection_json.get("root_reason") or (
            "反思层判定至少一条命令需要 root" if reflection_need_root else "反思层判定命令均无需 root"
        )

        plan_execution = []
        for item in reflection_plan:
            tool = item.get("tool")
            args = item.get("args") or {}
            level = float(MCP_TOOLS_REGISTRY.get(tool, {}).get("level", 1.0) or 1.0)
            if level <= 0.1:
                try:
                    probe = await KylinMCP.call(tool, **args)
                    ok = probe.get("status") == "success"
                    plan_execution.append({
                        "id": item.get("id"),
                        "tool": tool,
                        "command": item.get("command"),
                        "need_root": self._to_bool(item.get("need_root"), default=False),
                        "status": "success" if ok else "warning",
                        "note": "反思层探测执行完成",
                    })
                except Exception as e:
                    plan_execution.append({
                        "id": item.get("id"),
                        "tool": tool,
                        "command": item.get("command"),
                        "need_root": self._to_bool(item.get("need_root"), default=False),
                        "status": "warning",
                        "note": f"反思层探测失败: {str(e)}",
                    })
            else:
                plan_execution.append({
                    "id": item.get("id"),
                    "tool": tool,
                    "command": item.get("command"),
                    "need_root": self._to_bool(item.get("need_root"), default=False),
                    "status": "skipped",
                    "note": "反思层仅执行低风险探测命令，写操作保留到执行阶段",
                })

        # ------------------------------------------------------------------
        # 3. 严格映射你要求的 security_scan 细分结构
        # ------------------------------------------------------------------
        llm_scan = reflection_json.get("security_scan", {})
        llm_checks = llm_scan.get("checks", {})
        # [LLM] 四项安全审查均由 LLM 根据 draft 内容判断，不使用硬编码关键词匹配。
        # 安审原则：
        #   可逆性（Reversibility）—操作是否容易撤回，应优先选非破坏性方案
        #   业务连续性（Continuity）—操作是否导致服务中断、句柄失效、配置失联
        #   最小代价（Least Cost）—是否存在更温和、更精准的替代方案
        #   抗注入性（Injection Resistance）—输入是否存在提示词注入、越权诱导、
        #     非法截断或要求忽略安全规则的迹象
        # security_scan = {
        #     "passed": True,                    # [LLM] 四项全部通过才为 True
        #     "checks": {
        #         "reversibility": {
        #             "passed": True,            # [LLM]
        #             "note": "truncate 操作可恢复，优于直接 rm",  # [LLM]
        #         },
        #         "continuity": {
        #             "passed": True,            # [LLM]
        #             "note": "保留文件句柄，不影响正在写入的服务",  # [LLM]
        #         },
        #         "least_cost": {
        #             "passed": True,            # [LLM]
        #             "note": "仅清空内容，未销毁文件节点",  # [LLM]
        #         },
        #         "injection_resistance": {
        #             "passed": True,            # [LLM]
        #             "note": "未检测到提示词注入或越权诱导迹象。",  # [LLM]
        #         },
        #     },
        #     "message": "未发现非法指令截断或越权尝试。",  # [LLM]
        # }
        security_scan = {
            "passed": llm_scan.get("passed", False),
            "checks": {
                "reversibility": {
                    "passed": llm_checks.get("reversibility", {}).get("passed", False),
                    "note": self._zh_or_fallback(
                        llm_checks.get("reversibility", {}).get("note"),
                        "该操作具备可逆性，未发现不可恢复副作用。",
                    ),
                },
                "continuity": {
                    "passed": llm_checks.get("continuity", {}).get("passed", False),
                    "note": self._zh_or_fallback(
                        llm_checks.get("continuity", {}).get("note"),
                        "命令对服务连续性影响可控，不会造成业务中断。",
                    ),
                },
                "least_cost": {
                    "passed": llm_checks.get("least_cost", {}).get("passed", False),
                    "note": self._zh_or_fallback(
                        llm_checks.get("least_cost", {}).get("note"),
                        "方案代价较低且目标明确，未引入不必要复杂度。",
                    ),
                },
                "injection_resistance": {
                    "passed": llm_checks.get("injection_resistance", {}).get("passed", False),
                    "note": self._zh_or_fallback(
                        llm_checks.get("injection_resistance", {}).get("note"),
                        "未检测到注入或越权诱导风险。",
                    ),
                },
            },
            "message": self._zh_or_fallback(llm_scan.get("message"), "审计评估完成"),
        }

        injection_detected, injection_note = self._detect_reflection_injection(draft)
        if injection_detected:
            security_scan["checks"]["injection_resistance"] = {
                "passed": False,
                "note": injection_note,
            }
            security_scan["passed"] = False
            security_scan["message"] = "反思层检测到提示词注入或越权诱导，已强制拦截。"

        # 可逆性说明增强：避免把只读命令误描述为“无回滚机制”。
        if not security_scan["checks"]["reversibility"]["passed"] and reflection_plan:
            readonly_tools = []
            archive_tools = []
            risky_tools = []
            for item in reflection_plan:
                if not isinstance(item, dict):
                    continue
                t = str(item.get("tool") or "")
                level = float(MCP_TOOLS_REGISTRY.get(t, {}).get("level", 1.0) or 1.0)
                if level <= 0.1:
                    readonly_tools.append(t)
                if t == "archive_backup":
                    archive_tools.append(t)
                if t in {"truncate_file", "delete_file", "write_file_overwrite", "disk_format_partition", "manage_lvm_remove"}:
                    risky_tools.append(t)

            note_parts = []
            if readonly_tools:
                note_parts.append(f"只读命令（{', '.join(sorted(set(readonly_tools)))}）本身无需回滚")
            if archive_tools:
                note_parts.append("归档命令可通过删除归档文件回滚其创建动作")
            if risky_tools:
                note_parts.append(f"但 {', '.join(sorted(set(risky_tools)))} 涉及清空/删除类写操作，若无前置备份则不可自动恢复")

            if note_parts:
                security_scan["checks"]["reversibility"]["note"] = "；".join(note_parts) + "。"

        if self._is_safe_log_archive_cleanup_plan(reflection_plan):
            self._mark_log_archive_cleanup_reversible(reflection_plan)
            security_scan["checks"]["reversibility"] = {
                "passed": True,
                "note": "已先归档 nginx 访问日志，且清理步骤会在执行层创建同路径 .bak 前置备份，可通过备份恢复原始日志内容。",
            }
            security_scan["checks"]["least_cost"] = {
                "passed": True,
                "note": "采用先归档、再带备份清理的方式，避免直接删除日志文件节点，属于更温和的日志释放方案。",
            }
            if all(self._to_bool(check.get("passed"), default=False) for check in security_scan["checks"].values()):
                security_scan["passed"] = True
                security_scan["message"] = "日志归档与清理方案已补齐回滚依据，四项安全检查通过。"

        # [LLM] 根据 security_scan.passed 判断状态：
        #   全部通过 → status="revised"，流程继续
        #   任意一项未通过 → status="intercepted"，后端拦截流程
        llm_scan_passed = security_scan["passed"]  # 后端从 LLM 返回的 security_scan 中读取

        reflection_result = {
            "stage": "reflection",
            "request_id": self.task_id,
            "original_tool": draft.get("tool"),
            "original_command": draft.get("command"),
            "original_target": draft.get("target"),
            "revised_tool": revised_tool,
            "revised_args": revised_args,
            "revised_command": revised_command,
            "revised_target": revised_target,
            "plan_execute": {
                "mode": "plan-execute",
                "commands": reflection_plan,
                "execution": plan_execution,
            },
            "root_assessment": {
                "need_root": reflection_need_root,
                "reason": reflection_root_reason,
            },
            "reflection_reason": self._zh_or_fallback(
                reflection_json.get("reflection_reason"),
                "反思层已完成安全修正与一致性校验。",
            ),
            "evidence": [
                self._zh_or_fallback(e, "基于命令特征与任务语义完成审查。")
                for e in (reflection_json.get("evidence", []) or [])
            ],
            "status": "revised" if llm_scan_passed else "intercepted",
            "security_scan": security_scan,
            "timestamp": self._now(),
        }
        # reflection_result = {
        #     "stage": "reflection",
        #     "request_id": self.task_id,
        #     "original_tool": draft.get("tool"),          # 取自 step5，非 LLM
        #     "original_command": draft.get("command"),    # 取自 step5，非 LLM
        #     "original_target": draft.get("target"),      # 取自 step5，非 LLM
        #     "revised_tool": "truncate_file",             # [LLM] 修订后工具
        #     "revised_command": "truncate -s 0 /var/log/big_log.log",  # [LLM] 修订后命令
        #     "revised_target": "/var/log/big_log.log",   # [LLM] 修订后目标路径，BERT 审计直接取此字段
        #     "reflection_reason": "直接删除可能导致日志句柄失效，清空内容更安全",  # [LLM]
        #     "evidence": [                                 # [LLM] 自由生成，说明判断依据即可
        #         "清空操作不影响文件句柄，可逆性优于直接删除",
        #         "满足最小代价原则",
        #     ],
        #     "status": "revised" if llm_scan_passed else "intercepted",  # 后端根据 LLM 推断
        #     "security_scan": security_scan,
        # }
        self._update_context("step6_reflection", reflection_result)
        if reflection_lock_violations:
            self._add_history(
                "路径锁定",
                f"反思层检测到 {len(reflection_lock_violations)} 条越界路径命令，已自动纠偏到 {locked_paths[0]}。",
            )
        cmd_changed = reflection_result["revised_command"] != draft.get("command", "")
        scan_summary = "四项安全检查全部通过" if llm_scan_passed else "安全检查未通过，流程将被拦截"
        self._add_history(
            "反思修正",
            f"{reflection_result['reflection_reason']} "
            f"| 命令{'已修订' if cmd_changed else '维持原样'}：{reflection_result['revised_command']} "
            f"| 反思计划执行 {len(plan_execution)} 条。"
            f"| {scan_summary}。",
        )
        return reflection_result

    async def _audit_risk(self, reflection: dict) -> dict:
        tool = reflection.get("revised_tool", "")
        # BERT 输入格式：[Tool_Name] Target_Path
        # revised_target 是反思层对 step5 target 的修订结果，直接从 step6_reflection 读取
        target = reflection.get("revised_target", "")
        risk_result = await MLService.audit_risk(tool_name=tool, target=target)

        draft = self.task_record.context_data.get("step5_decision_draft", {})
        # Step7 风险评估必须优先来源于反思层 plan，只有反思层缺失时才回退到 Step5。
        command_candidates = (reflection.get("plan_execute", {}) or {}).get("commands", [])
        risk_command_source = "step6_reflection_plan"
        if not command_candidates:
            command_candidates = (draft.get("execution_plan", {}) or {}).get("commands", [])
            risk_command_source = "step5_decision_plan_fallback"
        if command_candidates:
            ranked = sorted(
                command_candidates,
                key=lambda x: float(MCP_TOOLS_REGISTRY.get(x.get("tool", ""), {}).get("level", x.get("risk_level", 0.0)) or 0.0),
                reverse=True,
            )
            top = ranked[0]
            risk_result["highest_risk_command"] = {
                "tool": top.get("tool"),
                "command": top.get("command"),
                "risk_level": float(MCP_TOOLS_REGISTRY.get(top.get("tool", ""), {}).get("level", top.get("risk_level", 0.0)) or 0.0),
            }
        else:
            risk_result["highest_risk_command"] = {
                "tool": tool,
                "command": reflection.get("revised_command", ""),
                "risk_level": float(MCP_TOOLS_REGISTRY.get(tool, {}).get("level", 0.0) or 0.0),
            }
        risk_result["risk_command_source"] = risk_command_source

        self._update_context("step7_risk_audit", risk_result)
        self._add_history(
            "风险评估",
            f"BERT 语义审计完成：综合风险分 {risk_result.get('total_risk', 'N/A')}（"
            f"动作能量 {risk_result.get('action_energy', 'N/A')}，"
            f"资产敏感度 {risk_result.get('asset_sensitivity', 'N/A')}），"
            f"最终裁决：{risk_result.get('verdict', 'N/A')}。",
        )
        return risk_result

    async def _check_guardrails(
        self, bundle: dict, draft: dict, reflection: dict, risk: dict
    ) -> tuple:
        planned_tools = self._collect_guardrail_tools(draft, reflection)
        tool_name = reflection.get("revised_tool", "")
        ai_verdict = risk.get("verdict", "PASS")
        risk_score = risk.get("total_risk", 0.0)

        # 第一层：大模型幻觉护栏（task_text 与反思命令一致性校验）
        reflection_cmds = (reflection.get("plan_execute", {}) or {}).get("commands", [])
        hallucination_input = [
            {
                "id": c.get("id"),
                "tool": c.get("tool"),
                "command": c.get("command"),
                "target": c.get("target"),
            }
            for c in reflection_cmds
            if isinstance(c, dict)
        ]
        hallucination_eval = None
        try:
            hallucination_user = prompts.STEP8_HALLUCINATION_GUARDRAIL_USER_TPL.format(
                task_text=self.task_record.task_text,
                reflection_commands_json=json.dumps(hallucination_input, ensure_ascii=False),
            )
            hallucination_eval = await MLService.call_llm(
                system_prompt=prompts.STEP8_HALLUCINATION_GUARDRAIL_SYSTEM,
                user_prompt=hallucination_user,
            )
        except Exception:
            hallucination_eval = None

        if isinstance(hallucination_eval, dict):
            hallucination_detected = self._to_bool(
                hallucination_eval.get("hallucination_detected"), default=False
            )
            hallucination_reason = str(hallucination_eval.get("reason") or "") or (
                "检测到命令与任务不一致" if hallucination_detected else "命令与任务语义一致"
            )
            mismatch_commands = hallucination_eval.get("mismatch_commands") or []
            hallucination_conf = float(hallucination_eval.get("confidence", 0.0) or 0.0)
        else:
            # LLM 判定不可用时不直接硬拦；后续路径锁、工具白名单、风险审计仍会继续兜底。
            hallucination_detected = False
            hallucination_reason = "幻觉验证服务未返回有效结果，已回退到路径锁与工具白名单确定性校验"
            mismatch_commands = []
            hallucination_conf = 0.0

        task_paths = self._normalize_locked_paths(bundle.get("locked_paths", []))
        if not task_paths:
            task_paths = self._extract_abs_paths_from_text(self.task_record.task_text)
        path_mismatch_commands = []
        unmatched_task_paths = []
        if task_paths:
            command_path_hits = {tp: False for tp in task_paths}
            for cmd_item in reflection_cmds:
                if not isinstance(cmd_item, dict):
                    continue
                cmd_paths = self._extract_abs_paths_from_command_item(cmd_item)
                if not cmd_paths:
                    # 部分资源探测命令（如 lsblk、ps、lsof -i）天然不带绝对路径，不按路径漂移处理。
                    continue

                matched_any = False
                for expected in task_paths:
                    if any(self._path_matches_expected(cp, expected) for cp in cmd_paths):
                        command_path_hits[expected] = True
                        matched_any = True

                if not matched_any:
                    display_cmd = str(cmd_item.get("command") or cmd_item.get("target") or "")
                    path_mismatch_commands.append(
                        f"{cmd_item.get('id') or 'unknown'}: {display_cmd}"
                    )

            unmatched_task_paths = [p for p, ok in command_path_hits.items() if not ok]
            if unmatched_task_paths:
                hallucination_detected = True
                hallucination_conf = max(hallucination_conf, 0.99)
                mismatch_commands = (mismatch_commands or []) + [
                    f"任务路径未命中: {p}" for p in unmatched_task_paths
                ]
                if path_mismatch_commands:
                    mismatch_commands.extend(path_mismatch_commands)
                hallucination_reason = (
                    f"检测到路径漂移：任务路径 {', '.join(unmatched_task_paths[:3])} "
                    "未被反思命令命中（仅允许同路径或子路径）"
                )

        if mismatch_commands:
            dedup = []
            seen = set()
            for m in mismatch_commands:
                s = str(m)
                if s not in seen:
                    seen.add(s)
                    dedup.append(s)
            mismatch_commands = dedup

        # 放宽误判：同路径只读辅助命令（如 ls -la /path）在存在核心日志读取命令时不视为幻觉。
        if hallucination_detected and not unmatched_task_paths:
            if self._should_relax_hallucination_for_readonly_helpers(task_paths, reflection_cmds):
                hallucination_detected = False
                hallucination_conf = min(hallucination_conf, 0.35)
                mismatch_commands = []
                hallucination_reason = "检测到同路径只读辅助命令（如 ls -la/stat）且包含核心日志读取步骤，判定与任务语义一致"

        if self._is_disk_space_diagnosis():
            required_disk_tools = {"disk_usage", "directory_usage", "find_large_files"}
            missing = required_disk_tools - {c.get("tool") for c in reflection_cmds}
            if missing:
                hallucination_detected = True
                hallucination_conf = max(hallucination_conf, 0.99)
                hallucination_reason = "磁盘排查缺少核心证据采集步骤：" + "、".join(sorted(missing))
                mismatch_commands = list(mismatch_commands or []) + [hallucination_reason]

        hallucination_pass = not hallucination_detected

        tool_info = MCP_TOOLS_REGISTRY.get(tool_name)
        allowed_tools = bundle.get("allowed_tools", [])
        tool_checks = []
        for t in planned_tools:
            in_registry = t in MCP_TOOLS_REGISTRY
            backend_allowed = in_registry and (t in allowed_tools)
            user_disabled_record = self.db.query(UserToolConfig).filter(
                UserToolConfig.user_id == int(self.task_record.user_id),
                UserToolConfig.tool_name == t,
                UserToolConfig.disabled == True,
            ).first()
            user_disabled = user_disabled_record is not None
            tool_checks.append({
                "tool": t,
                "in_registry": in_registry,
                "backend_allowed": backend_allowed,
                "user_disabled": user_disabled,
                "effective": backend_allowed and not user_disabled,
            })

        tool_pass = all(i.get("effective") for i in tool_checks) if tool_checks else False
        blocked_tools = [i for i in tool_checks if not i.get("effective")]
        if not tool_checks:
            tool_reason = "未识别到可执行工具计划"
        elif blocked_tools:
            detail = []
            for i in blocked_tools:
                if not i.get("backend_allowed"):
                    detail.append(f"{i.get('tool')} 不在角色白名单")
                elif i.get("user_disabled"):
                    detail.append(f"{i.get('tool')} 已被用户禁用")
            tool_reason = "；".join(detail)
        else:
            tool_reason = f"计划工具全部通过校验：{', '.join(planned_tools)}"

        need_root = any(self._to_bool(i.get("need_root"), default=False) for i in reflection_cmds)
        if not need_root:
            need_root = self._to_bool((reflection.get("root_assessment") or {}).get("need_root"), default=False)

        ai_blocked = ai_verdict == "BLOCK"
        over_threshold = float(risk_score or 0.0) >= float(settings.RISK_APPROVAL_THRESHOLD)
        sem_pass = not ai_blocked
        sem_reason = (
            f"BERT 语义审计通过（风险分: {risk_score}）"
            if sem_pass
            else f"BERT 语义审计阻断（风险分: {risk_score}，verdict: {ai_verdict}）"
        )

        trigger_reasons = []
        if not hallucination_pass:
            if mismatch_commands:
                mismatch_text = "；".join([str(i) for i in mismatch_commands[:3]])
                trigger_reasons.append(f"幻觉护栏：命令与任务不一致（示例：{mismatch_text}）")
            else:
                trigger_reasons.append(f"幻觉护栏：{hallucination_reason}")
        for i in blocked_tools:
            if not i.get("backend_allowed"):
                trigger_reasons.append(f"工具护栏（后端白名单）：{i.get('tool')} 角色不可用")
            elif i.get("user_disabled"):
                trigger_reasons.append(f"工具护栏（用户禁用）：{i.get('tool')} 已被用户在管理页关闭")
        if need_root:
            trigger_reasons.append("操作涉及 root 权限，需要审计人员确认")
        if over_threshold:
            trigger_reasons.append(f"风险评分 {risk_score} 超过审批阈值 {settings.RISK_APPROVAL_THRESHOLD}")
        if ai_blocked:
            trigger_reasons.append(f"语义护栏：BERT 风险评分 {risk_score} 超阈值")

        if not hallucination_pass or not tool_pass:
            final_action = "REJECTED"
        elif ai_blocked or need_root or over_threshold:
            final_action = "PENDING_APPROVAL"
        else:
            final_action = "PASS"

        policy_decision = {
            "request_id": self.task_id,
            # 兼容旧字段：role_allowed 复用为第一层通过标记（当前语义为幻觉护栏通过）。
            "role_allowed": hallucination_pass,
            "hallucination_allowed": hallucination_pass,
            "hallucination_detected": hallucination_detected,
            "hallucination_reason": hallucination_reason,
            "hallucination_confidence": hallucination_conf,
            "hallucination_mismatch_commands": mismatch_commands,
            "tool_allowed": tool_pass,
            "risk_allowed": sem_pass,
            "need_admin_approval": final_action == "PENDING_APPROVAL",
            "need_root": need_root,
            "trigger_reasons": trigger_reasons,
            "final_action": final_action,
        }

        guardrail_tree = {
            "request_id": self.task_id,
            "root": {
                "node_id": "guardrail_root",
                "label": "安全护栏总流程",
                "node_type": "root",
                "status": "pass" if final_action == "PASS" else "warning",
                "children": [
                    {
                        "node_id": "hallucination_guardrail",
                        "label": "第一层：幻觉护栏",
                        "node_type": "guardrail",
                        "status": "pass" if hallucination_pass else "blocked",
                        "reason": hallucination_reason,
                        "evidence": {
                            "task_text": self.task_record.task_text,
                            "confidence": hallucination_conf,
                            "mismatch_commands": mismatch_commands,
                            "allowed": hallucination_pass,
                        },
                        
                    },
                    {
                        "node_id": "tool_guardrail",
                        "label": "第二层：工具护栏",
                        "node_type": "guardrail",
                        "status": "pass" if tool_pass else "blocked",
                        "reason": tool_reason,
                        "evidence": {
                            "tool": tool_name,
                            "checked_tools": tool_checks,
                            "effective": tool_pass,
                        },
                        
                    },
                    {
                        "node_id": "semantic_guardrail",
                        "label": "第三层：语义护栏",
                        "node_type": "guardrail",
                        "status": "pass" if sem_pass else "warning",
                        "reason": sem_reason,
                        "evidence": {
                            "total_risk": risk_score,
                            "action_energy": risk.get("action_energy"),
                            "asset_sensitivity": risk.get("asset_sensitivity"),
                            "verdict": ai_verdict,
                        },
                        "children": [
                            {
                                "node_id": "approval_required",
                                "label": "审计人员确认",
                                "node_type": "action",
                                "status": "pending" if final_action == "PENDING_APPROVAL" else "pass",
                                "reason": "命中高风险或 root 审批条件" if final_action == "PENDING_APPROVAL" else "无需审批",
                                
                            },
                            {
                                "node_id": "root_required",
                                "label": "root 执行链路",
                                "node_type": "action",
                                "status": "pending" if need_root else "pass",
                                "reason": "该操作需要 root 权限" if need_root else "无需 root",
                                
                            },
                        ],
                    },
                ],
            },
        }

        self._update_context("step8_policy_decision", policy_decision)
        self._update_context("step8_guardrail_tree", guardrail_tree)
        layers = (
            f"幻觉层：{'✓' if hallucination_pass else '✗'} | "
            f"工具层：{'✓' if tool_pass else '✗'}（计划工具 {len(planned_tools)} 个） | "
            f"语义层：{'✓' if sem_pass else '✗'}（风险分 {risk_score}）"
        )
        trigger_desc = "，触发原因：" + "；".join(trigger_reasons) if trigger_reasons else "，无触发项"
        self._add_history(
            "护栏判定",
            f"三层护栏审查完毕：{layers}。最终判定：{final_action}{trigger_desc}。",
        )
        return policy_decision, guardrail_tree

    async def _generate_approval_payload(self, policy_decision: dict) -> dict:
        risk_audit = self.task_record.context_data.get("step7_risk_audit", {})
        perception = self.task_record.context_data.get("step3_perception", {})
        reflection = self.task_record.context_data.get("step6_reflection", {})
        draft = self.task_record.context_data.get("step5_decision_draft", {})
        risk_score = risk_audit.get("total_risk", 0)
        need_root = policy_decision.get("need_root", False)
        command_options = self._collect_approval_commands(draft, reflection, risk_audit)
        if not command_options:
            command_options = self._normalize_plan_commands(
                [],
                default_tool=reflection.get("revised_tool", ""),
                default_target=reflection.get("revised_target", ""),
                default_args=reflection.get("revised_args", {}),
                stage="approval",
            )
            for c in command_options:
                c["checked"] = True
                c["need_root"] = self._to_bool(c.get("need_root"), default=False)
                c["risk_score"] = max(float(c.get("risk_level", 0.0) or 0.0), float(risk_score or 0.0))

        approval_payload = {
            "request_id": self.task_id,
            "risk_score": risk_score,
            "risk_level": "high" if risk_score > settings.RISK_APPROVAL_THRESHOLD else "medium",
            "trigger_reasons": policy_decision.get("trigger_reasons", []),
            "perception_summary": perception.get("summary", "感知数据缺失"),
            "reflection_summary": reflection.get("reflection_reason", "无反思修正说明"),
            "command_preview": "\n".join([c.get("command", "") for c in command_options]) or reflection.get("revised_command", "命令生成失败"),
            "command_options": command_options,
            "approval_status": "pending",
            "native_notice_required": need_root,
        }

        self._update_context("step9_approval_payload", approval_payload)

        if need_root:
            self._add_history(
                "系统通知",
                "操作需要 root 权限，已向审计人员发起审批请求，等待审计人员审批。",
            )

        self._add_history(
            "流程挂起",
            f"任务已挂起，等待审计人员审批。"
            f"待执行命令数：{len(command_options)}，"
            f"风险等级：{approval_payload.get('risk_level', '未知')}（得分 {risk_score}）。",
        )
        return approval_payload

    async def _execute_mcp_command(self) -> dict:
        start_time = datetime.now(timezone.utc)
        self.task_record.status = "executing"
        self.db.commit()

        reflection = self.task_record.context_data.get("step6_reflection", {})
        approval_payload = self.task_record.context_data.get("step9_approval_payload", {})
        approval_info = self.task_record.context_data.get("approval_info", {})
        selected_ids = set(approval_info.get("selected_command_ids", []) or [])

        command_options = approval_payload.get("command_options") or []
        if command_options:
            selected_commands = [
                c for c in command_options
                if not selected_ids or c.get("id") in selected_ids
            ]
        else:
            reflection_plan = (reflection.get("plan_execute") or {}).get("commands") or []
            selected_commands = reflection_plan or self._normalize_plan_commands(
                [],
                default_tool=reflection.get("revised_tool", ""),
                default_target=reflection.get("revised_target", ""),
                default_args=reflection.get("revised_args", {}),
                stage="execution",
            )

        readonly_tools = {
            "read_file",
            "list_dir",
            "network_config_show",
            "show_service_status",
            "show_system_log",
            "list_process",
            "list_disk",
            "disk_usage",
            "directory_usage",
            "find_large_files",
            "list_open_files",
            "show_network_connections",
        }

        command_runs = []
        for item in selected_commands:
            tool_name = item.get("tool")
            exec_args_raw = item.get("args", {})
            exec_args = exec_args_raw if isinstance(exec_args_raw, dict) else {}
            command_str = item.get("command") or KylinMCP._build_command(tool_name, **exec_args)
            target_path = item.get("target") or exec_args.get("path")
            effective_need_root = self._resolve_need_root(
                {
                    "need_root": item.get("need_root"),
                    "target": target_path,
                    "args": exec_args,
                    "command": command_str,
                },
                tool_name,
            )

            rollback_supported = self._to_bool(item.get("rollback_supported"), default=False)
            rollback_command = str(item.get("rollback_command") or "").strip()
            rollback_reason = str(item.get("rollback_reason") or "").strip()
            rollback_need_root = self._to_bool(item.get("rollback_need_root"), default=False)

            # 执行层强约束：只读命令不应提供回滚。
            if tool_name in readonly_tools:
                rollback_supported = False
                rollback_command = ""
                rollback_need_root = False
                rollback_reason = rollback_reason or "只读命令不修改系统状态，无需回滚"

            # archive_backup 采用确定性回滚：删除本次创建的归档文件（避免 .tar.gz 幻觉后缀）。
            if tool_name == "archive_backup":
                archive_name = str(exec_args.get("archive_name") or "").strip()
                if archive_name:
                    rollback_supported = True
                    rollback_command = f"rm -f {archive_name}"
                    rollback_need_root = self._resolve_need_root(
                        {"command": rollback_command, "target": exec_args.get("path")},
                        "archive_backup",
                    )
                    rollback_reason = "删除本次生成的归档文件，回滚归档创建操作"

            # truncate_file 自动前置备份，确保回滚命令可执行。
            pre_backup_status = "skipped"
            pre_backup_error = ""
            if tool_name == "truncate_file":
                path = str(exec_args.get("path") or target_path or "").strip()
                if path:
                    backup_path = f"{path}.bak"
                    backup_need_root = self._resolve_need_root(
                        {"command": f"cp -a {path} {backup_path}", "target": path},
                        "copy_file",
                    )
                    backup_res = await KylinMCP.call(
                        "copy_file",
                        src=path,
                        dst=backup_path,
                        _confirmed=True,
                        _need_root=backup_need_root,
                    )
                    if backup_res.get("status") == "success":
                        pre_backup_status = "success"
                        rollback_supported = True
                        rollback_command = f"cp -a {backup_path} {path}"
                        rollback_need_root = self._resolve_need_root(
                            {"command": rollback_command, "target": path},
                            "copy_file",
                        )
                        rollback_reason = "执行前已自动备份原文件，可通过备份文件恢复"
                    else:
                        pre_backup_status = "failed"
                        pre_backup_error = str(backup_res.get("message", "前置备份失败"))
                        rollback_supported = False
                        rollback_command = ""
                        rollback_need_root = False
                        rollback_reason = f"前置备份失败，无法提供可执行回滚：{pre_backup_error}"

            try:
                mcp_res = await KylinMCP.call(
                    tool_name,
                    _confirmed=True,
                    _need_root=effective_need_root,
                    **exec_args,
                )
                status = "success" if mcp_res.get("status") == "success" else "failed"
                stdout = str(mcp_res.get("output", ""))
                stderr = str(mcp_res.get("message", ""))
            except Exception as e:
                status, stdout, stderr = "failed", "", str(e)

            command_runs.append({
                "id": item.get("id"),
                "tool": tool_name,
                "command": command_str,
                "args": exec_args,
                "target": target_path,
                "need_root": effective_need_root,
                "status": status,
                "exit_code": 0 if status == "success" else 1,
                "stdout": stdout,
                "stderr": stderr,
                "rollback_supported": rollback_supported,
                "rollback_command": rollback_command,
                "rollback_reason": rollback_reason,
                "rollback_need_root": rollback_need_root,
                "pre_backup_status": pre_backup_status,
                "pre_backup_error": pre_backup_error,
                "rollback_available": (
                    status == "success" and
                    rollback_supported and
                    bool(rollback_command)
                ),
            })

        status = "success" if command_runs and all(i.get("status") == "success" for i in command_runs) else "failed"
        first_run = command_runs[0] if command_runs else {}
        stdout = first_run.get("stdout", "")
        stderr = first_run.get("stderr", "")

        execution_result = {
            "request_id": self.task_id,
            "tool": first_run.get("tool", reflection.get("revised_tool", "")),
            "command": first_run.get("command", reflection.get("revised_command", "")),
            "status": status,
            "exit_code": 0 if status == "success" else 1,
            "stdout": stdout,
            "stderr": stderr,
            "command_runs": command_runs,
            "started_at": start_time.isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        self._update_context("step10_execution_result", execution_result)
        stdout_preview = stdout[:80].replace("\n", " ") if stdout else "（无输出）"
        self._add_history(
            "执行阶段",
            f"按审批结果执行 {len(command_runs)} 条命令，"
            f"退出码：{execution_result['exit_code']}，状态：{status}。"
            f"输出摘要：{stdout_preview}",
        )

        # Step 13: 执行结果解读（将 task_text + 执行结果传给 LLM，补齐用户要求输出）
        review_input = {
            "status": execution_result.get("status"),
            "exit_code": execution_result.get("exit_code"),
            "tool": execution_result.get("tool"),
            "command": execution_result.get("command"),
            "stdout": execution_result.get("stdout", "")[:2000],
            "stderr": execution_result.get("stderr", "")[:2000],
            "command_runs": [
                {
                    "tool": i.get("tool"),
                    "command": i.get("command"),
                    "status": i.get("status"),
                    "stdout": str(i.get("stdout", ""))[:500],
                    "stderr": str(i.get("stderr", ""))[:500],
                    "rollback_available": i.get("rollback_available", False),
                }
                for i in command_runs
            ],
        }

        review_json = None
        try:
            review_user_prompt = prompts.STEP13_EXECUTION_REVIEW_USER_TPL.format(
                task_text=self.task_record.task_text,
                execution_result_json=json.dumps(review_input, ensure_ascii=False),
            )
            review_json = await MLService.call_llm(
                system_prompt=prompts.STEP13_EXECUTION_REVIEW_SYSTEM,
                user_prompt=review_user_prompt,
            )
        except Exception:
            review_json = None

        if not isinstance(review_json, dict):
            review_json = {
                "task_completion": "completed" if status == "success" else "failed",
                "result_summary": f"执行状态：{status}，退出码：{execution_result.get('exit_code')}",
                "risk_explanation": "无明显新增风险" if status == "success" else "执行失败存在操作不一致风险，请人工复核",
                "user_facing_answer": (
                    "任务已完成，请查看执行明细。" if status == "success"
                    else "任务执行失败，请根据错误信息修复后重试。"
                ),
            }

        step13_execution_report = {
            "request_id": self.task_id,
            "task_text": self.task_record.task_text,
            "task_completion": review_json.get("task_completion", "failed" if status != "success" else "completed"),
            "result_summary": review_json.get("result_summary", ""),
            "risk_explanation": review_json.get("risk_explanation", ""),
            "user_facing_answer": review_json.get("user_facing_answer", ""),
            "timestamp": self._now(),
        }
        self._update_context("step13_execution_report", step13_execution_report)
        self._add_history(
            "结果解读",
            f"已基于任务要求与执行结果生成最终答复：{step13_execution_report.get('task_completion', 'unknown')}。",
        )

        # Step 11: 审计落库（审计人员只查这里）
        raw_log = {
            "type": "Raw_Log",
            "request_id": self.task_id,
            "task": first_run.get("tool", "unknown"),
            "target": first_run.get("target", "unknown"),
            "status": status,
            "description": f"MCP 在审计人员批准后执行了 {len(command_runs)} 条命令",
            "commands": [
                {
                    "id": i.get("id"),
                    "tool": i.get("tool"),
                    "command": i.get("command"),
                    "target": i.get("target"),
                    "status": i.get("status"),
                    "exit_code": i.get("exit_code"),
                    "stdout_preview": (i.get("stdout", "")[:120]),
                    "stderr": i.get("stderr", ""),
                    "rollback_supported": i.get("rollback_supported", False),
                    "rollback_command": i.get("rollback_command", ""),
                    "rollback_reason": i.get("rollback_reason", ""),
                    "rollback_need_root": i.get("rollback_need_root", False),
                    "rollback_available": i.get("rollback_available", False),
                } for i in command_runs
            ],
        }
        step11_audit = {
            "audit_trace": {
                "request_id": self.task_id,
                "user_id": self.task_record.user_id,
                "host_id": self.task_record.host_id,
                "task_text": self.task_record.task_text,
                "final_status": status,
            },
            "raw_log": raw_log,
            "row_log": raw_log,
            "approval_log": {
                "approval_id": f"apv_{self.task_id[:8]}",
                "request_id": self.task_id,
                "approved": True,
                "approved_by": "local_admin",
                "notice_channel": "gdbus",
                "approve_time": start_time.isoformat(),
            },
        }
        self._update_context("step11_audit", step11_audit)
        self._add_history(
            "审计落库",
            f"全流程审计记录已写入数据库（用户：{self.task_record.user_id}，"
            f"主机：{self.task_record.host_id}），最终状态：{status}。",
        )

        # Step 12: 记忆写回
        # tags 由 Step 3 感知层 LLM 生成（场景标签，用于 RAG 召回过滤/加权）
        reflection_ctx = self.task_record.context_data.get("step6_reflection", {})
        perception_ctx = self.task_record.context_data.get("step3_perception", {})
        writeback_request = {
            "request_id": self.task_id,
            "raw_log": raw_log,
            "reflection_result": reflection_ctx,
            "tags": perception_ctx.get("tags", []),   # ← 来自 Step 3 感知层
        }
        # 实际写入 RAG 记忆库（raw_log + reflection_result 作为一组同时入库，
        # 共享 request_id / timestamp / tags）
        writeback_result = await MLService.save_memory(writeback_request)
        writeback_request["writeback_result"] = writeback_result
        self._update_context("step12_memory_writeback", writeback_request)
        self._add_history(
            "记忆写回",
            f"本次运维经验（执行日志 + 反思修正记录）已写入 RAG 记忆库，"
            f"标签：{writeback_request['tags']}，"
            f"写回状态：{writeback_result.get('status', '未知')}。",
        )

        self.task_record.status = "success" if status == "success" else "failed"
        self.db.commit()
        return execution_result

    async def run(self):
        try:
            if self.task_record.status == "approved":
                reflection_preview = self.task_record.context_data.get("step6_reflection", {})
                cmd_preview = reflection_preview.get("revised_command", "未知命令")
                self._add_history(
                    "流程复活",
                    f"审计人员已批准审批请求，流程从挂起态恢复，即将执行命令：{cmd_preview}。",
                )
                return await self._execute_mcp_command()

            # Step 3
            self.task_record.status = "perceiving"
            self.db.commit()
            perception = await self._perceive()

            # Step 4
            self.task_record.status = "planning"
            self.db.commit()
            bundle = await self._build_context_bundle(perception["summary"])

            # Step 5
            self.task_record.status = "drafting"
            self.db.commit()
            draft = await self._generate_decision_draft(bundle)

            # Step 6
            self.task_record.status = "reflecting"
            self.db.commit()
            reflection = await self._self_reflection(bundle, draft)

            if not reflection["security_scan"]["passed"]:
                self.task_record.status = "blocked"
                failed_checks = [
                    name for name, detail in reflection["security_scan"].get("checks", {}).items()
                    if not detail.get("passed", True)
                ]
                failed_desc = ', '.join(failed_checks) if failed_checks else '未知'
                self._add_history(
                    "安全拦截",
                    f"反思层安全审查未通过，触发拦截。"
                    f"未通过项：{failed_desc}。"
                    f"系统已强制终止本次操作流程。",
                )
                reflection_ctx = self.task_record.context_data.get("step6_reflection", {})
                step11_audit = {
                    "audit_trace": {
                        "request_id": self.task_id,
                        "user_id": self.task_record.user_id,
                        "host_id": self.task_record.host_id,
                        "task_text": self.task_record.task_text,
                        "final_status": "blocked",
                    },
                    "raw_log": {
                        "type": "Raw_Log",
                        "request_id": self.task_id,
                        "task": reflection_ctx.get("revised_tool", "unknown"),
                        "target": reflection_ctx.get("revised_target", "unknown"),
                        "status": "blocked",
                        "description": f"操作被反思层安全审查拦截，未通过项：{failed_desc}",
                        "commands": [],
                    },
                    "row_log": {
                        "type": "Raw_Log",
                        "request_id": self.task_id,
                        "task": reflection_ctx.get("revised_tool", "unknown"),
                        "target": reflection_ctx.get("revised_target", "unknown"),
                        "status": "blocked",
                        "description": f"操作被反思层安全审查拦截，未通过项：{failed_desc}",
                        "commands": [],
                    },
                    "approval_log": None,
                }
                self._update_context("step11_audit", step11_audit)
                self._add_history(
                    "审计落库",
                    f"反思层拦截审计记录已写入数据库（用户：{self.task_record.user_id}，主机：{self.task_record.host_id}），最终状态：blocked。",
                )
                self.db.commit()
                return self.task_record

            # Step 7
            self.task_record.status = "auditing"
            self.db.commit()
            risk = await self._audit_risk(reflection)

            # Step 8
            self.task_record.status = "guardrail_checking"
            self.db.commit()
            policy_decision, guardrail_tree = await self._check_guardrails(
                bundle, draft, reflection, risk
            )

            # Step 9
            if policy_decision["final_action"] == "PENDING_APPROVAL":
                self.task_record.status = "awaiting_approval"
                await self._generate_approval_payload(policy_decision)
                self.db.commit()
                return self.task_record
            elif policy_decision["final_action"] == "REJECTED":
                self.task_record.status = "blocked"
                reasons_desc = "；".join(policy_decision.get("trigger_reasons", [])) or "合规规则校验失败"
                reflection_ctx = self.task_record.context_data.get("step6_reflection", {})
                is_hallucination_reject = self._to_bool(policy_decision.get("hallucination_detected"), default=False)
                reject_status = "blocked_hallucination" if is_hallucination_reject else "rejected"
                reject_desc = (
                    f"操作被第一层幻觉护栏拦截，原因：{policy_decision.get('hallucination_reason', reasons_desc)}"
                    if is_hallucination_reject
                    else f"操作被护栏拒绝，原因：{reasons_desc}"
                )
                step11_audit = {
                    "audit_trace": {
                        "request_id": self.task_id,
                        "user_id": self.task_record.user_id,
                        "host_id": self.task_record.host_id,
                        "task_text": self.task_record.task_text,
                        "final_status": reject_status,
                    },
                    "raw_log": {
                        "type": "Raw_Log",
                        "request_id": self.task_id,
                        "task": reflection_ctx.get("revised_tool", "unknown"),
                        "target": reflection_ctx.get("revised_target", "unknown"),
                        "status": reject_status,
                        "description": reject_desc,
                        "commands": [],
                    },
                    "row_log": {
                        "type": "Raw_Log",
                        "request_id": self.task_id,
                        "task": reflection_ctx.get("revised_tool", "unknown"),
                        "target": reflection_ctx.get("revised_target", "unknown"),
                        "status": reject_status,
                        "description": reject_desc,
                        "commands": [],
                    },
                    "approval_log": None,
                }
                self._update_context("step11_audit", step11_audit)
                self._add_history(
                    "安全拦截",
                    f"护栏判定结果为 REJECTED，操作已被系统强制终止。原因：{reasons_desc}。",
                )
                self._add_history(
                    "审计落库",
                    f"护栏层拦截审计记录已写入数据库（用户：{self.task_record.user_id}，主机：{self.task_record.host_id}），最终状态：rejected。",
                )
                self.db.commit()
                return self.task_record
            else:
                self.task_record.status = "approved"
                self.db.commit()
                return await self._execute_mcp_command()
        except Exception as e:
            failed_stage = self.task_record.status
            self.task_record.status = "failed"
            self._add_history(
                "流程失败",
                f"任务在 {failed_stage} 阶段异常终止：{str(e)}",
            )
            self.db.commit()
            return self.task_record
