"""Small standard-library HTTP API for local task execution and result viewing."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from src.data_store import (
    DataStore,
    ReviewValidationError,
    SnapshotNotFoundError,
)
from src.runtime import read_json
from src.task_runtime import (
    ActiveTaskError,
    TaskManager,
    TaskNotFoundError,
    TaskNotResumableError,
    TaskValidationError,
)


def resolve_run_root(output_root: Path, run_id: str) -> Path:
    output_root = output_root.resolve()
    if not run_id or run_id in {".", ".."} or "/" in run_id or "\\" in run_id:
        raise ValueError("invalid run id")
    run_root = (output_root / run_id).resolve()
    if run_root.parent != output_root:
        raise ValueError("run path escapes output root")
    return run_root


def resolve_run_file(run_root: Path, relative_path: str) -> Path:
    run_root = run_root.resolve()
    relative_path = unquote(relative_path).replace("\\", "/").lstrip("/")
    if not relative_path:
        raise ValueError("empty file path")
    destination = (run_root / relative_path).resolve()
    if destination == run_root or not destination.is_relative_to(run_root):
        raise ValueError("file path escapes run root")
    return destination


def resolve_web_file(web_root: Path, relative_path: str) -> Path:
    web_root = web_root.resolve()
    relative_path = unquote(relative_path).replace("\\", "/").lstrip("/")
    relative_path = relative_path or "index.html"
    destination = (web_root / relative_path).resolve()
    if not destination.is_relative_to(web_root):
        raise ValueError("file path escapes web root")
    return destination


def list_run_snapshots(output_root: Path) -> list[dict[str, Any]]:
    output_root = output_root.resolve()
    if not output_root.exists():
        return []
    runs = []
    for run_root in output_root.iterdir():
        snapshot_path = run_root / "web_snapshot.json"
        if not run_root.is_dir() or not snapshot_path.exists():
            continue
        try:
            snapshot = read_json(snapshot_path)
        except (OSError, ValueError, TypeError):
            continue
        runs.append(
            {
                "id": run_root.name,
                "generatedAt": snapshot.get("generatedAt"),
                "task": snapshot.get("task") or {},
                "statistics": snapshot.get("statistics") or {},
                "url": f"/api/runs/{run_root.name}",
            }
        )
    runs.sort(key=lambda item: str(item.get("generatedAt") or ""), reverse=True)
    return runs


def create_handler(
    output_root: Path,
    web_root: Path = Path("web"),
    task_manager: TaskManager | None = None,
    data_store: DataStore | None = None,
) -> type[BaseHTTPRequestHandler]:
    resolved_output = output_root.resolve()
    resolved_web = web_root.resolve()
    store = data_store or DataStore(
        resolved_output.parent / "data" / "app.db", resolved_output
    )
    store.initialize()
    store.import_all_runs()
    manager = task_manager or TaskManager(
        resolved_output, task_indexer=store.import_run
    )
    manager.set_task_indexer(store.import_run)

    class LocalApiHandler(BaseHTTPRequestHandler):
        server_version = "TaobaoRiskMVP/1.1"

        def _common_headers(self, content_type: str, length: int) -> None:
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")

        def _json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._common_headers("application/json; charset=utf-8", len(body))
            self.end_headers()
            self.wfile.write(body)

        def _error(self, status: int, code: str, message: str) -> None:
            self._json(status, {"error": {"code": code, "message": message}})

        def _read_json_body(self) -> Any | None:
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except ValueError:
                self._error(400, "invalid_content_length", "请求长度不合法")
                return None
            if length < 1 or length > 16 * 1024:
                self._error(400, "invalid_request_size", "请求体不能为空且不能超过16KB")
                return None
            try:
                return json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._error(400, "invalid_json", "请求体不是有效的UTF-8 JSON")
                return None

        def _send_file(self, destination: Path) -> None:
            body = destination.read_bytes()
            content_type = mimetypes.guess_type(destination.name)[0]
            if content_type is None:
                content_type = "application/octet-stream"
            if content_type.startswith("text/") or content_type in {
                "application/json",
                "application/javascript",
            }:
                content_type += "; charset=utf-8"
            self.send_response(200)
            self._common_headers(content_type, len(body))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            parsed = urlparse(self.path)
            path = parsed.path
            if not path.startswith("/api/"):
                try:
                    destination = resolve_web_file(
                        resolved_web, "index.html" if path == "/" else path
                    )
                except ValueError:
                    self._error(400, "invalid_web_path", "页面路径不合法")
                    return
                if not destination.is_file():
                    self._error(404, "page_not_found", "页面文件不存在")
                    return
                self._send_file(destination)
                return
            if path == "/api/health":
                self._json(200, {"status": "ok", "service": "taobao-risk-mvp"})
                return
            if path == "/api/runs":
                self._json(200, {"runs": list_run_snapshots(resolved_output)})
                return
            if path == "/api/tasks":
                self._json(
                    200,
                    {
                        "tasks": manager.list_tasks(),
                        "activeTaskId": manager.active_task_id,
                    },
                )
                return
            parts = [unquote(item) for item in path.split("/") if item]
            if path == "/api/products":
                query = parse_qs(parsed.query)
                try:
                    products = store.list_products(
                        query=str((query.get("query") or [""])[0]).strip(),
                        review_status=str(
                            (query.get("review_status") or [""])[0]
                        ).strip(),
                        effect=str((query.get("effect") or [""])[0]).strip(),
                        task_id=str((query.get("task_id") or [""])[0]).strip(),
                    )
                except ReviewValidationError as exc:
                    self._error(400, "invalid_filter", str(exc))
                    return
                self._json(200, {"products": products, "count": len(products)})
                return
            if (
                len(parts) == 4
                and parts[:2] == ["api", "products"]
                and parts[3] == "snapshots"
            ):
                snapshots = store.list_product_snapshots(parts[2])
                self._json(
                    200,
                    {
                        "productId": parts[2],
                        "snapshots": snapshots,
                        "count": len(snapshots),
                    },
                )
                return
            if len(parts) == 3 and parts[:2] == ["api", "snapshots"]:
                try:
                    self._json(200, store.get_snapshot(parts[2]))
                except SnapshotNotFoundError as exc:
                    self._error(404, "snapshot_not_found", str(exc))
                return
            if len(parts) == 3 and parts[:2] == ["api", "tasks"]:
                try:
                    self._json(200, manager.get_task(parts[2]))
                except TaskNotFoundError as exc:
                    self._error(404, "task_not_found", str(exc))
                return
            if len(parts) < 3 or parts[:2] != ["api", "runs"]:
                self._error(404, "not_found", "接口不存在")
                return
            run_id = parts[2]
            try:
                run_root = resolve_run_root(resolved_output, run_id)
            except ValueError:
                self._error(400, "invalid_run_id", "运行编号不合法")
                return
            if not run_root.is_dir():
                self._error(404, "run_not_found", "运行目录不存在")
                return
            if len(parts) == 3:
                snapshot_path = run_root / "web_snapshot.json"
                if not snapshot_path.exists():
                    self._error(404, "snapshot_not_found", "该任务还没有网页快照")
                    return
                try:
                    self._json(200, read_json(snapshot_path))
                except (OSError, ValueError, TypeError):
                    self._error(500, "invalid_snapshot", "网页快照无法读取")
                return
            if len(parts) >= 5 and parts[3] == "files":
                relative_path = "/".join(parts[4:])
                try:
                    destination = resolve_run_file(run_root, relative_path)
                except ValueError:
                    self._error(400, "invalid_file_path", "文件路径不合法")
                    return
                if not destination.is_file():
                    self._error(404, "file_not_found", "文件不存在")
                    return
                self._send_file(destination)
                return
            self._error(404, "not_found", "接口不存在")

        def do_PUT(self) -> None:  # noqa: N802 - stdlib handler API
            path = urlparse(self.path).path
            parts = [unquote(item) for item in path.split("/") if item]
            if (
                len(parts) == 4
                and parts[:2] == ["api", "snapshots"]
                and parts[3] == "review"
            ):
                payload = self._read_json_body()
                if payload is None:
                    return
                if not isinstance(payload, dict):
                    self._error(400, "invalid_review", "请求体必须是JSON对象")
                    return
                try:
                    review = store.update_review(
                        parts[2],
                        str(payload.get("status") or ""),
                        str(payload.get("note") or ""),
                    )
                except ReviewValidationError as exc:
                    self._error(400, "invalid_review", str(exc))
                    return
                except SnapshotNotFoundError as exc:
                    self._error(404, "snapshot_not_found", str(exc))
                    return
                self._json(200, {"snapshotId": parts[2], "review": review})
                return
            self._error(404, "not_found", "接口不存在")

        def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
            path = urlparse(self.path).path
            parts = [unquote(item) for item in path.split("/") if item]
            if path == "/api/tasks":
                payload = self._read_json_body()
                if payload is None:
                    return
                try:
                    self._json(202, manager.create_task(payload))
                except TaskValidationError as exc:
                    self._error(400, "invalid_task", str(exc))
                except ActiveTaskError as exc:
                    self._json(
                        409,
                        {
                            "error": {
                                "code": "active_task_exists",
                                "message": str(exc),
                                "activeTaskId": exc.task_id,
                            }
                        },
                    )
                return
            if len(parts) == 4 and parts[:2] == ["api", "tasks"] and parts[3] == "resume":
                try:
                    self._json(202, manager.resume_task(parts[2]))
                except TaskNotFoundError as exc:
                    self._error(404, "task_not_found", str(exc))
                except TaskNotResumableError as exc:
                    self._error(409, "task_not_resumable", str(exc))
                except ActiveTaskError as exc:
                    self._json(
                        409,
                        {
                            "error": {
                                "code": "active_task_exists",
                                "message": str(exc),
                                "activeTaskId": exc.task_id,
                            }
                        },
                    )
                return
            self._error(404, "not_found", "接口不存在")

        def log_message(self, format: str, *args: Any) -> None:
            print(f"[local-api] {self.address_string()} - {format % args}")

    return LocalApiHandler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="启动本地任务与结果服务")
    parser.add_argument("--output-root", type=Path, default=Path("output"))
    parser.add_argument("--web-root", type=Path, default=Path("web"))
    parser.add_argument("--database", type=Path, default=Path("data/app.db"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--profile-dir", type=Path, default=Path(".browser-profile"))
    parser.add_argument("--channel", default="chrome")
    parser.add_argument("--browser-mode", choices=("persistent", "cdp"), default="cdp")
    parser.add_argument("--cdp-port", type=int, default=9222)
    parser.add_argument("--browser-proxy")
    parser.add_argument(
        "--direct-browser",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="让采集浏览器绕过系统代理直连（默认启用）",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    store = DataStore(args.database, args.output_root)
    store.initialize()
    imported = store.import_all_runs()
    manager = TaskManager(
        args.output_root,
        pipeline_defaults={
            "profile_dir": args.profile_dir,
            "channel": args.channel,
            "browser_mode": args.browser_mode,
            "cdp_port": args.cdp_port,
            "browser_proxy": args.browser_proxy,
            "direct_browser": args.direct_browser,
            "verbose": args.verbose,
        },
        task_indexer=store.import_run,
    )
    server = ThreadingHTTPServer(
        (args.host, args.port),
        create_handler(args.output_root, args.web_root, manager, store),
    )
    server.daemon_threads = True
    print(f"本地展示页面：http://{args.host}:{args.port}/")
    print(f"本地结果接口：http://{args.host}:{args.port}/api/health")
    print(f"任务创建接口：http://{args.host}:{args.port}/api/tasks")
    print(
        "业务数据索引："
        f"{store.database_path}（发现 {imported['discovered']}，索引 {imported['imported']}）"
    )
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("本地结果接口已停止")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
