"""Regression checks using an isolated database; no production seed data."""
import asyncio
from collections import deque
from datetime import datetime, timedelta
import os
from pathlib import Path
import secrets
import sys
import tempfile
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
TEMP = tempfile.TemporaryDirectory(prefix="kylin-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{TEMP.name}/test.db"
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["OPERATOR_REGISTER_KEY"] = secrets.token_urlsafe(24)
os.environ["AUDITOR_REGISTER_KEY"] = secrets.token_urlsafe(24)
sys.path.insert(0, str(ROOT / "program2"))
sys.path.insert(0, str(ROOT / "scripts"))

from fastapi.testclient import TestClient
from sqlalchemy import func, select

import main
import create_admin
from app.core.database import Base, SessionLocal, engine
from app.core.security import verify_password
from app.models.user import User
from app.services import monitor, rag_store
from app.services.ml_service import MLService
from app.services.monitor_center import MonitorCenter
from app.services.mcp_tools import KylinMCP, MCP_TOOLS_REGISTRY
from app.services.orchestrator import Orchestrator
from app.models.monitor_sample import MonitorSample


def tearDownModule():
    engine.dispose()
    TEMP.cleanup()


class RuntimeChecks(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)
        self.password = secrets.token_urlsafe(18)

    def register(self, username, role):
        key = os.environ[f"{role.upper()}_REGISTER_KEY"]
        response = self.client.post("/auth/register", json={
            "username": username, "password": self.password, "role": role, "reg_key": key,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def login(self, username, password=None):
        response = self.client.post("/auth/login", data={
            "username": username, "password": password or self.password,
        })
        self.assertEqual(response.status_code, 200, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_empty_install_has_no_accounts_or_history(self):
        self.assertEqual(self.client.get("/health").json()["status"], "ok")
        self.assertEqual(self.client.get("/users/me").status_code, 401)
        with engine.connect() as connection:
            for table in Base.metadata.sorted_tables:
                self.assertEqual(connection.scalar(select(func.count()).select_from(table)), 0, table.name)

    def test_real_registration_login_and_role_controls(self):
        self.register("operator-check", "operator")
        headers = self.login("operator-check")
        self.assertEqual(self.client.get("/users/me", headers=headers).json()["role"], "operator")
        self.assertEqual(self.client.get("/api/v1/audit/personnel", headers=headers).status_code, 403)
        self.assertEqual(self.client.post("/auth/register", json={
            "username": "unauthorized-admin", "password": self.password, "role": "admin",
        }).status_code, 403)

    def test_interactive_admin_creation_does_not_overwrite(self):
        with patch.object(sys, "argv", ["create_admin.py", "--username", "owner-check"]):
            with patch("getpass.getpass", side_effect=[self.password, self.password]):
                create_admin.main()
            with self.assertRaises(SystemExit) as error:
                create_admin.main()
            self.assertEqual(error.exception.code, 1)
        with SessionLocal() as db:
            account = db.query(User).filter_by(username="owner-check").one()
            self.assertEqual(account.role, "admin")
            self.assertTrue(verify_password(self.password, account.hashed_password))
        self.assertEqual(self.client.get("/tasks/pending-approvals", headers=self.login("owner-check")).status_code, 200)

    def test_messages_and_password_change_use_persisted_records(self):
        operator = self.register("recipient-check", "operator")
        self.register("auditor-check", "auditor")
        headers = self.login("auditor-check")
        self.assertEqual(self.client.get("/api/v1/audit/messages", headers=headers).json(), [])
        response = self.client.post("/api/v1/audit/messages", headers=headers, json={
            "recipient_user_id": str(operator["id"]), "content": "Integration check", "category": "notification",
        })
        self.assertEqual(response.status_code, 200, response.text)
        recipient_headers = self.login("recipient-check")
        inbox = self.client.get("/api/v1/audit/messages/inbox", headers=recipient_headers).json()
        self.assertEqual(inbox["unread_count"], 1)
        item = inbox["items"][0]
        self.assertEqual(item["content"], "Integration check")
        self.assertEqual(self.client.post(f"/api/v1/audit/messages/inbox/{item['id']}/read", headers=recipient_headers).status_code, 200)
        new_password = secrets.token_urlsafe(18)
        response = self.client.put("/api/v1/audit/security-settings", headers=headers, json={
            "current_password": self.password, "new_password": new_password, "confirm_password": new_password,
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.login("auditor-check", new_password)

    def test_monitor_does_not_invent_process_rows_or_bandwidth(self):
        with patch.object(monitor.psutil, "net_connections", side_effect=PermissionError):
            self.assertEqual(monitor._safe_get_net_rows(None, None), [])
        with patch.object(monitor.psutil, "process_iter", return_value=[]):
            self.assertEqual(monitor._safe_get_disk_rows(interval=0), [])
        with patch.object(monitor.psutil, "net_if_stats", return_value={}):
            self.assertIsNone(monitor._net_capacity_bytes_per_sec())
        self.assertEqual(MonitorCenter._observed_24h_series(deque()), [])
        MonitorCenter._last_net_total_bytes = None
        MonitorCenter._last_net_ts = None
        MonitorCenter._network_history.clear()
        self.assertIsNone(MonitorCenter._sample_network_kbps())
        self.assertEqual(list(MonitorCenter._network_history), [])
        self.assertGreaterEqual(MonitorCenter._sample_network_kbps(), 0)
        self.assertEqual(len(MonitorCenter._network_history), 1)

    def test_ai_failure_returns_error_instead_of_a_health_score(self):
        self.register("report-check", "operator")
        headers = self.login("report-check")
        for result, expected in [(None, 503), (asyncio.TimeoutError(), 504)]:
            replacement = AsyncMock(side_effect=result) if isinstance(result, Exception) else AsyncMock(return_value=result)
            with patch.object(MLService, "call_llm", replacement):
                response = self.client.post("/system/monitor/resource-report", headers=headers, json={"directory": TEMP.name})
            self.assertEqual(response.status_code, expected, response.text)
            self.assertNotIn("ai_report", response.json())

    def test_disk_diagnosis_replaces_irrelevant_plan_and_preserves_scope(self):
        agent = Orchestrator.__new__(Orchestrator)
        agent.task_record = SimpleNamespace(task_text="先只读排查：用 df -h、du -sh 等命令定位磁盘使用率 94.7% 的挂载点及占用热点目录与大文件，收集证据并输出分析结论；再提出低风险空间释放方案，涉及删除、清理或扩容等变更须经审批，并明确回滚步骤与验证方式后方可执行。")
        wrong = [{"tool": "list_disk"}, {"tool": "list_dir", "args": {"path": "/var/log"}}, {"tool": "show_system_log"}]
        partitions = [SimpleNamespace(mountpoint="/mnt/data", fstype="ext4", opts="rw"),
                      SimpleNamespace(mountpoint="/snap/package", fstype="squashfs", opts="ro"),
                      SimpleNamespace(mountpoint="/mnt/other", fstype="ext4", opts="rw")]
        with patch("psutil.disk_partitions", return_value=partitions), \
             patch("psutil.disk_usage", side_effect=lambda p: SimpleNamespace(percent={"/mnt/data": 94.7, "/mnt/other": 98, "/snap/package": 100}.get(p, 50))), \
             patch("os.path.isdir", return_value=True):
            plan = agent._normalize_plan_commands(wrong, allowed_tools=list(MCP_TOOLS_REGISTRY))
        self.assertEqual([p["tool"] for p in plan], ["disk_usage", "directory_usage", "find_large_files"])
        self.assertEqual(plan[0]["command"], "df -h")
        self.assertEqual(plan[1]["args"]["path"], "/mnt/data")
        self.assertEqual(plan[2]["args"]["path"], "/mnt/data")
        self.assertNotIn("journalctl", str(plan))
        agent.task_record.task_text = f"排查磁盘占用热点目录与大文件，限于 {TEMP.name}"
        scoped = agent._normalize_plan_commands(wrong, allowed_tools=list(MCP_TOOLS_REGISTRY))
        self.assertTrue(all(p["target"] == TEMP.name for p in scoped))
        limited = agent._normalize_plan_commands(wrong, allowed_tools=["list_disk"], auto_expand=False)
        self.assertFalse(any(p["tool"] == "find_large_files" for p in limited))

    def test_disk_tools_execute_real_statistics_and_quote_paths(self):
        with tempfile.TemporaryDirectory(dir=TEMP.name, prefix="space ; literal ") as directory:
            large = Path(directory) / "large.bin"
            with large.open("wb") as f:
                f.truncate(101 * 1024 * 1024)
            for tool in ["directory_usage", "find_large_files"]:
                self.assertEqual(KylinMCP.get_required_args_for_tool(tool), ["path"])
                result = subprocess.run(KylinMCP._build_command(tool, path=directory), shell=True, capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(directory, result.stdout)
                if tool == "find_large_files":
                    self.assertIn("large.bin", result.stdout)
            self.assertEqual(KylinMCP._build_command("directory_usage", path="relative"), "")

    def test_reflection_retains_disk_evidence_when_llm_returns_ls_and_logs(self):
        agent = Orchestrator.__new__(Orchestrator)
        agent.task_id = "disk-reflection-test"
        agent.task_record = SimpleNamespace(task_text=f"排查磁盘占用热点目录与大文件 {TEMP.name}", context_data={})
        agent._update_context = Mock()
        agent._add_history = Mock()
        allowed = list(MCP_TOOLS_REGISTRY)
        plan = agent._normalize_plan_commands([], default_tool="list_disk", allowed_tools=allowed)
        draft = {**plan[0], "intent": "磁盘空间排查", "execution_plan": {"commands": plan}}
        response = {"revised_tool": "list_disk", "plan": {"commands": [{"tool": "list_disk"}, {"tool": "list_dir", "args": {"path": TEMP.name}}, {"tool": "show_system_log"}]},
                    "security_scan": {"passed": True, "checks": {name: {"passed": True} for name in ["reversibility", "continuity", "least_cost", "injection_resistance"]}}}
        with patch.object(MLService, "call_llm", AsyncMock(return_value=response)):
            reflection = asyncio.run(agent._self_reflection({"allowed_tools": allowed, "locked_paths": [TEMP.name]}, draft))
        commands = reflection["plan_execute"]["commands"]
        self.assertEqual([c["tool"] for c in commands], [c["tool"] for c in plan])
        self.assertEqual(reflection["revised_command"], commands[0]["command"])
        self.assertEqual([c["id"] for c in commands], [c["id"] for c in plan])

    def test_qps_incremental_read_rotation_truncation_and_missing_log(self):
        class IsolatedMonitor(MonitorCenter):
            _last_access_log_ts = None
            _qps_history = deque()
        now = datetime(2026, 11, 25, 12)
        log = Path(TEMP.name) / "access.log"
        log.write_bytes(b"old request\n" * 1000)
        with patch.dict(os.environ, {"NGINX_ACCESS_LOG": str(log)}), patch.object(IsolatedMonitor, "_now", return_value=now) as clock:
            self.assertIsNone(IsolatedMonitor._sample_nginx_qps())
            with log.open("ab") as f:
                f.write(b"new request\n" * 120)
            clock.return_value = now + timedelta(seconds=60)
            self.assertEqual(IsolatedMonitor._sample_nginx_qps(), 2)
            clock.return_value = now + timedelta(seconds=120)
            self.assertEqual(IsolatedMonitor._sample_nginx_qps(), 0)
            log.rename(log.with_suffix(".log.1"))
            log.write_bytes(b"rotated request\n" * 10)
            clock.return_value = now + timedelta(seconds=180)
            self.assertIsNone(IsolatedMonitor._sample_nginx_qps())
            log.write_bytes(b"")
            clock.return_value = now + timedelta(seconds=240)
            self.assertIsNone(IsolatedMonitor._sample_nginx_qps())
            log.unlink()
            self.assertIsNone(IsolatedMonitor._sample_nginx_qps())

    def test_disk_guardrail_still_blocks_missing_evidence_when_llm_passes(self):
        agent = Orchestrator.__new__(Orchestrator)
        agent.task_id = "disk-guard-test"
        agent.task_record = SimpleNamespace(task_text="排查磁盘占用热点目录与大文件", user_id="1", context_data={})
        agent._update_context = Mock()
        agent._add_history = Mock()
        commands = [{"tool": "list_disk", "command": "lsblk"}]
        reflection = {"revised_tool": "list_disk", "plan_execute": {"commands": commands}}
        with SessionLocal() as db, patch.object(MLService, "call_llm", AsyncMock(return_value={"hallucination_detected": False})):
            agent.db = db
            policy, _ = asyncio.run(agent._check_guardrails({"allowed_tools": list(MCP_TOOLS_REGISTRY)}, {}, reflection, {"total_risk": 0, "verdict": "PASS"}))
        self.assertEqual(policy["final_action"], "REJECTED")
        self.assertIn("缺少核心证据", policy["hallucination_reason"])

    def test_io_diagnosis_does_not_become_space_diagnosis(self):
        agent = Orchestrator.__new__(Orchestrator)
        agent.task_record = SimpleNamespace(task_text="排查磁盘 I/O 占用，分析读写速率")
        self.assertFalse(agent._is_disk_space_diagnosis())

    def test_history_keeps_minute_samples_nulls_and_utc(self):
        now = datetime(2026, 11, 25, 12)
        history = deque([(now - timedelta(hours=25), 99), (now - timedelta(minutes=2), 1.2),
                         (now - timedelta(minutes=1), None), (now, 0), (now + timedelta(minutes=1), 88)])
        with patch.object(MonitorCenter, "_now", return_value=now):
            series = MonitorCenter._observed_24h_series(history)
        self.assertEqual([s["value"] for s in series], [1.2, None, 0])
        self.assertTrue(all(s["timestamp"].endswith("+00:00") for s in series))

    def test_collection_is_independent_of_polling_and_history_survives_reload(self):
        class IsolatedMonitor(MonitorCenter):
            _last_sample_monotonic = None
            _network_history = deque()
            _qps_history = deque()
        with patch.object(IsolatedMonitor, "_sample_network_kbps", return_value=None) as net, \
             patch.object(IsolatedMonitor, "_sample_nginx_qps", return_value=None), \
             patch("app.services.monitor_center.time.monotonic", side_effect=[0, 12, 60]):
            IsolatedMonitor.collect_sample()
            IsolatedMonitor.collect_sample()
            IsolatedMonitor.collect_sample()
        self.assertEqual(net.call_count, 2)
        with SessionLocal() as db:
            self.assertEqual(db.query(MonitorSample).count(), 2)
        IsolatedMonitor._network_history.clear()
        IsolatedMonitor._qps_history.clear()
        IsolatedMonitor.load_history()
        self.assertEqual(len(IsolatedMonitor._network_history), 2)
        self.assertEqual(len(IsolatedMonitor._qps_history), 2)

    def test_real_monitor_snapshot_and_empty_alerts(self):
        self.register("monitor-check", "operator")
        headers = self.login("monitor-check")
        snapshot = self.client.get("/system/monitor/snapshot", headers=headers)
        self.assertEqual(snapshot.status_code, 200, snapshot.text)
        for view in ["cpu_view", "memory_view", "network_view", "disk_view"]:
            self.assertIn("main_chart", snapshot.json()[view])
        self.assertEqual(self.client.get("/api/v1/aiops/alerts", headers=headers).json(), [])

    def test_tool_settings_survive_api_reload(self):
        self.register("tools-check", "operator")
        headers = self.login("tools-check")
        tools = self.client.get("/tools/config/", headers=headers).json()
        self.assertTrue(any(tool["tool_name"] == "list_disk" for tool in tools))
        response = self.client.post("/tools/config/list_disk/disable", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        reloaded = self.client.get("/tools/config/", headers=headers).json()
        self.assertTrue(next(tool for tool in reloaded if tool["tool_name"] == "list_disk")["user_disabled"])
        response = self.client.post("/tools/config/list_disk/enable", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        reloaded = self.client.get("/tools/config/", headers=headers).json()
        self.assertFalse(next(tool for tool in reloaded if tool["tool_name"] == "list_disk")["user_disabled"])

    def test_rag_paths_use_the_repository_root(self):
        self.assertEqual(Path(rag_store.BASE_DIR), ROOT)
        self.assertEqual(Path(rag_store.DATA_DIR), ROOT / "data/rag_store")


if __name__ == "__main__":
    unittest.main()
