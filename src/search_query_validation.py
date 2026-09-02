"""Low-frequency, search-only validation for configured MonitorTarget queries."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Callable

from src.data_store import validate_monitor_config
from src.runtime import iso_now, new_run_id, read_json, setup_run_logger, write_json
from src.taobao_live import BrowserSettings, LiveSearchCollector, launch_browser_session


PILOT_TARGET_IDS = (
    "food-medicine-2002-078",  # 酸枣仁
    "food-medicine-2002-049",  # 茯苓
    "food-medicine-2002-020",  # 龙眼肉（桂圆）
    "food-medicine-2019-001",  # 当归
    "food-medicine-2023-003",  # 铁皮石斛
    "food-medicine-2024-004",  # 化橘红
)


def select_queries(
    config: dict[str, Any],
    target_ids: tuple[str, ...],
    query_ids: set[str] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    by_id = {target["target_id"]: target for target in config["targets"]}
    missing = [target_id for target_id in target_ids if target_id not in by_id]
    if missing:
        raise ValueError(f"配置中不存在Pilot MonitorTarget：{', '.join(missing)}")
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for target_id in target_ids:
        target = by_id[target_id]
        queries = sorted(
            target.get("queries") or [],
            key=lambda item: (int(item.get("order") or 0), str(item.get("query_id") or "")),
        )
        for query in queries:
            if query_ids is None or query["query_id"] in query_ids:
                selected.append((target, query))
    if query_ids is not None:
        found = {query["query_id"] for _, query in selected}
        missing_queries = sorted(query_ids - found)
        if missing_queries:
            raise ValueError(f"Pilot中不存在SearchQuery：{', '.join(missing_queries)}")
    if not selected:
        raise ValueError("没有可执行的Pilot SearchQuery")
    return selected


def _title_rows(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "rank": candidate.get("rank"),
            "product_id": candidate.get("product_id"),
            "title": candidate.get("product_name") or "",
            "shop": candidate.get("shop_name") or "",
            "region": candidate.get("region") or "",
        }
        for candidate in candidates[:10]
    ]


def run_search_validation(
    *,
    context: Any,
    run_root: Path,
    logger: Any,
    selected: list[tuple[dict[str, Any], dict[str, Any]]],
    candidate_limit: int = 10,
    pause_seconds: float = 3.0,
    non_interactive: bool = False,
    collector_factory: Callable[..., Any] = LiveSearchCollector,
) -> dict[str, Any]:
    if not 1 <= candidate_limit <= 20:
        raise ValueError("search-only验证的candidate_limit必须在1到20之间")
    started_at = iso_now()
    results: list[dict[str, Any]] = []
    for position, (target, query) in enumerate(selected, start=1):
        query_root = run_root / "pilot_queries" / query["query_id"]
        logger.info(
            "Pilot search-only %s/%s：target=%s, query=%s",
            position,
            len(selected),
            target["standard_name"],
            query["query_text"],
        )
        record = {
            "target_id": target["target_id"],
            "standard_name": target["standard_name"],
            "query_id": query["query_id"],
            "query_text": query["query_text"],
            "query_source": query["query_source"],
            "configured_validation_status": query["validation_status"],
            "started_at": iso_now(),
        }
        try:
            payload = collector_factory(
                context=context,
                run_root=query_root,
                logger=logger,
                non_interactive=non_interactive,
            ).collect(
                query["query_text"],
                candidate_limit=candidate_limit,
                detail_limit=1,
            )
            candidates = payload.get("candidates") or []
            record.update(
                {
                    "execution_status": "completed",
                    "actual_candidates": len(candidates),
                    "raw_card_count": int(payload.get("raw_card_count") or 0),
                    "stop_reason": payload.get("search_stop_reason") or "unknown",
                    "selector_health": payload.get("selector_health") or {},
                    "titles": _title_rows(candidates),
                    "diagnostics_path": (
                        query_root.relative_to(run_root)
                        / "search"
                        / "search_diagnostics.json"
                    ).as_posix(),
                    "relevance_review": "pending_manual_review",
                    "completed_at": iso_now(),
                }
            )
        except Exception as exc:
            record.update(
                {
                    "execution_status": "failed",
                    "actual_candidates": 0,
                    "stop_reason": "error",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "relevance_review": "not_reviewed",
                    "completed_at": iso_now(),
                }
            )
            results.append(record)
            write_json(
                run_root / "query_validation_results.json",
                {
                    "run_id": run_root.name,
                    "phase": "search_query_pilot_validation",
                    "started_at": started_at,
                    "completed_at": iso_now(),
                    "candidate_limit": candidate_limit,
                    "status": "stopped_after_failure",
                    "results": results,
                },
            )
            logger.error("Pilot验证停止，保留已完成结果：%s: %s", type(exc).__name__, exc)
            break
        results.append(record)
        write_json(
            run_root / "query_validation_results.json",
            {
                "run_id": run_root.name,
                "phase": "search_query_pilot_validation",
                "started_at": started_at,
                "completed_at": iso_now(),
                "candidate_limit": candidate_limit,
                "status": "running" if position < len(selected) else "completed",
                "results": results,
            },
        )
        if position < len(selected) and pause_seconds > 0:
            time.sleep(pause_seconds)
    status = (
        "completed"
        if len(results) == len(selected)
        and all(result["execution_status"] == "completed" for result in results)
        else "stopped_after_failure"
    )
    summary = {
        "run_id": run_root.name,
        "phase": "search_query_pilot_validation",
        "started_at": started_at,
        "completed_at": iso_now(),
        "candidate_limit": candidate_limit,
        "status": status,
        "results": results,
    }
    write_json(run_root / "query_validation_results.json", summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="正式SearchQuery低频search-only验证")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/monitor_targets.reference.json"),
    )
    parser.add_argument("--target-id", action="append", dest="target_ids")
    parser.add_argument("--query-id", action="append", dest="query_ids")
    parser.add_argument("--candidate-limit", type=int, default=10)
    parser.add_argument("--output-root", type=Path, default=Path("output"))
    parser.add_argument("--run-id")
    parser.add_argument("--profile-dir", type=Path, default=Path(".browser-profile"))
    parser.add_argument("--channel", default="chrome")
    parser.add_argument("--browser-mode", choices=("cdp", "persistent"), default="cdp")
    parser.add_argument("--browser-executable", type=Path)
    parser.add_argument("--cdp-port", type=int, default=9222)
    parser.add_argument("--browser-proxy")
    parser.add_argument("--direct-browser", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--pause-seconds", type=float, default=3.0)
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = validate_monitor_config(read_json(args.config))
        selected = select_queries(
            config,
            tuple(args.target_ids or PILOT_TARGET_IDS),
            set(args.query_ids) if args.query_ids else None,
        )
    except (OSError, ValueError, TypeError) as exc:
        print(f"SearchQuery验证配置错误：{exc}", file=sys.stderr)
        return 2
    run_root = (args.output_root / (args.run_id or new_run_id("query_validation"))).resolve()
    logger = setup_run_logger(run_root, verbose=args.verbose)
    write_json(
        run_root / "validation_request.json",
        {
            "created_at": iso_now(),
            "config_path": str(args.config.resolve()),
            "candidate_limit": args.candidate_limit,
            "target_ids": [target["target_id"] for target, _ in selected],
            "query_ids": [query["query_id"] for _, query in selected],
            "search_only": True,
        },
    )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("缺少Playwright，无法执行真实search-only验证")
        return 2
    settings = BrowserSettings(
        profile_dir=args.profile_dir,
        channel=args.channel,
        mode=args.browser_mode,
        executable_path=args.browser_executable,
        cdp_port=args.cdp_port,
        non_interactive=args.non_interactive,
        proxy_server=args.browser_proxy,
        direct_connection=args.direct_browser,
    )
    with sync_playwright() as playwright:
        browser_session = launch_browser_session(playwright, settings, logger=logger)
        try:
            summary = run_search_validation(
                context=browser_session.context,
                run_root=run_root,
                logger=logger,
                selected=selected,
                candidate_limit=args.candidate_limit,
                pause_seconds=max(args.pause_seconds, 0),
                non_interactive=args.non_interactive,
            )
        finally:
            browser_session.close()
    print(f"SearchQuery验证结果：{run_root / 'query_validation_results.json'}")
    return 0 if summary["status"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
