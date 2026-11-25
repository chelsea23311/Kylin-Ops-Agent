import asyncio
import time
import psutil
from datetime import datetime, timezone

# --- 状态判定逻辑 ---
def _cpu_status(pct: float) -> str:
    if pct >= 90: return "critical"
    if pct >= 70: return "warning"
    return "normal"

def _mem_status(pct: float) -> str:
    if pct >= 95: return "critical"
    if pct >= 85: return "warning"
    return "normal"

def _disk_status(pct: float) -> str:
    if pct >= 95: return "critical"
    if pct >= 80: return "warning"
    return "normal"

# --- 核心采集函数 (防御性增强) ---
def _safe_get_cpu_rows(limit=15):
    """确保返回 list，绝不返回 None"""
    rows = []
    try:
        # 第一次调用获取百分配比
        psutil.cpu_percent(interval=None) 
        for p in psutil.process_iter(['pid', 'name', 'status', 'num_threads', 'cpu_percent']):
            try:
                info = p.info
                rows.append({
                    "名称": str(info.get('name') or "Unknown"),
                    "PID": int(info.get('pid') or 0),
                    "描述": "",
                    "状态": str(info.get('status') or "running"),
                    "线程数": int(info.get('num_threads') or 0),
                    "CPU%": round(float(info.get('cpu_percent') or 0), 1),
                })
            except: continue
        rows.sort(key=lambda x: x["CPU%"], reverse=True)
    except:
        pass
    return rows[:limit] if isinstance(rows, list) else []

def _safe_get_mem_rows(limit=15):
    """确保内存进程列表符合文档格式"""
    rows = []
    try:
        for p in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                info = p.info
                m = info.get('memory_info')
                rss = (m.rss / 1024 / 1024) if m else 0
                vms = (m.vms / 1024 / 1024) if m else 0
                rows.append({
                    "名称": str(info.get('name') or "Unknown"),
                    "PID": int(info.get('pid') or 0),
                    "提交(KB)": f"{int(vms*1024)}",
                    "工作集(KB)": f"{int(rss*1024)}",
                })
            except: continue
        rows.sort(key=lambda x: int(x["工作集(KB)"]), reverse=True)
    except:
        pass
    return rows[:limit] if isinstance(rows, list) else []

def _net_capacity_bytes_per_sec() -> float:
    try:
        total_mbps = 0
        for name, stats in psutil.net_if_stats().items():
            if stats.isup and stats.speed and not name.lower().startswith(("lo", "loopback")):
                total_mbps += stats.speed
        if total_mbps > 0:
            return total_mbps * 1000 * 1000 / 8
    except Exception:
        pass
    return None

def _sample_system_io(interval=0.25):
    net_a = psutil.net_io_counters()
    disk_a = psutil.disk_io_counters()
    start = time.monotonic()
    time.sleep(interval)
    elapsed = max(time.monotonic() - start, 0.001)
    net_b = psutil.net_io_counters()
    disk_b = psutil.disk_io_counters()

    def rate(before, after, attr):
        if not before or not after:
            return None
        return max(0.0, (getattr(after, attr, 0) - getattr(before, attr, 0)) / elapsed)

    return {
        "net_sent_bps": rate(net_a, net_b, "bytes_sent"),
        "net_recv_bps": rate(net_a, net_b, "bytes_recv"),
        "disk_read_bps": rate(disk_a, disk_b, "read_bytes"),
        "disk_write_bps": rate(disk_a, disk_b, "write_bytes"),
    }

def _safe_get_net_rows(total_sent_bps=0, total_recv_bps=0, limit=15):
    """返回真实连接所属进程；psutil 不提供的进程带宽以 None 标记。"""
    rows = []
    total_sent = round(float(total_sent_bps or 0), 1)
    total_recv = round(float(total_recv_bps or 0), 1)
    if total_sent_bps is not None and total_recv_bps is not None:
        rows.append({
            "名称": "系统网络总计",
            "PID": "—",
            "发送(字节/秒)": total_sent,
            "接收(字节/秒)": total_recv,
            "总数(字节/秒)": round(total_sent + total_recv, 1),
        })
    try:
        pid_set = set()
        for c in psutil.net_connections(kind='inet'):
            if c.pid:
                pid_set.add(c.pid)

        for pid in list(pid_set):
            if len(rows) >= limit:
                break
            try:
                p = psutil.Process(pid)
                rows.append({
                    "名称": str(p.name() or "Unknown"),
                    "PID": int(pid),
                    "发送(字节/秒)": None,
                    "接收(字节/秒)": None,
                    "总数(字节/秒)": None,
                })
            except:
                continue
    except:
        pass

    return rows[:limit] if isinstance(rows, list) else []

def _safe_get_disk_rows(interval=0.25, limit=15):
    """用两次 I/O 计数计算真实进程速率；没有观测值时返回空列表。"""
    rows = []
    try:
        first = {}
        for p in psutil.process_iter(['pid', 'name', 'io_counters']):
            try:
                io = p.info.get('io_counters')
                if not io:
                    continue
                first[int(p.info.get('pid') or 0)] = (
                    str(p.info.get('name') or "Unknown"),
                    int(io.read_bytes or 0),
                    int(io.write_bytes or 0),
                )
            except:
                continue
        start = time.monotonic()
        time.sleep(interval)
        elapsed = max(time.monotonic() - start, 0.001)
        for p in psutil.process_iter(['pid', 'name', 'io_counters']):
            try:
                pid = int(p.info.get('pid') or 0)
                before = first.get(pid)
                io = p.info.get('io_counters')
                if not before or not io:
                    continue
                name, read_a, write_a = before
                read_bps = max(0.0, (int(io.read_bytes or 0) - read_a) / elapsed)
                write_bps = max(0.0, (int(io.write_bytes or 0) - write_a) / elapsed)
                total_bps = read_bps + write_bps
                if total_bps <= 0:
                    continue
                rows.append({
                    "名称": name,
                    "PID": pid,
                    "读(字节/秒)": round(read_bps, 1),
                    "写(字节/秒)": round(write_bps, 1),
                    "总数(字节/秒)": round(total_bps, 1),
                })
            except:
                continue
        rows.sort(key=lambda x: x["总数(字节/秒)"], reverse=True)
    except:
        pass

    return rows[:limit] if isinstance(rows, list) else []

class SystemMonitor:
    @staticmethod
    def get_resource_monitor_payload() -> dict:
        """采集操作系统实时数据，不填充历史数据或未观测到的进程。"""
        
        # 基础运行时间
        boot_time = psutil.boot_time()
        uptime_days = int((datetime.now().timestamp() - boot_time) / 86400)
        now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # 1. CPU
        cpu_pct = psutil.cpu_percent(interval=None)
        
        # 2. 内存
        mem = psutil.virtual_memory()
        
        # 3. 网络 / 磁盘 I/O 速率
        io_rates = _sample_system_io()
        net_available = io_rates["net_sent_bps"] is not None and io_rates["net_recv_bps"] is not None
        net_total_bps = io_rates["net_sent_bps"] + io_rates["net_recv_bps"] if net_available else None
        net_val = round(net_total_bps / 1024, 1) if net_available else None
        capacity = _net_capacity_bytes_per_sec()
        net_util_pct = min(round(net_total_bps / capacity * 100, 1), 100) if net_available and capacity else None
        disk_available = io_rates["disk_read_bps"] is not None and io_rates["disk_write_bps"] is not None
        disk_io_kbps = round((io_rates["disk_read_bps"] + io_rates["disk_write_bps"]) / 1024, 1) if disk_available else None
        cpu_freq = psutil.cpu_freq()
        cpu_max = f"{cpu_freq.max:g} MHz" if cpu_freq and cpu_freq.max else "—"
        net_label = f"{net_val} KB/s" if net_val is not None else "—"
        net_util_label = f"{net_util_pct}%" if net_util_pct is not None else "—"
        disk_io_label = f"{disk_io_kbps} KB/s" if disk_io_kbps is not None else "—"

        # 4. 磁盘
        try:
            disk_usage = psutil.disk_usage('/')
            disk_pct = disk_usage.percent
        except:
            disk_pct = None

        # 构造最终大对象
        return {
            "cpu_view": {
                "summary_bar": {
                    "label": f"{cpu_pct}% CPU 使用率",
                    "extra_label": f"{cpu_max} 最大频率",
                    "status": _cpu_status(cpu_pct),
                    "uptime_days": uptime_days
                },
                "process_table": {
                    "title": "进程",
                    "columns": ["名称", "PID", "描述", "状态", "线程数", "CPU%"],
                    "rows": _safe_get_cpu_rows()
                },
                "main_chart": {
                    "title": "CPU - 总计",
                    "unit": "%",
                    "series": [{"timestamp": now_iso, "value": cpu_pct}]
                }
            },
            "memory_view": {
                "summary_bar": {
                    "label": f"{mem.percent}% 已用物理内存",
                    "extra_label": f"{mem.available // 1024 // 1024} MB 可用",
                    "status": _mem_status(mem.percent),
                    "uptime_days": uptime_days
                },
                "process_table": {
                    "title": "进程",
                    "columns": ["名称", "PID", "提交(KB)", "工作集(KB)"],
                    "rows": _safe_get_mem_rows()
                },
                "main_chart": {
                    "title": "使用的物理内存",
                    "unit": "%",
                    "series": [{"timestamp": now_iso, "value": mem.percent}]
                }
            },
            "network_view": {
                "summary_bar": {
                    "label": f"{net_label} 网络 I/O",
                    "extra_label": f"{net_util_label} 网络使用率",
                    "status": "normal",
                    "uptime_days": uptime_days
                },
                "process_table": {
                    "title": "网络活动的进程",
                    "columns": ["名称", "PID", "发送(字节/秒)", "接收(字节/秒)", "总数(字节/秒)"],
                    "rows": _safe_get_net_rows(io_rates["net_sent_bps"], io_rates["net_recv_bps"])
                },
                "main_chart": {
                    "title": "网络",
                    "unit": "KB/s",
                    "series": [{"timestamp": now_iso, "value": net_val}] if net_available else []
                }
            },
            "disk_view": {
                "summary_bar": {
                    "label": f"{disk_pct}% 磁盘使用率" if disk_pct is not None else "— 磁盘使用率",
                    "extra_label": f"{disk_io_label} 磁盘 I/O",
                    "status": _disk_status(disk_pct) if disk_pct is not None else "unknown",
                    "uptime_days": uptime_days
                },
                "process_table": {
                    "title": "磁盘活动的进程",
                    "columns": ["名称", "PID", "读(字节/秒)", "写(字节/秒)", "总数(字节/秒)"],
                    "rows": _safe_get_disk_rows()
                },
                "main_chart": {
                    "title": "磁盘",
                    "unit": "KB/s",
                    "series": [{"timestamp": now_iso, "value": disk_io_kbps}] if disk_available else []
                }
            }
        }

    @staticmethod
    async def stream(interval: float = 3.0):
        """
        WebSocket 专用生成器。
        严格包装在 monitor_frame 协议内。
        """
        while True:
            try:
                # 实时生成数据
                payload = SystemMonitor.get_resource_monitor_payload()
                yield {
                    "type": "monitor_frame",
                    "data": payload
                }
            except Exception as e:
                # 后端异常不中断 WebSocket，只打印
                print(f"Monitor Stream Error: {str(e)}")
            await asyncio.sleep(interval)
