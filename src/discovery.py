"""Deterministic multi-query candidate discovery built on the frozen collector."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Callable, Iterable

from src.runtime import iso_now, read_json, write_json
from src.monitor_coverage import is_operational_query
from src.taobao_live import LiveSearchCollector


DEFAULT_CLUE_CONFIG = Path("config/effect_keywords.json")


def _safe_segment(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_")
    return normalized[:48] or "query"


def _load_clue_keywords(path: Path = DEFAULT_CLUE_CONFIG) -> tuple[str, ...]:
    """Load the existing page-promotion clue words for search-card triage.

    These words only influence which candidates receive expensive detail
    collection.  They do not create Claims, risk findings or legal conclusions.
    """

    try:
        payload = read_json(path)
    except (OSError, ValueError, TypeError, FileNotFoundError):
        return ()
    categories = payload.get("effect_categories") if isinstance(payload, dict) else None
    if not isinstance(categories, dict):
        return ()
    result: list[str] = []
    seen: set[str] = set()
    for values in categories.values():
        if not isinstance(values, list):
            continue
        for value in values:
            keyword = str(value or "").strip()
            if keyword and keyword not in seen:
                seen.add(keyword)
                result.append(keyword)
    return tuple(result)


def _title_clues(candidate: dict[str, Any], keywords: Iterable[str]) -> list[str]:
    title = str(candidate.get("product_name") or "")
    return [keyword for keyword in keywords if keyword and keyword in title]


def _stable_exploration_key(target_id: str, candidate: dict[str, Any]) -> str:
    product_id = str(candidate.get("product_id") or "")
    return hashlib.sha256(f"{target_id}\0{product_id}".encode("utf-8")).hexdigest()


def select_detail_candidates(
    candidates: list[dict[str, Any]],
    *,
    detail_limit: int,
    target_id: str,
    clue_keywords: Iterable[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Choose detail candidates from exposure, visible clues and exploration.

    Search result order is retained in each candidate's ``rank``.  The returned
    list is reordered only so the existing detail collector processes the
    selected candidates first.  Selection never means the product is risky; it
    only explains why limited detail-collection capacity was allocated to it.
    """

    if detail_limit < 1:
        raise ValueError("detail_limit必须大于0")
    total = min(len(candidates), detail_limit)
    prepared: list[dict[str, Any]] = []
    keywords = tuple(clue_keywords)
    for original_order, source in enumerate(candidates, start=1):
        item = dict(source)
        item["discovery_order"] = original_order
        item["title_clue_terms"] = _title_clues(item, keywords)
        item["selected_for_detail"] = False
        item["selection_group"] = None
        item["selection_reasons"] = []
        item["selection_order"] = None
        prepared.append(item)

    if total == 0:
        return prepared, {
            "name": "balanced_exposure_clue_exploration_v1",
            "detail_limit": detail_limit,
            "selected_count": 0,
            "exposure_target": 0,
            "clue_target": 0,
            "exploration_target": 0,
        }

    exploration_target = 1 if total >= 3 else 0
    if total >= 10:
        exploration_target = max(1, total // 5)
    remaining_budget = total - exploration_target
    clue_target = remaining_budget // 2
    exposure_target = remaining_budget - clue_target

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()

    def add(item: dict[str, Any], group: str, reason: str) -> bool:
        product_id = str(item.get("product_id") or "")
        if not product_id or product_id in selected_ids or len(selected) >= total:
            return False
        selected_ids.add(product_id)
        item["selected_for_detail"] = True
        item["selection_group"] = group
        item["selection_reasons"].append(reason)
        selected.append(item)
        return True

    for item in prepared[:exposure_target]:
        add(item, "exposure", "搜索结果靠前")

    clue_added = 0
    for item in prepared:
        if clue_added >= clue_target:
            break
        terms = item["title_clue_terms"]
        if not terms:
            continue
        if add(
            item,
            "visible_clue",
            f"搜索卡片出现宣传线索：{'、'.join(terms[:3])}",
        ):
            clue_added += 1

    exploration_pool = [
        item
        for item in prepared
        if str(item.get("product_id") or "") not in selected_ids
        and not item["title_clue_terms"]
    ]
    exploration_pool.sort(key=lambda item: _stable_exploration_key(target_id, item))
    exploration_added = 0
    for item in exploration_pool:
        if exploration_added >= exploration_target:
            break
        if add(item, "exploration", "探索样本"):
            exploration_added += 1

    for item in prepared:
        if len(selected) >= total:
            break
        add(item, "fill", "补足详情样本")

    for order, item in enumerate(selected, start=1):
        item["selection_order"] = order
        terms = item["title_clue_terms"]
        if terms and not any("宣传线索" in reason for reason in item["selection_reasons"]):
            item["selection_reasons"].append(
                f"搜索卡片同时出现宣传线索：{'、'.join(terms[:3])}"
            )

    unselected = [
        item
        for item in prepared
        if str(item.get("product_id") or "") not in selected_ids
    ]
    ordered = selected + unselected
    strategy = {
        "name": "balanced_exposure_clue_exploration_v1",
        "detail_limit": detail_limit,
        "selected_count": len(selected),
        "exposure_target": exposure_target,
        "clue_target": clue_target,
        "exploration_target": exploration_target,
        "selected_product_ids": [str(item["product_id"]) for item in selected],
        "selected_groups": {
            "exposure": sum(item["selection_group"] == "exposure" for item in selected),
            "visible_clue": sum(item["selection_group"] == "visible_clue" for item in selected),
            "exploration": sum(item["selection_group"] == "exploration" for item in selected),
            "fill": sum(item["selection_group"] == "fill" for item in selected),
        },
    }
    return ordered, strategy


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
        clue_keywords: Iterable[str] | None = None,
    ) -> None:
        self.context = context
        self.run_root = run_root.resolve()
        self.logger = logger
        self.non_interactive = non_interactive
        self.collector_factory = collector_factory
        self.manual_action_adapter = manual_action_adapter
        self.clue_keywords = (
            tuple(clue_keywords) if clue_keywords is not None else _load_clue_keywords()
        )

    def discover(
        self,
        *,
        target: dict[str, Any],
        queries: list[dict[str, Any]],
        per_query_candidate_limit: int,
        detail_limit: int,
    ) -> dict[str, Any]:
        enabled = [item for item in queries if is_operational_query(item)]
        enabled.sort(key=lambda item: (int(item.get("order") or 0), str(item.get("query_id") or "")))
        if not enabled:
            raise ValueError("监测对象没有已验证并启用的SearchQuery")
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
        ordered_candidates, selection_strategy = select_detail_candidates(
            merged,
            detail_limit=detail_limit,
            target_id=target_id,
            clue_keywords=self.clue_keywords,
        )
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
            "selected_for_detail": selection_strategy["selected_count"],
            "selection_strategy": selection_strategy,
            "search_stop_reason": "all_queries_completed",
            "query_results": query_results,
            "candidate_hits": hits,
            "candidates": ordered_candidates,
        }
        search_root = self.run_root / "search"
        write_json(search_root / "search_candidates.json", result)
        write_json(search_root / "discovery_summary.json", result)
        return result
