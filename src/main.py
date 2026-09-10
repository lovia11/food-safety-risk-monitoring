"""Standalone end-to-end Taobao risk-clue MVP pipeline."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.discovery import DiscoveryCoordinator
from src.inspection_runtime import (
    DEFAULT_INSPECTION_CONFIG_PATH,
    DEFAULT_RISK_SUBSTANCE_CONFIG_PATH,
    INSPECTION_RECOMMENDATION_ERROR_FILE,
    INSPECTION_RECOMMENDATION_FILE,
    InspectionRuntime,
)
from src.phase1_experiment import PhaseOneCollector
from src.phase2_ocr import OCRRuntime, create_ocr_runtime, run_ocr
from src.phase3_analysis import run_analysis
from src.phase5_batch import build_batch_record, build_batch_summary, write_batch_csv
from src.runtime import iso_now, new_run_id, read_json, setup_run_logger, write_json
from src.taobao_live import BrowserSettings, LiveSearchCollector, launch_browser_session
from src.web_contract import write_web_snapshot


class ProductStatus:
    PENDING = "pending_detail_collection"
    COLLECTING = "collecting_detail"
    DETAIL_COLLECTED = "detail_collected"
    PROCESSING = "processing_ocr_analysis"
    SUCCESS = "success"
    FAILED_COLLECTION = "failed_collection"
    FAILED_PROCESSING = "failed_processing"


@dataclass(frozen=True)
class PipelineOptions:
    keyword: str
    # ``limit`` remains as a Python API compatibility alias for pre-v0.2 callers.
    limit: int = 10
    candidate_limit: int | None = None
    detail_limit: int | None = None
    output_root: Path = Path("output")
    profile_dir: Path = Path(".browser-profile")
    channel: str = "chrome"
    browser_mode: str = "cdp"
    browser_executable: Path | None = None
    cdp_port: int = 9222
    rule_config: Path = Path("config/effect_keywords.json")
    cache_dir: Path = Path.home() / ".cache" / "paddlex"
    run_id: str | None = None
    headless: bool = False
    non_interactive: bool = False
    browser_proxy: str | None = None
    direct_browser: bool = False
    product_delay_seconds: float = 2.0
    detail_retries: int = 1
    skip_ocr: bool = False
    verbose: bool = False
    task_type: str = "quick"
    target_id: str | None = None
    target_name: str | None = None
    search_queries: tuple[dict[str, Any], ...] = ()
    per_query_candidate_limit: int | None = None

    @property
    def requested_candidate_limit(self) -> int:
        return self.candidate_limit if self.candidate_limit is not None else self.limit

    @property
    def requested_detail_limit(self) -> int:
        return (
            self.detail_limit
            if self.detail_limit is not None
            else self.requested_candidate_limit
        )

    @property
    def requested_per_query_candidate_limit(self) -> int:
        return (
            self.per_query_candidate_limit
            if self.per_query_candidate_limit is not None
            else self.requested_candidate_limit
        )


def initial_state(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "product_id": str(candidate["product_id"]),
        "rank": candidate.get("rank"),
        "status": ProductStatus.PENDING,
        "attempts": 0,
        "errors": [],
        "updated_at": iso_now(),
    }


def set_state(
    state: dict[str, Any],
    status: str,
    error: str | None = None,
) -> None:
    state["status"] = status
    state["updated_at"] = iso_now()
    if error:
        state.setdefault("errors", []).append(error)


class StandalonePipeline:
    def __init__(self, options: PipelineOptions) -> None:
        if not options.keyword.strip():
            raise ValueError("keyword不能为空")
        if options.limit < 1:
            raise ValueError("limit必须大于0")
        if options.candidate_limit is not None and options.candidate_limit < 1:
            raise ValueError("candidate_limit必须大于0")
        if options.detail_limit is not None and options.detail_limit < 1:
            raise ValueError("detail_limit必须大于0")
        if options.task_type not in {"quick", "monitor"}:
            raise ValueError("task_type必须是quick或monitor")
        if options.task_type == "monitor":
            if not options.target_id or not options.search_queries:
                raise ValueError("Monitor Task必须包含target_id和SearchQuery")
            if options.requested_per_query_candidate_limit < 1:
                raise ValueError("per_query_candidate_limit必须大于0")
        if options.detail_retries < 0:
            raise ValueError("detail_retries不能小于0")
        self.options = options
        run_id = options.run_id or new_run_id()
        self.run_root = options.output_root.resolve() / run_id
        self.products_root = self.run_root / "products"
        self.products_root.mkdir(parents=True, exist_ok=True)
        self.logger = setup_run_logger(self.run_root, verbose=options.verbose)
        self.state_path = self.run_root / "batch_state.json"
        self.state_by_id: dict[str, dict[str, Any]] = {}
        self.prepared_roots: dict[str, Path] = {}
        self.search_payload: dict[str, Any] | None = None
        self.web_stage = "initializing"
        self.web_message = "正在初始化本地采集任务"
        self.inspection_runtime: InspectionRuntime | None = None
        self.manual_action_adapter: Any | None = None

    def set_inspection_runtime(
        self, inspection_runtime: InspectionRuntime | None
    ) -> None:
        """Attach D6's file-oriented integration layer."""

        self.inspection_runtime = inspection_runtime

    def set_manual_action_adapter(self, adapter: Any | None) -> None:
        """Attach the Web gate adapter without changing standalone CLI behavior."""

        self.manual_action_adapter = adapter

    def _generate_inspection_recommendation(self, product_root: Path) -> bool:
        if self.inspection_runtime is None:
            return False
        error_path = product_root / INSPECTION_RECOMMENDATION_ERROR_FILE
        try:
            self.inspection_runtime.generate(product_root)
            error_path.unlink(missing_ok=True)
            return True
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            InspectionRuntime.record_error(product_root, exc)
            self.logger.exception(
                "商品%s Phase3已完成，但抽检辅助建议生成失败：%s",
                product_root.name,
                error,
            )
            return False

    def _write_state(self) -> None:
        ordered = sorted(
            self.state_by_id.values(),
            key=lambda item: int(item.get("rank") or 10**9),
        )
        write_json(self.state_path, ordered)
        self._write_web_snapshot()

    def _records_and_batch_payload(
        self,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        search_payload = self.search_payload or {}
        candidates = search_payload.get("candidates") or []
        records = []
        for candidate in candidates:
            product_id = str(candidate["product_id"])
            state = self.state_by_id.get(product_id, initial_state(candidate))
            product_root = self.prepared_roots.get(product_id)
            if product_root is None:
                existing_root = self.products_root / product_id
                if (existing_root / "meta.json").exists():
                    product_root = existing_root
            records.append(build_batch_record(candidate, product_root, state))
        batch_payload = {
            "run_id": self.run_root.name,
            "phase": "standalone_end_to_end",
            "generated_at": iso_now(),
            "keyword": search_payload.get("keyword") or self.options.keyword,
            "search_collection_method": search_payload.get("collection_method"),
            "search_raw_count": search_payload.get("raw_card_count", len(candidates)),
            "search_deduplicated_count": search_payload.get(
                "deduplicated_count", len(candidates)
            ),
            "candidate_count": len(candidates),
            "candidates": candidates,
            "products": records,
        }
        return records, batch_payload

    def _write_web_snapshot(self) -> Path:
        records, batch_payload = self._records_and_batch_payload()
        return write_web_snapshot(
            self.run_root,
            batch_payload,
            records,
            self.web_stage,
            self.web_message,
        )

    def update_web_status(self, stage: str, message: str) -> None:
        self.web_stage = stage
        self.web_message = message
        self._write_web_snapshot()

    def mark_interrupted(self) -> None:
        """Leave resumable product states after a user stops the process."""

        self.web_stage = "interrupted"
        self.web_message = "任务已由用户中止，已保存的数据可以断点续跑"
        for product_id, state in self.state_by_id.items():
            if state.get("status") not in {
                ProductStatus.COLLECTING,
                ProductStatus.PROCESSING,
            }:
                continue
            product_root = self.products_root / product_id
            set_state(
                state,
                ProductStatus.DETAIL_COLLECTED
                if (product_root / "meta.json").exists()
                else ProductStatus.PENDING,
            )
        self._write_state()

    def _write_run_config(self) -> None:
        payload = asdict(self.options)
        for key, value in list(payload.items()):
            if isinstance(value, Path):
                payload[key] = value.as_posix()
        if payload.get("browser_proxy"):
            payload["browser_proxy"] = "configured"
        payload["run_id"] = self.run_root.name
        payload["generated_at"] = iso_now()
        payload["resolved_candidate_limit"] = self.options.requested_candidate_limit
        payload["resolved_detail_limit"] = self.options.requested_detail_limit
        payload["resolved_per_query_candidate_limit"] = (
            self.options.requested_per_query_candidate_limit
        )
        write_json(self.run_root / "run_config.json", payload)

    def _collect_details(
        self,
        context: Any,
        candidates: list[dict[str, Any]],
    ) -> None:
        detail_limit = min(
            len(candidates),
            self.options.requested_detail_limit,
        )
        for index, candidate in enumerate(candidates):
            product_id = str(candidate["product_id"])
            state = self.state_by_id[product_id]
            if index >= detail_limit:
                continue
            existing_root = self.products_root / product_id
            if (
                state.get("status")
                in {
                    ProductStatus.DETAIL_COLLECTED,
                    ProductStatus.PROCESSING,
                    ProductStatus.SUCCESS,
                    ProductStatus.FAILED_PROCESSING,
                }
                and (existing_root / "meta.json").exists()
            ):
                self.prepared_roots[product_id] = existing_root
                self.logger.info("商品%s已有真实详情断点，跳过重复采集", product_id)
                continue
            set_state(state, ProductStatus.COLLECTING)
            self.web_stage = "collecting_details"
            self.web_message = (
                f"正在采集第 {index + 1}/{detail_limit} 个商品：{product_id}"
            )
            self._write_state()
            last_error: str | None = None
            for attempt in range(1, self.options.detail_retries + 2):
                state["attempts"] = attempt
                self._write_state()
                try:
                    collector = PhaseOneCollector(
                        product_url=str(candidate["product_url"]),
                        output_root=self.options.output_root,
                        profile_dir=self.options.profile_dir,
                        channel=self.options.channel,
                        max_scrolls=50,
                        non_interactive=self.options.non_interactive,
                        manual_action_adapter=self.manual_action_adapter,
                        run_root=self.run_root,
                        candidate=candidate,
                        logger=self.logger,
                    )
                    product_root = collector.collect_in_context(context)
                    self.prepared_roots[product_id] = product_root
                    set_state(state, ProductStatus.DETAIL_COLLECTED)
                    self.web_message = (
                        f"已完成第 {index + 1}/{detail_limit} 个商品详情采集"
                    )
                    last_error = None
                    break
                except Exception as exc:
                    last_error = f"attempt {attempt}: {type(exc).__name__}: {exc}"
                    self.logger.exception("商品%s详情采集失败（第%s次）", product_id, attempt)
                    state.setdefault("errors", []).append(last_error)
                    state["updated_at"] = iso_now()
                    self._write_state()
            if last_error is not None:
                set_state(state, ProductStatus.FAILED_COLLECTION)
            self._write_state()
            if index + 1 < detail_limit and self.options.product_delay_seconds > 0:
                time.sleep(self.options.product_delay_seconds)

    def _process_products(self) -> None:
        if self.options.skip_ocr:
            self.logger.warning("已启用--skip-ocr，仅完成搜索和详情采集，不算完整全流程验收")
            return
        runtime: OCRRuntime | None = None
        total = len(self.prepared_roots)
        for index, (product_id, product_root) in enumerate(
            self.prepared_roots.items(), start=1
        ):
            state = self.state_by_id[product_id]
            analysis_exists = (product_root / "analysis.json").is_file()
            recommendation_exists = (
                product_root / INSPECTION_RECOMMENDATION_FILE
            ).is_file()
            if state.get("status") == ProductStatus.SUCCESS and analysis_exists:
                if self.inspection_runtime is None or recommendation_exists:
                    self.logger.info("商品%s已有成功分析结果，断点续跑跳过", product_id)
                    continue
                self.web_stage = "processing_ocr_analysis"
                self.web_message = (
                    f"正在为第 {index}/{total} 个已有分析商品补生成抽检辅助建议"
                )
                self._write_state()
                generated = self._generate_inspection_recommendation(product_root)
                self.web_message = (
                    f"已为第 {index}/{total} 个商品补生成抽检辅助建议"
                    if generated
                    else f"第 {index}/{total} 个商品的抽检辅助建议暂不可用"
                )
                self._write_state()
                continue
            set_state(state, ProductStatus.PROCESSING)
            self.web_stage = "processing_ocr_analysis"
            self.web_message = f"正在处理第 {index}/{total} 个商品的 OCR 与风险分析"
            self._write_state()
            try:
                if runtime is None:
                    runtime = create_ocr_runtime(self.options.cache_dir)
                run_ocr(
                    product_root=product_root,
                    cache_dir=self.options.cache_dir,
                    runtime=runtime,
                )
                run_analysis(
                    product_root,
                    self.options.rule_config,
                    write_run_outputs=False,
                )
                set_state(state, ProductStatus.SUCCESS)
                generated = self._generate_inspection_recommendation(product_root)
                self.web_message = (
                    f"已完成第 {index}/{total} 个商品的 OCR、风险分析与抽检辅助建议"
                    if generated
                    else (
                        f"已完成第 {index}/{total} 个商品的 OCR 与风险分析；"
                        "抽检辅助建议暂不可用"
                    )
                )
                self.logger.info("商品%s完成OCR与风险分析", product_id)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                set_state(state, ProductStatus.FAILED_PROCESSING, error)
                self.logger.exception("商品%s OCR/分析失败", product_id)
            self._write_state()

    def _write_outputs(self, search_payload: dict[str, Any]) -> dict[str, Path]:
        self.search_payload = search_payload
        records, batch_payload = self._records_and_batch_payload()
        products_json = self.run_root / "products.json"
        products_csv = self.run_root / "products.csv"
        summary = self.run_root / "summary.md"
        write_json(products_json, batch_payload)
        write_batch_csv(products_csv, records)
        summary.write_text(
            build_batch_summary(batch_payload, records), encoding="utf-8"
        )
        web_snapshot = self._write_web_snapshot()
        return {
            "run_root": self.run_root,
            "state": self.state_path,
            "products_json": products_json,
            "products_csv": products_csv,
            "summary": summary,
            "web_snapshot": web_snapshot,
            "run_log": self.run_root / "run.log",
        }

    def resume_processing(self, collect_pending_details: bool = False) -> dict[str, Path]:
        """Resume saved detail collection and/or offline OCR/analysis."""

        search_path = self.run_root / "search" / "search_candidates.json"
        if not search_path.exists():
            raise RuntimeError(f"断点目录缺少搜索结果：{search_path}")
        if not self.state_path.exists():
            raise RuntimeError(f"断点目录缺少批次状态：{self.state_path}")
        search_payload = read_json(search_path)
        self.search_payload = search_payload
        candidates = search_payload.get("candidates") or []
        states = read_json(self.state_path)
        if not isinstance(states, list):
            raise RuntimeError("batch_state.json格式错误，预期为数组")
        self.state_by_id = {
            str(state["product_id"]): state
            for state in states
            if isinstance(state, dict) and state.get("product_id")
        }
        for candidate in candidates:
            product_id = str(candidate["product_id"])
            self.state_by_id.setdefault(product_id, initial_state(candidate))
            product_root = self.products_root / product_id
            if (product_root / "meta.json").exists():
                self.prepared_roots[product_id] = product_root
        if not self.prepared_roots:
            if not collect_pending_details:
                raise RuntimeError("断点目录中没有已采集详情的商品，无法继续OCR/分析")
        self.logger.info(
            "断点续跑开始：目录=%s，已采集详情商品=%s",
            self.run_root,
            len(self.prepared_roots),
        )
        if collect_pending_details:
            self.update_web_status("collecting_details", "正在继续采集未完成的商品详情")
            try:
                from playwright.sync_api import sync_playwright
            except ImportError as exc:
                raise RuntimeError(
                    "缺少Playwright，请先运行：python -m pip install -r requirements-phase1.txt"
                ) from exc
            settings = BrowserSettings(
                profile_dir=self.options.profile_dir,
                channel=self.options.channel,
                mode=self.options.browser_mode,
                executable_path=self.options.browser_executable,
                cdp_port=self.options.cdp_port,
                headless=self.options.headless,
                non_interactive=self.options.non_interactive,
                proxy_server=self.options.browser_proxy,
                direct_connection=self.options.direct_browser,
            )
            with sync_playwright() as playwright:
                browser_session = launch_browser_session(
                    playwright,
                    settings,
                    logger=self.logger,
                )
                try:
                    self._collect_details(
                        browser_session.context,
                        candidates,
                    )
                finally:
                    browser_session.close()
        if self.options.skip_ocr:
            self.update_web_status("collection_completed", "详情采集已完成，未执行 OCR")
        else:
            self.update_web_status(
                "processing_ocr_analysis", "正在继续离线 OCR 与风险分析"
            )
        self._process_products()
        final_stage = (
            "collection_completed"
            if self.options.skip_ocr
            else "completed_with_errors"
            if any(
                str(state.get("status") or "").startswith("failed")
                for state in self.state_by_id.values()
            )
            else "completed"
        )
        self.update_web_status(
            final_stage,
            "详情采集已完成，未执行 OCR"
            if self.options.skip_ocr
            else "本次任务处理完成",
        )
        outputs = self._write_outputs(search_payload)
        self.logger.info("断点续跑完成：%s", self.run_root)
        return outputs

    def run(self) -> dict[str, Path]:
        self._write_run_config()
        self.update_web_status("searching", "浏览器已启动，正在搜索淘宝商品")
        self.logger.info(
            "standalone全流程开始：type=%s, keyword=%s, candidate_limit=%s, detail_limit=%s",
            self.options.task_type,
            self.options.keyword,
            self.options.requested_per_query_candidate_limit
            if self.options.task_type == "monitor"
            else self.options.requested_candidate_limit,
            self.options.requested_detail_limit,
        )
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "缺少Playwright，请先运行：python -m pip install -r requirements-phase1.txt"
            ) from exc

        search_payload: dict[str, Any]
        settings = BrowserSettings(
            profile_dir=self.options.profile_dir,
            channel=self.options.channel,
            mode=self.options.browser_mode,
            executable_path=self.options.browser_executable,
            cdp_port=self.options.cdp_port,
            headless=self.options.headless,
            non_interactive=self.options.non_interactive,
            proxy_server=self.options.browser_proxy,
            direct_connection=self.options.direct_browser,
        )
        with sync_playwright() as playwright:
            browser_session = launch_browser_session(
                playwright,
                settings,
                logger=self.logger,
            )
            context = browser_session.context
            try:
                if self.options.task_type == "monitor":
                    self.update_web_status(
                        "searching", "正在按监测对象配置串行执行多个淘宝搜索词"
                    )
                    search_payload = DiscoveryCoordinator(
                        context=context,
                        run_root=self.run_root,
                        logger=self.logger,
                        non_interactive=self.options.non_interactive,
                        manual_action_adapter=self.manual_action_adapter,
                    ).discover(
                        target={
                            "target_id": self.options.target_id,
                            "standard_name": self.options.target_name
                            or self.options.keyword,
                        },
                        queries=list(self.options.search_queries),
                        per_query_candidate_limit=(
                            self.options.requested_per_query_candidate_limit
                        ),
                        detail_limit=self.options.requested_detail_limit,
                    )
                else:
                    search_payload = LiveSearchCollector(
                        context=context,
                        run_root=self.run_root,
                        logger=self.logger,
                        non_interactive=self.options.non_interactive,
                        manual_action_adapter=self.manual_action_adapter,
                    ).collect(
                        self.options.keyword,
                        candidate_limit=self.options.requested_candidate_limit,
                        detail_limit=self.options.requested_detail_limit,
                    )
                self.search_payload = search_payload
                self.state_by_id = {
                    str(candidate["product_id"]): initial_state(candidate)
                    for candidate in search_payload["candidates"]
                }
                self.web_stage = "collecting_details"
                self.web_message = "搜索完成，准备采集商品详情"
                self._write_state()
                self._collect_details(context, search_payload["candidates"])
            finally:
                browser_session.close()

        if self.options.skip_ocr:
            self.update_web_status("collection_completed", "详情采集已完成，未执行 OCR")
        else:
            self.update_web_status(
                "processing_ocr_analysis", "详情采集完成，开始离线 OCR 与风险分析"
            )
        self._process_products()
        final_stage = (
            "collection_completed"
            if self.options.skip_ocr
            else "completed_with_errors"
            if any(
                str(state.get("status") or "").startswith("failed")
                for state in self.state_by_id.values()
            )
            else "completed"
        )
        self.update_web_status(
            final_stage,
            "详情采集已完成，未执行 OCR"
            if self.options.skip_ocr
            else "本次任务处理完成",
        )
        outputs = self._write_outputs(search_payload)
        success_count = sum(
            state["status"] == ProductStatus.SUCCESS
            for state in self.state_by_id.values()
        )
        self.logger.info(
            "standalone全流程结束：候选%s，端到端成功%s，目录=%s",
            len(search_payload["candidates"]),
            success_count,
            self.run_root,
        )
        return outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="淘宝食药同源风险线索发现standalone全流程"
    )
    parser.add_argument("--keyword", help="淘宝搜索关键词，例如酸枣仁")
    parser.add_argument(
        "--resume-run",
        type=Path,
        help="从已有运行目录继续OCR和分析，不再访问淘宝",
    )
    parser.add_argument(
        "--resume-details",
        action="store_true",
        help="与--resume-run配合，继续采集尚未完成的候选详情",
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        help="搜索阶段最多保留的去重候选数量，默认10",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="兼容旧命令；等价于--candidate-limit",
    )
    parser.add_argument(
        "--detail-limit",
        type=int,
        help="本次实际采集详情的候选数量，默认与limit相同",
    )
    parser.add_argument("--output-root", type=Path, default=Path("output"))
    parser.add_argument(
        "--database",
        type=Path,
        help="默认按output-root同级的data/app.db约定解析",
    )
    parser.add_argument(
        "--inspection-config",
        type=Path,
        default=DEFAULT_INSPECTION_CONFIG_PATH,
    )
    parser.add_argument(
        "--risk-substance-config",
        type=Path,
        default=DEFAULT_RISK_SUBSTANCE_CONFIG_PATH,
    )
    parser.add_argument("--profile-dir", type=Path, default=Path(".browser-profile"))
    parser.add_argument("--channel", default="chrome")
    parser.add_argument(
        "--browser-mode",
        choices=("cdp", "persistent"),
        default="cdp",
        help="浏览器启动方式；默认CDP，persistent保留为兼容/诊断模式",
    )
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--cdp-port", type=int, default=9222)
    parser.add_argument("--config", type=Path, default=Path("config/effect_keywords.json"))
    parser.add_argument(
        "--cache-dir", type=Path, default=Path.home() / ".cache" / "paddlex"
    )
    parser.add_argument("--run-id")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    network_group = parser.add_mutually_exclusive_group()
    network_group.add_argument(
        "--browser-proxy",
        help="可选浏览器代理，例如http://127.0.0.1:7890；默认使用Chrome/系统设置",
    )
    network_group.add_argument(
        "--direct-browser",
        action="store_true",
        help="仅让项目打开的浏览器绕过系统代理直连，不影响Codex或其他应用",
    )
    parser.add_argument("--product-delay", type=float, default=2.0)
    parser.add_argument("--detail-retries", type=int, default=1)
    parser.add_argument("--skip-ocr", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    if (
        args.candidate_limit is not None
        and args.limit is not None
        and args.candidate_limit != args.limit
    ):
        parser.error("--candidate-limit与兼容参数--limit不能设置为不同数值")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.resume_run:
        resume_root = args.resume_run.expanduser().resolve()
        config_path = resume_root / "run_config.json"
        if not config_path.exists():
            print(f"断点目录缺少run_config.json：{config_path}", file=sys.stderr)
            return 2
        old_config = read_json(config_path)
        keyword = args.keyword or str(old_config.get("keyword") or "")
        output_root = resume_root.parent
        run_id = resume_root.name
        candidate_limit = (
            args.candidate_limit
            if args.candidate_limit is not None
            else args.limit
            if args.limit is not None
            else old_config.get("resolved_candidate_limit")
            or old_config.get("candidate_limit")
            or old_config.get("limit")
            or 10
        )
        detail_limit = (
            args.detail_limit
            if args.detail_limit is not None
            else old_config.get("resolved_detail_limit")
            or old_config.get("detail_limit")
        )
    else:
        if args.resume_details:
            print("--resume-details必须与--resume-run同时使用", file=sys.stderr)
            return 2
        if not args.keyword:
            print("必须提供--keyword，或使用--resume-run继续已有运行", file=sys.stderr)
            return 2
        keyword = args.keyword
        output_root = args.output_root
        run_id = args.run_id
        candidate_limit = (
            args.candidate_limit
            if args.candidate_limit is not None
            else args.limit
            if args.limit is not None
            else 10
        )
        detail_limit = args.detail_limit
    options = PipelineOptions(
        keyword=keyword,
        limit=candidate_limit,
        candidate_limit=candidate_limit,
        detail_limit=detail_limit,
        output_root=output_root,
        profile_dir=args.profile_dir,
        channel=args.channel,
        browser_mode=args.browser_mode,
        browser_executable=args.browser_executable,
        cdp_port=args.cdp_port,
        rule_config=args.config,
        cache_dir=args.cache_dir,
        run_id=run_id,
        headless=args.headless,
        non_interactive=args.non_interactive,
        browser_proxy=args.browser_proxy,
        direct_browser=args.direct_browser,
        product_delay_seconds=args.product_delay,
        detail_retries=args.detail_retries,
        skip_ocr=args.skip_ocr,
        verbose=args.verbose,
    )
    pipeline: StandalonePipeline | None = None
    try:
        inspection_runtime = InspectionRuntime.create(
            output_root,
            database_path=args.database,
            inspection_config=args.inspection_config,
            risk_substance_config=args.risk_substance_config,
        )
        pipeline = StandalonePipeline(options)
        pipeline.set_inspection_runtime(inspection_runtime)
        outputs = (
            pipeline.resume_processing(collect_pending_details=args.resume_details)
            if args.resume_run
            else pipeline.run()
        )
    except KeyboardInterrupt:
        if pipeline is not None:
            pipeline.mark_interrupted()
        print("用户中止运行", file=sys.stderr)
        return 130
    except RuntimeError as exc:
        if pipeline is not None:
            pipeline.update_web_status("failed", f"全流程未完成：{exc}")
        logging.getLogger(__name__).error("全流程未完成：%s", exc)
        print(f"全流程未完成：{exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        if pipeline is not None:
            pipeline.update_web_status(
                "failed", f"全流程运行失败：{type(exc).__name__}: {exc}"
            )
        logging.getLogger(__name__).exception("全流程运行失败")
        print(f"全流程运行失败：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(f"运行目录：{outputs['run_root']}")
    print(f"汇总报告：{outputs['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
