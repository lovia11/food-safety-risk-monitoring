"""Deterministic multi-query candidate discovery built on the frozen collector."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from src.runtime import iso_now, write_json
from src.taobao_live import LiveSearchCollector


def _safe_segment(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return normalized[:48] or "query"


class DiscoveryCoordinator:
    """Run configured queries serially and merge products by first valid hit."""

    def __init__(
        self,
        *,
        context: Any,
        run_root: Path,
        logger: Any,
        non_interactive: bool = False,
        collector_factory: Callable[..., Any] = LiveSearchCollector,
        manual_action_adapter: Any | None = None,
    ) -> None:
        self.context = context
        self.run_root = run_root.resolve()
        self.logger = logger
        self.non_interactive = non_interactive
        self.collector_factory = collector_factory
        self.manual_action_adapter = manual_action_adapter

    def discover(
        self,
        *,
        target: dict[str, Any],
        queries: list[dict[str, Any]],
        per_query_candidate_limit: int,
        detail_limit: int,
    ) -> dict[str, Any]:
        enabled = [item for item in queries if item.get("enabled", True)]
        enabled.sort(key=lambda item: (int(item.get("order") or 0), str(item.get("query_id") or "")))
        if not enabled:
            raise ValueError("监测对象没有启用的SearchQuery")
        if per_query_candidate_limit < 1 or detail_limit < 1:
            raise ValueError("候选数量和详情数量必须大于0")

        started_at = iso_now()
        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        hits: list[dict[str, Any]] = []
        query_results: list[dict[str, Any]] = []
        raw_card_count = 0

        for position, query in enumerate(enabled, start=1):
            query_id = str(query.get("query_id") or f"query_{position}")
            query_text = str(query.get("query_text") or "").strip()
            if not query_text:
                raise ValueError(f"SearchQuery {query_id} 的query_text不能为空")
            query_root = (
                self.run_root
                / "search_queries"
                / f"{position:02d}_{_safe_segment(query_id)}"
            )
            collector = self.collector_factory(
                context=self.context,
                run_root=query_root,
                logger=self.logger,
                non_interactive=self.non_interactive,
                manual_action_adapter=self.manual_action_adapter,
            )
            payload = collector.collect(
                query_text,
                candidate_limit=per_query_candidate_limit,
                detail_limit=detail_limit,
            )
            candidates = [
                item for item in (payload.get("candidates") or []) if isinstance(item, dict)
            ]
            raw_card_count += int(payload.get("raw_card_count") or len(candidates))
            discovered_at = str(payload.get("completed_at") or iso_now())
            for candidate in candidates:
                product_id = str(candidate.get("product_id") or "").strip()
                if not product_id:
                    continue
                hits.append(
                    {
                        "task_id": self.run_root.name,
                        "product_id": product_id,
                        "query_id": query_id,
                        "query_text": query_text,
                        "rank": candidate.get("rank"),
                        "discovered_at": candidate.get("crawl_time") or discovered_at,
                    }
                )
                if product_id in seen:
                    continue
                seen.add(product_id)
                merged_candidate = dict(candidate)
                merged_candidate["discovery_query_id"] = query_id
                merged_candidate["discovery_query_text"] = query_text
                merged_candidate["discovery_query_rank"] = candidate.get("rank")
                merged.append(merged_candidate)
            query_results.append(
                {
                    "query_id": query_id,
                    "query_text": query_text,
                    "order": query.get("order", position),
                    "candidate_count": len(candidates),
                    "raw_card_count": int(payload.get("raw_card_count") or len(candidates)),
                    "stop_reason": payload.get("search_stop_reason") or "unknown",
                    "diagnostics_path": (
                        query_root.relative_to(self.run_root)
                        / "search"
                        / "search_diagnostics.json"
                    ).as_posix(),
                }
            )
            self.logger.info(
                "监测Query完成：%s，候选%s，停止原因=%s",
                query_text,
                len(candidates),
                payload.get("search_stop_reason") or "unknown",
            )

        for rank, candidate in enumerate(merged, start=1):
            candidate["rank"] = rank

        target_id = str(target.get("target_id") or "")
        target_name = str(target.get("standard_name") or "")
        completed_at = iso_now()
        result = {
            "run_id": self.run_root.name,
            "phase": "monitor_multi_query_discovery",
            "task_type": "monitor",
            "target_id": target_id,
            "target_name": target_name,
            "keyword": target_name,
            "collection_method": "serial_live_search_multi_query",
            "started_at": started_at,
            "completed_at": completed_at,
            "per_query_candidate_limit": per_query_candidate_limit,
            "detail_limit": detail_limit,
            "raw_card_count": raw_card_count,
            "candidate_hit_count": len(hits),
            "deduplicated_count": len(merged),
            "selected_count": len(merged),
            "selected_for_detail": min(len(merged), detail_limit),
            "search_stop_reason": "all_queries_completed",
            "query_results": query_results,
            "candidate_hits": hits,
            "candidates": merged,
        }
        search_root = self.run_root / "search"
        write_json(search_root / "search_candidates.json", result)
        write_json(search_root / "discovery_summary.json", result)
        return result
