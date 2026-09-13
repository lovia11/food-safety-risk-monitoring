"""V2-4 governed search-only query validation entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_store import validate_monitor_config
from src.monitor_query_validation import select_validation_queries, validation_dry_run
from src.runtime import read_json


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor SearchQuery治理验证（仅搜索）")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--target", action="append", dest="target_ids")
    parser.add_argument("--query", action="append", dest="query_ids")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--output", type=Path, default=Path("output/query_validation"))
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/monitor_targets.reference.json"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = validate_monitor_config(read_json(args.config))
        selected = select_validation_queries(
            config,
            target_ids=set(args.target_ids) if args.target_ids else None,
            query_ids=set(args.query_ids) if args.query_ids else None,
        )
        plan = validation_dry_run(
            batch_id=args.batch,
            output_root=args.output,
            max_results=args.max_results,
            selected=selected,
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"SearchQuery验证计划错误：{exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    batch_root = args.output / args.batch
    if batch_root.exists() and not args.resume:
        print(
            f"验证批次已存在：{batch_root}；确认继续时使用--resume。",
            file=sys.stderr,
        )
        return 2

    # Live execution remains delegated to the existing visible-browser,
    # search-only collector. It never enters Detail/OCR/Phase3.
    from src.search_query_validation import main as run_live_validation

    live_args = [
        "--config",
        str(args.config),
        "--candidate-limit",
        str(args.max_results),
        "--output-root",
        str(args.output),
        "--run-id",
        args.batch,
    ]
    for target_id in sorted({target["target_id"] for target, _ in selected}):
        live_args.extend(["--target-id", target_id])
    for _, query in selected:
        live_args.extend(["--query-id", query["query_id"]])
    if args.resume:
        live_args.append("--resume")
    return run_live_validation(live_args)


if __name__ == "__main__":
    raise SystemExit(main())
