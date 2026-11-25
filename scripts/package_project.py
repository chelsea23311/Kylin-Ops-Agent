#!/usr/bin/env python3
"""Package the maintained source tree without local models or runtime state."""
import argparse
import fnmatch
import re
import shutil
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATHS = [
    "README.md", ".env.example", ".gitignore", ".dockerignore",
    "Dockerfile", "docker-compose.yml", "requirements.txt",
    "inference_service.py", "kylin_rag.py", "kylin_faq.index", "kylin_faq_meta.pkl",
    "银河麒麟桌面操作系统V11 2603常见问题(FAQ) .pdf",
    "operations-and-maintenance", "program2", "scripts", "docs", "tests",
]
EXCLUDED = [
    ".git", ".env", ".env.*", "node_modules", "__pycache__", "venv", ".venv",
    "data", "runtime", "models", "audit_model_v1", "*.pyc", "*.pyo", "*.db*",
    "*.sqlite*", "*.log", "*.bak", "*_archive*", "*_backup*", "*.tar.gz", "*.zip",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["source", "release"])
    parser.add_argument("version")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.version):
        parser.error("版本号只能包含字母、数字、点、下划线和连字符")
    include_dist = args.kind == "release"
    if include_dist and not (ROOT / "operations-and-maintenance/dist/index.html").is_file():
        parser.error("请先在 operations-and-maintenance 中执行 npm ci 和 npm run build")

    def ignore(directory, names):
        patterns = EXCLUDED + ([] if include_dist else ["dist"])
        return [name for name in names if name != ".env.example" and (
            (Path(directory) / name).is_symlink()
            or any(fnmatch.fnmatch(name, pattern) for pattern in patterns)
        )]

    out = ROOT / "release"
    out.mkdir(exist_ok=True)
    suffix = "-source" if args.kind == "source" else ""
    name = f"kylin-ops-agent{suffix}-{args.version}"
    archive = out / f"{name}.tar.gz"
    if archive.exists():
        parser.error(f"输出文件已存在：{archive}（请使用新的版本号）")
    with tempfile.TemporaryDirectory(prefix="package-", dir=out) as stage:
        destination = Path(stage) / name
        destination.mkdir()
        for relative in SOURCE_PATHS:
            src = ROOT / relative
            dst = destination / relative
            if src.is_dir():
                shutil.copytree(src, dst, ignore=ignore)
            else:
                shutil.copy2(src, dst)
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(destination, arcname=name)
    print(archive)


if __name__ == "__main__":
    main()
