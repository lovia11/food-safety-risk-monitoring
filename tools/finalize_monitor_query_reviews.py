"""Finalize human-reviewed SearchQuery artifacts without touching raw collection facts."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.monitor_query_validation import finalize_review_queue
from src.runtime import iso_now, read_json, write_json
from src.search_query_validation import render_review_queue_markdown


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _collection_identity(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": card.get("rank"),
        "productId": card.get("productId"),
        "title": card.get("title"),
        "shop": card.get("shop"),
        "price": card.get("price"),
        "cardMetadata": card.get("cardMetadata"),
        "duplicateOccurrences": card.get("duplicateOccurrences") or [],
        "rawArtifactRefs": card.get("rawArtifactRefs") or [],
    }


def validate_review_source(
    query_artifact: dict[str, Any], review_queue: dict[str, Any]
) -> None:
    if query_artifact.get("executionStatus") != "completed":
        raise ValueError(f"Query尚未完成采集：{query_artifact.get('queryId')}")
    for field in ("batchId", "targetId", "queryId", "queryText"):
        if query_artifact.get(field) != review_queue.get(field):
            raise ValueError(f"Review artifact与Query collection的{field}不一致")
    query_cards = query_artifact.get("resultCards")
    review_results = review_queue.get("results")
    if not isinstance(query_cards, list) or not isinstance(review_results, list):
        raise ValueError("Query/Review artifact缺少结果数组")
    if [_collection_identity(item) for item in query_cards] != [
        _collection_identity(item) for item in review_results
    ]:
        raise ValueError(
            f"Review artifact与immutable Query collection卡片不一致：{query_artifact.get('queryId')}"
        )


def ledger_record_from_review(
    reviewed: dict[str, Any],
    *,
    manifest_sha256: str,
) -> dict[str, Any]:
    metrics = reviewed["metrics"]
    reviewed_at = reviewed["reviewedAt"]
    query_id = reviewed["queryId"]
    batch_id = reviewed["batchId"]
    return {
        "query_id": query_id,
        "target_id": reviewed["targetId"],
        "query_text": reviewed["queryText"],
        "batch_id": batch_id,
        "validation_date": reviewed_at[:10],
        "reviewed_at": reviewed_at,
        "sample_size": metrics["sampleSize"],
        "assessable_count": metrics["assessableCount"],
        "relevant_count": metrics["relevantCount"],
        "raw_medicinal_or_nonfood_scope_count": metrics[
            "rawMedicinalOrNonfoodScopeCount"
        ],
        "non_food_count": metrics["nonFoodCount"],
        "ambiguous_count": metrics["ambiguousSkipped"],
        "ambiguous_skipped": metrics["ambiguousSkipped"],
        "duplicate_skipped": metrics["duplicateSkipped"],
        "relevance_rate": metrics["relevanceRate"],
        "decision": reviewed["decision"],
        "decision_note": reviewed["decisionNote"],
        "validation_note": reviewed["decisionNote"],
        "systematic_scope_issue": reviewed["systematicScopeIssue"],
        "observed_product_forms": reviewed.get("observedProductForms") or [],
        "protocol_version": "V2-4",
        "artifact_ref": f"output/query_validation/{batch_id}/manifest.json",
        "review_artifact_ref": f"output/query_validation/{batch_id}/review/{query_id}.json",
        "artifact_manifest_sha256": manifest_sha256,
    }


def finalize_batch(
    *,
    batch_root: Path,
    review_input: dict[str, Any],
    reviewed_at: str | None = None,
) -> dict[str, Any]:
    manifest_path = batch_root / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("status") != "complete" or manifest.get("searchOnly") is not True:
        raise ValueError("Batch必须是complete且searchOnly=true")
    manifest_entries = {
        str(item.get("queryId") or ""): item for item in manifest.get("queries") or []
    }
    reviews = review_input.get("reviews")
    if not isinstance(reviews, list):
        raise ValueError("人工复核输入必须包含reviews数组")
    input_ids = {str(item.get("queryId") or "") for item in reviews}
    if input_ids != set(manifest_entries):
        missing = sorted(set(manifest_entries) - input_ids)
        extra = sorted(input_ids - set(manifest_entries))
        raise ValueError(f"人工复核Query集合与Batch不一致：missing={missing}, extra={extra}")
    timestamp = reviewed_at or iso_now()
    reviewer = str(review_input.get("reviewedBy") or "human_review")
    manifest_sha256 = sha256_file(manifest_path)
    finalized_by_query: dict[str, dict[str, Any]] = {}
    for decision_input in reviews:
        query_id = str(decision_input["queryId"])
        entry = manifest_entries[query_id]
        query_artifact = read_json(batch_root / str(entry["artifact"]))
        review_path = batch_root / "review" / f"{query_id}.json"
        review_queue = read_json(review_path)
        validate_review_source(query_artifact, review_queue)
        reviewed = finalize_review_queue(
            review_queue,
            assignments=decision_input.get("assignments") or [],
            decision=decision_input.get("decision"),
            decision_note=decision_input.get("decisionNote"),
            systematic_scope_issue=bool(
                decision_input.get("systematicScopeIssue", False)
            ),
            observed_product_forms=decision_input.get("observedProductForms") or [],
            reviewed_at=timestamp,
            reviewed_by=reviewer,
        )
        finalized_by_query[query_id] = reviewed

    for query_id, reviewed in finalized_by_query.items():
        review_path = batch_root / "review" / f"{query_id}.json"
        write_json(review_path, reviewed)
        markdown_path = batch_root / "review" / f"{query_id}.md"
        markdown_path.write_text(
            render_review_queue_markdown(reviewed), encoding="utf-8"
        )

    ledger_records = [
        ledger_record_from_review(
            finalized_by_query[query_id],
            manifest_sha256=manifest_sha256,
        )
        for query_id in manifest_entries
    ]
    summary = {
        "batchId": manifest["batchId"],
        "protocolVersion": "V2-4",
        "searchOnly": True,
        "collectionStartedAt": manifest.get("startedAt"),
        "collectionCompletedAt": manifest.get("completedAt"),
        "reviewedAt": timestamp,
        "reviewedBy": reviewer,
        "manifestSha256": manifest_sha256,
        "records": ledger_records,
    }
    write_json(batch_root / "review" / "finalization_summary.json", summary)
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="离线完成SearchQuery人工复核、指标计算与review artifact固化"
    )
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = finalize_batch(
            batch_root=args.batch_root.resolve(),
            review_input=read_json(args.input),
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"人工复核固化失败：{exc}", file=sys.stderr)
        return 2
    print(
        f"人工复核已固化：batch={summary['batchId']}, "
        f"reviewedAt={summary['reviewedAt']}, records={len(summary['records'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
