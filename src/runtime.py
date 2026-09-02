"""Shared runtime helpers for the standalone collection pipeline."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_run_id(suffix: str = "standalone") -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + f"_{suffix}"


def write_json(path: Path, value: Any) -> None:
    """Atomically replace a UTF-8 JSON file.

    The web demo can poll progress files while the collector is updating them;
    replacing a complete temporary file prevents readers from observing partial
    JSON.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
    )
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        for attempt in range(20):
            try:
                temporary.replace(path)
                return
            except PermissionError:
                if attempt == 19:
                    raise
                # Windows can briefly lock the destination while an HTTP
                # request is reading it. Retrying preserves atomic snapshots
                # without exposing partially written JSON to the frontend.
                time.sleep(0.01)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_product_id(url: str) -> str | None:
    values = parse_qs(urlparse(url).query).get("id")
    if values and values[0].isdigit():
        return values[0]
    match = re.search(r"(?:^|[?&])id=(\d+)", url)
    return match.group(1) if match else None


def setup_run_logger(run_root: Path, verbose: bool = False) -> logging.Logger:
    """Create an isolated console + file logger for one pipeline run."""

    run_root.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"taobao_mvp.{run_root.name}")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.propagate = False
    logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG if verbose else logging.INFO)
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = logging.FileHandler(run_root / "run.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
