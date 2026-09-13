"""Low-frequency, search-only validation for configured MonitorTarget queries."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Callable

from src.data_store import validate_monitor_config
from src.monitor_query_validation import REVIEW_LABEL_ZH, DECISION_ZH
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


def _review_result_cards(
    candidates: list[dict[str, Any]],
    *,
    raw_artifact_refs: list[str],
) -> tuple[list[dict[str, Any]], int]:
    """Keep first-seen rank while deduplicating only by marketplace Product ID."""

    result: list[dict[str, Any]] = []
    by_product_id: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    for fallback_rank, candidate in enumerate(candidates, start=1):
        rank = candidate.get("rank") or fallback_rank
        product_id = str(candidate.get("product_id") or "").strip()
        occurrence = {
            "rank": rank,
            "productId": product_id or None,
            "title": candidate.get("product_name") or "",
            "shop": candidate.get("shop_name") or "",
            "price": candidate.get("price_text") or None,
            "cardMetadata": {
                "searchRegion": candidate.get("region") or None,
                "salesText": candidate.get("sales_text") or None,
                "platform": candidate.get("platform") or None,
                "sourceProductUrl": candidate.get("source_product_url")
                or candidate.get("product_url")
                or None,
                "thumbnailUrl": candidate.get("snapshot_image_path") or None,
            },
        }
        if not product_id or product_id not in by_product_id:
            canonical = {
                **occurrence,
                "duplicateOccurrences": [],
                "rawArtifactRefs": list(raw_artifact_refs),
            }
            result.append(canonical)
            if product_id:
                by_product_id[product_id] = canonical
            continue
        duplicate_count += 1
        by_product_id[product_id]["duplicateOccurrences"].append(occurrence)
    return result, duplicate_count


def _review_queue_record(
    query_record: dict[str, Any],
    result_cards: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "batchId": query_record.get("batchId"),
        "targetId": query_record.get("targetId"),
        "queryId": query_record.get("queryId"),
        "queryText": query_record.get("queryText"),
        "reviewStatus": query_record.get("reviewStatus"),
        "evaluationRule": "first_10_unique_assessable_in_original_search_order",
        "results": [
            {
                **card,
                "reviewedLabel": None,
                "reviewedAt": None,
                "reviewNote": None,
            }
            for card in result_cards
        ],
    }


def _markdown_cell(value: Any) -> str:
    return str(value or "—").replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_review_queue_markdown(queue: dict[str, Any]) -> str:
    lines = [
        f"# 人工复核队列 — {queue['queryText']}",
        "",
        f"- 批次：`{queue['batchId']}`",
        f"- 监测对象：`{queue['targetId']}`",
        f"- SearchQuery：`{queue['queryId']}`",
        "- 评价规则：按原始搜索顺序取前 10 个唯一、可评估结果；信息不足与重复结果跳过。",
        "",
    ]
    decision = queue.get("decision")
    if decision:
        metrics = queue.get("metrics") or {}
        lines.extend(
            [
                f"- 复核时间：{queue.get('reviewedAt') or '—'}",
                f"- 最终决策：{queue.get('decisionZh') or DECISION_ZH.get(decision, decision)}（机器值：`{decision}`）",
                f"- 评价结果：食品相关 {metrics.get('relevantCount', 0)} / 可评估 {metrics.get('assessableCount', 0)}，相关率 {float(metrics.get('relevanceRate') or 0):.0%}",
                f"- 决策说明：{queue.get('decisionNote') or '—'}",
                "",
            ]
        )
    else:
        lines.extend(["- 状态：等待人工复核；人工标签和复核说明保持空白。", ""])
    lines.extend(
        [
        "| 序号 | 商品ID | 商品标题 | 店铺 | 价格 | 卡片信息 | 重复出现 | 人工标签 | 机器标签 | 复核说明 | Raw artifact |",
        "|---:|---|---|---|---:|---|---:|---|---|---|---|",
        ]
    )
    for card in queue.get("results") or []:
        metadata = card.get("cardMetadata") or {}
        metadata_text = "; ".join(
            f"{key}={value}"
            for key, value in metadata.items()
            if value not in {None, ""}
        )
        raw_ref = next(iter(card.get("rawArtifactRefs") or []), "")
        machine_label = card.get("reviewedLabel") or ""
        label_zh = card.get("reviewedLabelZh") or REVIEW_LABEL_ZH.get(machine_label, "")
        lines.append(
            "| "
            + " | ".join(
                [
                    _markdown_cell(card.get("rank")),
                    _markdown_cell(card.get("productId")),
                    _markdown_cell(card.get("title")),
                    _markdown_cell(card.get("shop")),
                    _markdown_cell(card.get("price")),
                    _markdown_cell(metadata_text),
                    str(len(card.get("duplicateOccurrences") or [])),
                    _markdown_cell(label_zh),
                    _markdown_cell(machine_label),
                    _markdown_cell(card.get("reviewNote")),
                    _markdown_cell(raw_ref),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def _contract_record(batch_id: str, record: dict[str, Any]) -> dict[str, Any]:
    raw_refs = list(record.get("raw_artifact_refs") or [])
    return {
        "batchId": batch_id,
        "targetId": record.get("target_id"),
        "standardName": record.get("standard_name"),
        "queryId": record.get("query_id"),
        "queryText": record.get("query_text"),
        "startedAt": record.get("started_at"),
        "completedAt": record.get("completed_at"),
        "executionStatus": record.get("execution_status"),
        "resultCount": int(record.get("raw_result_count") or 0),
        "rawResultCount": int(record.get("raw_result_count") or 0),
        "uniqueResultCount": int(record.get("unique_result_count") or 0),
        "duplicateCount": int(record.get("duplicate_count") or 0),
        "resultCards": list(record.get("result_cards") or []),
        "labels": {
            "relevant_food": [],
            "raw_medicinal_or_nonfood_scope": [],
            "non_food": [],
            "ambiguous": [],
            "duplicate": [],
        },
        "metrics": {
            "assessableCount": None,
            "relevantCount": None,
            "relevanceRate": None,
        },
        "decision": None,
        "reviewedAt": None,
        "reviewStatus": "pending_manual_review"
        if record.get("execution_status") == "completed"
        else "not_reviewed",
        "rawSourceArtifactRefs": raw_refs,
        "blocker": record.get("stop_reason")
        if record.get("execution_status") == "failed"
        else None,
        "error": (
            {
                "type": record.get("error_type"),
                "message": record.get("error_message"),
            }
            if record.get("execution_status") == "failed"
            else None
        ),
    }


def _write_validation_state(run_root: Path, summary: dict[str, Any]) -> None:
    write_json(run_root / "query_validation_results.json", summary)
    queries_root = run_root / "queries"
    review_root = run_root / "review"
    for record in summary.get("results") or []:
        contract_record = _contract_record(run_root.name, record)
        write_json(
            queries_root / f"{record['query_id']}.json",
            contract_record,
        )
        review_queue = _review_queue_record(
            contract_record,
            contract_record["resultCards"],
        )
        review_json_path = review_root / f"{record['query_id']}.json"
        write_json(review_json_path, review_queue)
        review_markdown_path = review_root / f"{record['query_id']}.md"
        review_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        review_markdown_path.write_text(
            render_review_queue_markdown(review_queue),
            encoding="utf-8",
        )
    query_entries = []
    for path in sorted(queries_root.glob("*.json")) if queries_root.is_dir() else []:
        item = read_json(path)
        query_entries.append(
            {
                "targetId": item.get("targetId"),
                "queryId": item.get("queryId"),
                "queryText": item.get("queryText"),
                "executionStatus": item.get("executionStatus"),
                "reviewStatus": item.get("reviewStatus"),
                "artifact": path.relative_to(run_root).as_posix(),
                "reviewQueue": {
                    "json": f"review/{item['queryId']}.json",
                    "markdown": f"review/{item['queryId']}.md",
                },
            }
        )
    completed_count = sum(
        item.get("executionStatus") == "completed" for item in query_entries
    )
    failed_count = sum(item.get("executionStatus") == "failed" for item in query_entries)
    if summary.get("status") == "running":
        manifest_status = "running"
    elif query_entries and failed_count == 0:
        manifest_status = "complete"
    elif completed_count:
        manifest_status = "partial"
    else:
        manifest_status = "failed"
    write_json(
        run_root / "manifest.json",
        {
            "batchId": run_root.name,
            "contractVersion": 1,
            "phase": "search_query_validation",
            "searchOnly": True,
            "startedAt": summary.get("started_at"),
            "completedAt": summary.get("completed_at"),
            "collectionRawLimit": summary.get("candidate_limit"),
            "evaluationSampleSize": 10,
            "status": manifest_status,
            "queries": query_entries,
        },
    )


def remaining_queries_for_resume(
    run_root: Path,
    selected: list[tuple[dict[str, Any], dict[str, Any]]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    completed_query_ids: set[str] = set()
    queries_root = run_root / "queries"
    if queries_root.is_dir():
        for path in queries_root.glob("*.json"):
            try:
                item = read_json(path)
            except (OSError, ValueError, TypeError):
                continue
            if item.get("executionStatus") == "completed":
                completed_query_ids.add(str(item.get("queryId") or ""))
    return [
        item for item in selected if item[1]["query_id"] not in completed_query_ids
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
            raw_artifact_refs = [
                (
                    query_root.relative_to(run_root)
                    / "search"
                    / artifact_name
                ).as_posix()
                for artifact_name in (
                    "search_candidates.json",
                    "search_candidates.csv",
                    "search_diagnostics.json",
                    "search_results.png",
                    "search_page.html",
                    "scroll_states.json",
                )
            ]
            result_cards, duplicate_count = _review_result_cards(
                candidates,
                raw_artifact_refs=raw_artifact_refs,
            )
            record.update(
                {
                    "execution_status": "completed",
                    "actual_candidates": len(candidates),
                    "raw_result_count": len(candidates),
                    "unique_result_count": len(result_cards),
                    "duplicate_count": duplicate_count,
                    "raw_card_count": int(payload.get("raw_card_count") or 0),
                    "stop_reason": payload.get("search_stop_reason") or "unknown",
                    "selector_health": payload.get("selector_health") or {},
                    "titles": _title_rows(candidates),
                    "result_cards": result_cards,
                    "raw_artifact_refs": raw_artifact_refs,
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
            failure_raw_refs = [
                (
                    query_root.relative_to(run_root)
                    / "search"
                    / artifact_name
                ).as_posix()
                for artifact_name in (
                    "search_diagnostics.json",
                    "search_error.png",
                    "search_error.html",
                )
            ]
            record.update(
                {
                    "execution_status": "failed",
                    "actual_candidates": 0,
                    "raw_result_count": 0,
                    "unique_result_count": 0,
                    "duplicate_count": 0,
                    "result_cards": [],
                    "raw_artifact_refs": failure_raw_refs,
                    "stop_reason": "error",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "relevance_review": "not_reviewed",
                    "completed_at": iso_now(),
                }
            )
            results.append(record)
            _write_validation_state(
                run_root,
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
        _write_validation_state(
            run_root,
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
    _write_validation_state(run_root, summary)
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
    parser.add_argument("--resume", action="store_true")
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
    if args.resume:
        selected = remaining_queries_for_resume(run_root, selected)
        if not selected:
            print(f"批次已无待执行Query：{run_root}")
            return 0
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
