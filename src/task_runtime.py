"""Single-machine task runtime for launching the existing pipeline from the Web API."""

from __future__ import annotations

import logging
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from src.main import PipelineOptions, StandalonePipeline
from src.runtime import iso_now, read_json, write_json
from src.web_contract import STAGE_PRESENTATION, TERMINAL_STAGES, write_web_snapshot


MAX_KEYWORD_LENGTH = 80
MAX_PRODUCT_LIMIT = 50
RESUMABLE_STAGES = {"interrupted", "failed", "completed_with_errors"}
TASK_REQUEST_FILE = "task_request.json"


class TaskValidationError(ValueError):
    """The browser task request contains invalid public parameters."""


class ActiveTaskError(RuntimeError):
    """Only one collector task may run at a time."""

    def __init__(self, task_id: str) -> None:
        super().__init__(f"任务 {task_id} 正在运行，请等待其结束后再创建新任务")
        self.task_id = task_id


class TaskNotFoundError(LookupError):
    """The requested run directory or task snapshot does not exist."""


class TaskNotResumableError(RuntimeError):
    """The selected task cannot safely resume from its saved files."""


def validate_task_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TaskValidationError("请求体必须是JSON对象")
    keyword = str(payload.get("keyword") or "").strip()
    if not keyword:
        raise TaskValidationError("keyword不能为空")
    if len(keyword) > MAX_KEYWORD_LENGTH:
        raise TaskValidationError(f"keyword不能超过{MAX_KEYWORD_LENGTH}个字符")

    def positive_integer(name: str) -> int:
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TaskValidationError(f"{name}必须是整数")
        if value < 1 or value > MAX_PRODUCT_LIMIT:
            raise TaskValidationError(
                f"{name}必须在1到{MAX_PRODUCT_LIMIT}之间"
            )
        return value

    candidate_limit = positive_integer("candidate_limit")
    detail_limit = positive_integer("detail_limit")
    if detail_limit > candidate_limit:
        raise TaskValidationError("detail_limit不能大于candidate_limit")
    return {
        "keyword": keyword,
        "candidate_limit": candidate_limit,
        "detail_limit": detail_limit,
    }


class _ManualActionStatusHandler(logging.Handler):
    """Reflect existing Collector login/CAPTCHA warnings in the Web snapshot."""

    def __init__(self, callback: Callable[[str], None]) -> None:
        super().__init__(level=logging.WARNING)
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if "页面阻塞状态" in message or (
            "检测到淘宝" in message and "人工完成" in message
        ):
            self.callback(message)


class TaskManager:
    """Run one synchronous ``StandalonePipeline`` in a controlled worker thread."""

    def __init__(
        self,
        output_root: Path,
        pipeline_factory: Callable[[PipelineOptions], Any] = StandalonePipeline,
        pipeline_defaults: dict[str, Any] | None = None,
    ) -> None:
        self.output_root = output_root.resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.pipeline_factory = pipeline_factory
        self.pipeline_defaults = dict(pipeline_defaults or {})
        self._lock = threading.RLock()
        self._active_task_id: str | None = None
        self._worker_thread: threading.Thread | None = None
        self._mark_stale_runtime_tasks_interrupted()

    @property
    def active_task_id(self) -> str | None:
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return self._active_task_id
            return None

    def _run_root(self, task_id: str) -> Path:
        if (
            not task_id
            or task_id in {".", ".."}
            or "/" in task_id
            or "\\" in task_id
        ):
            raise TaskNotFoundError("任务编号不合法")
        run_root = (self.output_root / task_id).resolve()
        if run_root.parent != self.output_root:
            raise TaskNotFoundError("任务编号不合法")
        return run_root

    def _new_task_id(self) -> str:
        base = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S_task")
        candidate = base
        counter = 2
        while (self.output_root / candidate).exists():
            candidate = f"{base}_{counter:02d}"
            counter += 1
        return candidate

    def _request_path(self, run_root: Path) -> Path:
        return run_root / TASK_REQUEST_FILE

    def _read_request(self, run_root: Path) -> dict[str, Any]:
        path = self._request_path(run_root)
        try:
            value = read_json(path) if path.exists() else {}
        except (OSError, ValueError, TypeError):
            return {}
        return value if isinstance(value, dict) else {}

    def _initial_snapshot(
        self, run_root: Path, request: dict[str, Any], message: str
    ) -> None:
        batch_payload = {
            "run_id": run_root.name,
            "keyword": request["keyword"],
            "search_raw_count": 0,
            "search_deduplicated_count": 0,
            "candidates": [],
        }
        write_web_snapshot(run_root, batch_payload, [], "initializing", message)

    def _set_stage(self, run_root: Path, stage: str, message: str) -> None:
        snapshot_path = run_root / "web_snapshot.json"
        try:
            snapshot = read_json(snapshot_path)
        except (OSError, ValueError, TypeError, FileNotFoundError):
            request = self._read_request(run_root)
            self._initial_snapshot(
                run_root,
                {
                    "keyword": str(request.get("keyword") or ""),
                    "candidate_limit": int(request.get("candidate_limit") or 0),
                    "detail_limit": int(request.get("detail_limit") or 0),
                },
                message,
            )
            snapshot = read_json(snapshot_path)
        snapshot["generatedAt"] = iso_now()
        task = snapshot.setdefault("task", {})
        task.update(
            {
                "id": run_root.name,
                "stage": stage,
                "stageLabel": STAGE_PRESENTATION.get(stage, stage),
                "terminal": stage in TERMINAL_STAGES,
                "message": message,
            }
        )
        write_json(snapshot_path, snapshot)

    def _decorate_snapshot(self, run_root: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
        request = self._read_request(run_root)
        task_id = run_root.name
        stage = str((snapshot.get("task") or {}).get("stage") or "")
        decorated = dict(snapshot)
        decorated["runtime"] = {
            "active": self.active_task_id == task_id,
            "resumable": self._is_resumable(run_root, stage),
            "createdAt": request.get("created_at"),
            "request": {
                "keyword": request.get("keyword"),
                "candidateLimit": request.get("candidate_limit"),
                "detailLimit": request.get("detail_limit"),
            },
        }
        return decorated

    def get_task(self, task_id: str) -> dict[str, Any]:
        run_root = self._run_root(task_id)
        snapshot_path = run_root / "web_snapshot.json"
        if not run_root.is_dir() or not snapshot_path.is_file():
            raise TaskNotFoundError("任务不存在或尚无状态快照")
        try:
            snapshot = read_json(snapshot_path)
        except (OSError, ValueError, TypeError) as exc:
            raise TaskNotFoundError("任务状态快照无法读取") from exc
        return self._decorate_snapshot(run_root, snapshot)

    def list_tasks(self) -> list[dict[str, Any]]:
        tasks: list[dict[str, Any]] = []
        for run_root in self.output_root.iterdir():
            snapshot_path = run_root / "web_snapshot.json"
            if not run_root.is_dir() or not snapshot_path.is_file():
                continue
            try:
                snapshot = read_json(snapshot_path)
            except (OSError, ValueError, TypeError):
                continue
            decorated = self._decorate_snapshot(run_root, snapshot)
            tasks.append(
                {
                    "id": run_root.name,
                    "generatedAt": decorated.get("generatedAt"),
                    "task": decorated.get("task") or {},
                    "statistics": decorated.get("statistics") or {},
                    "runtime": decorated.get("runtime") or {},
                    "url": f"/api/tasks/{run_root.name}",
                }
            )
        tasks.sort(key=lambda item: str(item.get("generatedAt") or ""), reverse=True)
        return tasks

    def create_task(self, payload: Any) -> dict[str, Any]:
        request = validate_task_request(payload)
        with self._lock:
            active = self.active_task_id
            if active:
                raise ActiveTaskError(active)
            task_id = self._new_task_id()
            run_root = self.output_root / task_id
            run_root.mkdir(parents=True, exist_ok=False)
            request_record = {
                **request,
                "task_id": task_id,
                "created_at": iso_now(),
                "runtime_owned": True,
            }
            write_json(self._request_path(run_root), request_record)
            self._initial_snapshot(run_root, request, "任务已创建，正在启动采集流程")
            self._active_task_id = task_id
            self._worker_thread = threading.Thread(
                target=self._run_new_task,
                args=(task_id, request),
                name=f"collector-{task_id}",
                daemon=True,
            )
            self._worker_thread.start()
        return self.get_task(task_id)

    def _pipeline_options(
        self, task_id: str, request: dict[str, Any]
    ) -> PipelineOptions:
        values: dict[str, Any] = {
            "keyword": request["keyword"],
            "limit": request["candidate_limit"],
            "candidate_limit": request["candidate_limit"],
            "detail_limit": request["detail_limit"],
            "output_root": self.output_root,
            "run_id": task_id,
            "skip_ocr": False,
        }
        values.update(self.pipeline_defaults)
        # Public task creation must always run the complete pipeline.
        values["skip_ocr"] = False
        values["output_root"] = self.output_root
        values["run_id"] = task_id
        return PipelineOptions(**values)

    def _attach_manual_action_status(self, pipeline: Any, run_root: Path) -> None:
        logger = getattr(pipeline, "logger", None)
        if not isinstance(logger, logging.Logger):
            return
        logger.addHandler(
            _ManualActionStatusHandler(
                lambda message: self._set_stage(
                    run_root,
                    "manual_action_required",
                    "需要在项目浏览器中完成人工登录或验证；完成后请在服务终端按 Enter",
                )
            )
        )

    def _record_failure(self, run_root: Path, exc: BaseException) -> None:
        message = f"{type(exc).__name__}: {exc}"
        write_json(
            run_root / "task_runtime_error.json",
            {
                "failed_at": iso_now(),
                "type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        self._set_stage(run_root, "failed", f"任务运行失败：{message}")

    def _finish_worker(self, task_id: str) -> None:
        with self._lock:
            if self._active_task_id == task_id:
                self._active_task_id = None
                self._worker_thread = None

    def _run_new_task(self, task_id: str, request: dict[str, Any]) -> None:
        run_root = self._run_root(task_id)
        try:
            pipeline = self.pipeline_factory(self._pipeline_options(task_id, request))
            self._attach_manual_action_status(pipeline, run_root)
            pipeline.run()
        except BaseException as exc:  # keep the HTTP service alive on worker failure
            self._record_failure(run_root, exc)
        finally:
            self._finish_worker(task_id)

    def _options_from_run_config(self, task_id: str) -> PipelineOptions:
        run_root = self._run_root(task_id)
        config_path = run_root / "run_config.json"
        if not config_path.is_file():
            raise TaskNotResumableError("任务缺少run_config.json，无法安全恢复")
        config = read_json(config_path)
        candidate_limit = int(
            config.get("resolved_candidate_limit")
            or config.get("candidate_limit")
            or config.get("limit")
            or 10
        )
        detail_limit = int(
            config.get("resolved_detail_limit")
            or config.get("detail_limit")
            or candidate_limit
        )
        values: dict[str, Any] = {
            "keyword": str(config.get("keyword") or ""),
            "limit": candidate_limit,
            "candidate_limit": candidate_limit,
            "detail_limit": detail_limit,
            "output_root": self.output_root,
            "profile_dir": Path(config.get("profile_dir") or ".browser-profile"),
            "channel": str(config.get("channel") or "chrome"),
            "browser_mode": str(config.get("browser_mode") or "cdp"),
            "browser_executable": (
                Path(config["browser_executable"])
                if config.get("browser_executable")
                else None
            ),
            "cdp_port": int(config.get("cdp_port") or 9222),
            "rule_config": Path(
                config.get("rule_config") or "config/effect_keywords.json"
            ),
            "cache_dir": Path(
                config.get("cache_dir") or Path.home() / ".cache" / "paddlex"
            ),
            "run_id": task_id,
            "headless": bool(config.get("headless", False)),
            "non_interactive": bool(config.get("non_interactive", False)),
            "browser_proxy": (
                None if config.get("browser_proxy") == "configured" else config.get("browser_proxy")
            ),
            "direct_browser": bool(config.get("direct_browser", False)),
            "product_delay_seconds": float(
                config.get("product_delay_seconds") or 2.0
            ),
            "detail_retries": int(config.get("detail_retries") or 1),
            "skip_ocr": False,
            "verbose": bool(config.get("verbose", False)),
        }
        values.update(self.pipeline_defaults)
        values["keyword"] = str(config.get("keyword") or "")
        values["limit"] = candidate_limit
        values["candidate_limit"] = candidate_limit
        values["detail_limit"] = detail_limit
        values["output_root"] = self.output_root
        values["run_id"] = task_id
        values["skip_ocr"] = False
        return PipelineOptions(**values)

    def _is_resumable(self, run_root: Path, stage: str) -> bool:
        request = self._read_request(run_root)
        return (
            request.get("runtime_owned") is True
            and
            stage in RESUMABLE_STAGES
            and (run_root / "run_config.json").is_file()
            and (run_root / "search" / "search_candidates.json").is_file()
            and (run_root / "batch_state.json").is_file()
        )

    def resume_task(self, task_id: str) -> dict[str, Any]:
        run_root = self._run_root(task_id)
        snapshot = self.get_task(task_id)
        stage = str((snapshot.get("task") or {}).get("stage") or "")
        if not self._is_resumable(run_root, stage):
            raise TaskNotResumableError("该任务当前没有可安全恢复的断点")
        with self._lock:
            active = self.active_task_id
            if active:
                raise ActiveTaskError(active)
            options = self._options_from_run_config(task_id)
            self._set_stage(run_root, "initializing", "正在从已保存断点恢复任务")
            self._active_task_id = task_id
            self._worker_thread = threading.Thread(
                target=self._run_resume_task,
                args=(task_id, options),
                name=f"collector-resume-{task_id}",
                daemon=True,
            )
            self._worker_thread.start()
        return self.get_task(task_id)

    def _run_resume_task(self, task_id: str, options: PipelineOptions) -> None:
        run_root = self._run_root(task_id)
        try:
            pipeline = self.pipeline_factory(options)
            self._attach_manual_action_status(pipeline, run_root)
            pipeline.resume_processing(collect_pending_details=True)
        except BaseException as exc:
            self._record_failure(run_root, exc)
        finally:
            self._finish_worker(task_id)

    def wait_for_idle(self, timeout: float = 10.0) -> bool:
        """Test/support helper; the HTTP server never blocks on this method."""

        with self._lock:
            worker = self._worker_thread
        if worker is None:
            return True
        worker.join(timeout)
        return not worker.is_alive()

    def _mark_stale_runtime_tasks_interrupted(self) -> None:
        for run_root in self.output_root.iterdir():
            request = self._read_request(run_root) if run_root.is_dir() else {}
            snapshot_path = run_root / "web_snapshot.json"
            if not request.get("runtime_owned") or not snapshot_path.is_file():
                continue
            try:
                snapshot = read_json(snapshot_path)
            except (OSError, ValueError, TypeError):
                continue
            task = snapshot.get("task") or {}
            if not task.get("terminal"):
                self._set_stage(
                    run_root,
                    "interrupted",
                    "本地服务上次退出时任务尚未结束，可尝试从已保存断点恢复",
                )
