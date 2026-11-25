import os
import socket
import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Dict, List, Tuple

import psutil

from app.core.database import SessionLocal
from app.models.monitor_sample import MonitorSample

logger = logging.getLogger(__name__)


class MonitorCenter:
    SAMPLE_INTERVAL = 60
    _network_history: deque = deque(maxlen=24 * 60 + 1)
    _qps_history: deque = deque(maxlen=24 * 60 + 1)
    _last_net_total_bytes: int | None = None
    _last_net_ts: datetime | None = None
    _last_access_log_ts: datetime | None = None
    _access_log_identity: tuple | None = None
    _access_log_offset: int = 0
    _last_sample_monotonic: float | None = None
    _latest_rates: tuple = (None, None)
    _sample_lock = RLock()

    @classmethod
    def _now(cls) -> datetime:
        # Store UTC without tzinfo in SQL, emit explicit UTC offsets in JSON.
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @classmethod
    def _check_port(cls, host: str, port: int, timeout: float = 1.0) -> bool:
        try:
            with socket.create_connection((host, int(port)), timeout=timeout):
                return True
        except Exception:
            return False

    @classmethod
    def _sample_network_kbps(cls) -> float | None:
        try:
            net = psutil.net_io_counters()
        except (OSError, RuntimeError):
            net = None
        if net is None:
            cls._last_net_total_bytes = cls._last_net_ts = None
            return None
        total_bytes = int(net.bytes_sent + net.bytes_recv)
        now = cls._now()

        if cls._last_net_total_bytes is None or cls._last_net_ts is None:
            cls._last_net_total_bytes = total_bytes
            cls._last_net_ts = now
            return None

        delta = total_bytes - cls._last_net_total_bytes
        cls._last_net_total_bytes = total_bytes
        elapsed = (now - cls._last_net_ts).total_seconds()
        cls._last_net_ts = now
        if delta < 0 or elapsed <= 0 or elapsed > cls.SAMPLE_INTERVAL * 2.5:
            return None
        kbps = round(delta / elapsed / 1024, 2)
        cls._network_history.append((now, kbps))
        return kbps

    @classmethod
    def _sample_nginx_qps(cls) -> float | None:
        now = cls._now()
        path = os.environ.get("NGINX_ACCESS_LOG", "/var/log/nginx/access.log")
        try:
            with open(path, "rb") as log:
                stat = os.fstat(log.fileno())
                identity = (path, stat.st_dev, stat.st_ino)
                # Start at EOF. Existing/rotated log contents are not new requests.
                if (cls._last_access_log_ts is None or identity != cls._access_log_identity
                        or stat.st_size < cls._access_log_offset):
                    cls._access_log_identity = identity
                    cls._access_log_offset = stat.st_size
                    cls._last_access_log_ts = now
                    return None
                elapsed = (now - cls._last_access_log_ts).total_seconds()
                log.seek(cls._access_log_offset)
                lines = 0
                while chunk := log.read(64 * 1024):
                    lines += chunk.count(b"\n")
                cls._access_log_offset = log.tell()
                cls._last_access_log_ts = now
                if elapsed <= 0 or elapsed > cls.SAMPLE_INTERVAL * 2.5:
                    return None
                qps = round(lines / elapsed, 4)
        except OSError:
            cls._last_access_log_ts = None
            return None
        cls._qps_history.append((now, qps))
        return qps

    @classmethod
    def _observed_24h_series(cls, history: deque) -> List[Dict[str, float | str | None]]:
        """Preserve sample times and missing values; never stretch hourly averages."""
        now = cls._now()
        cutoff = now - timedelta(hours=24)
        with cls._sample_lock:
            samples = sorted(history, key=lambda item: item[0])
        return [
            {"timestamp": ts.replace(tzinfo=timezone.utc).isoformat(), "value": value}
            for ts, value in samples if cutoff <= ts <= now
        ]

    @classmethod
    def load_history(cls):
        with cls._sample_lock, SessionLocal() as db:
            cutoff = cls._now() - timedelta(hours=24)
            samples = db.query(MonitorSample).filter(MonitorSample.sampled_at >= cutoff).order_by(MonitorSample.sampled_at).all()
            cls._network_history.clear()
            cls._qps_history.clear()
            for sample in samples:
                cls._network_history.append((sample.sampled_at, sample.network_kbps))
                cls._qps_history.append((sample.sampled_at, sample.nginx_qps))

    @classmethod
    def collect_sample(cls):
        """At most one sample per minute, regardless of viewers and API polling."""
        with cls._sample_lock:
            tick = time.monotonic()
            if cls._last_sample_monotonic is not None and tick - cls._last_sample_monotonic < cls.SAMPLE_INTERVAL:
                return cls._latest_rates
            network = cls._sample_network_kbps()
            qps = cls._sample_nginx_qps()
            now = cls._now()
            if network is None:
                cls._network_history.append((now, None))
            if qps is None:
                cls._qps_history.append((now, None))
            cls._latest_rates = (network, qps)
            cls._last_sample_monotonic = tick
            try:
                with SessionLocal() as db:
                    db.merge(MonitorSample(sampled_at=now, network_kbps=network, nginx_qps=qps))
                    db.query(MonitorSample).filter(MonitorSample.sampled_at < now - timedelta(hours=24)).delete()
                    db.commit()
            except Exception:
                logger.exception("Failed to persist monitor sample")
            return cls._latest_rates

    @classmethod
    async def run_collector(cls):
        while True:
            try:
                await asyncio.to_thread(cls.collect_sample)
            except Exception:
                logger.exception("Monitor collection failed")
            await asyncio.sleep(cls.SAMPLE_INTERVAL)

    @classmethod
    def _service_status(cls) -> List[Dict[str, str]]:
        services: List[Tuple[str, int]] = [
            ("MySQL", 3306),
            ("Nginx", 80),
            ("Redis", 6379),
            ("Agent", 8000),
        ]
        result = []
        for name, port in services:
            up = cls._check_port("127.0.0.1", port)
            result.append({
                "name": name,
                "status": "UP" if up else "DOWN",
                "color": "green" if up else "red",
            })
        return result

    @classmethod
    def capture_snapshot(cls) -> Dict:
        cpu = float(psutil.cpu_percent(interval=0.2))
        mem = float(psutil.virtual_memory().percent)
        disk = float(psutil.disk_usage("/").percent)

        network_kbps, nginx_qps = cls.collect_sample()

        return {
            "generated_at": cls._now().replace(tzinfo=timezone.utc).isoformat(),
            "sample_interval_seconds": cls.SAMPLE_INTERVAL,
            "history_note": "每分钟采样；网络为收发总速率，QPS 为访问日志新增请求数/采样秒数；缺测不补零。",
            "gauges": {
                "cpu_percent": round(cpu, 2),
                "memory_percent": round(mem, 2),
                "disk_percent": round(disk, 2),
                "network_kbps": network_kbps,
                "nginx_qps": nginx_qps,
            },
            "service_status": cls._service_status(),
            "network_24h": cls._observed_24h_series(cls._network_history),
            "nginx_qps_24h": cls._observed_24h_series(cls._qps_history),
        }
