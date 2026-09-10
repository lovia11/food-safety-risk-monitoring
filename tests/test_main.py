import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.inspection_runtime import INSPECTION_RECOMMENDATION_ERROR_FILE
from src.main import PipelineOptions, ProductStatus, StandalonePipeline, initial_state
from src.phase1_experiment import PhaseOneCollector
from src.runtime import read_json, write_json


class StandalonePipelineResumeTest(unittest.TestCase):
    def test_successful_analysis_without_recommendation_is_backfilled_on_resume(self):
        class Runtime:
            def generate(self, product_root):
                payload = {"product_context": {"product_category": None}}
                write_json(product_root / "inspection_recommendation.json", payload)
                return payload

        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            product_root = output_root / "run" / "products" / "123"
            write_json(product_root / "analysis.json", {"product_id": "123"})
            pipeline = StandalonePipeline(
                PipelineOptions(keyword="测试", output_root=output_root, run_id="run")
            )
            pipeline.set_inspection_runtime(Runtime())
            pipeline.prepared_roots = {"123": product_root}
            pipeline.state_by_id = {
                "123": {
                    "product_id": "123",
                    "rank": 1,
                    "status": ProductStatus.SUCCESS,
                    "errors": [],
                }
            }
            pipeline.search_payload = {"keyword": "测试", "candidates": []}

            with patch("src.main.create_ocr_runtime") as create_runtime:
                pipeline._process_products()

            create_runtime.assert_not_called()
            self.assertEqual(
                pipeline.state_by_id["123"]["status"], ProductStatus.SUCCESS
            )
            self.assertTrue(
                (product_root / "inspection_recommendation.json").is_file()
            )
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_recommendation_failure_preserves_analysis_and_success_status(self):
        class FailingRuntime:
            def generate(self, product_root):
                raise RuntimeError("reference unavailable")

        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            product_root = output_root / "run" / "products" / "123"
            original_analysis = {"product_id": "123", "detected_effects": []}
            write_json(product_root / "analysis.json", original_analysis)
            pipeline = StandalonePipeline(
                PipelineOptions(keyword="测试", output_root=output_root, run_id="run")
            )
            pipeline.set_inspection_runtime(FailingRuntime())
            pipeline.prepared_roots = {"123": product_root}
            pipeline.state_by_id = {
                "123": {
                    "product_id": "123",
                    "rank": 1,
                    "status": ProductStatus.SUCCESS,
                    "errors": [],
                }
            }
            pipeline.search_payload = {"keyword": "测试", "candidates": []}

            pipeline._process_products()

            self.assertEqual(read_json(product_root / "analysis.json"), original_analysis)
            self.assertEqual(
                pipeline.state_by_id["123"]["status"], ProductStatus.SUCCESS
            )
            error = read_json(product_root / INSPECTION_RECOMMENDATION_ERROR_FILE)
            self.assertEqual(error["status"], "error")
            self.assertIn("reference unavailable", error["message"])
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_candidate_and_detail_limits_have_separate_semantics(self):
        options = PipelineOptions(
            keyword="酸枣仁",
            candidate_limit=50,
            detail_limit=10,
        )
        self.assertEqual(options.requested_candidate_limit, 50)
        self.assertEqual(options.requested_detail_limit, 10)
        self.assertEqual(
            PipelineOptions(keyword="酸枣仁", limit=20).requested_candidate_limit,
            20,
        )

    def test_detail_collection_processes_only_first_detail_limit_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            candidates = [
                {
                    "product_id": str(index),
                    "product_url": f"https://item.taobao.com/item.htm?id={index}",
                    "rank": index,
                }
                for index in range(1, 6)
            ]
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="酸枣仁",
                    candidate_limit=5,
                    detail_limit=2,
                    output_root=output_root,
                    run_id="limit_test",
                    product_delay_seconds=0,
                )
            )
            pipeline.search_payload = {"keyword": "酸枣仁", "candidates": candidates}
            pipeline.state_by_id = {
                item["product_id"]: initial_state(item) for item in candidates
            }
            collected_roots = [
                pipeline.products_root / "1",
                pipeline.products_root / "2",
            ]
            with patch("src.main.PhaseOneCollector") as collector:
                collector.return_value.collect_in_context.side_effect = collected_roots
                pipeline._collect_details(object(), candidates)
            self.assertEqual(collector.call_count, 2)
            self.assertEqual(set(pipeline.prepared_roots), {"1", "2"})
            self.assertEqual(
                pipeline.state_by_id["3"]["status"], ProductStatus.PENDING
            )
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_manual_action_adapter_reaches_real_detail_collector_constructor(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            candidate = {
                "product_id": "123",
                "product_url": "https://item.taobao.com/item.htm?id=123",
                "rank": 1,
            }
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="酸枣仁",
                    candidate_limit=1,
                    detail_limit=1,
                    output_root=output_root,
                    run_id="adapter-constructor",
                    product_delay_seconds=0,
                )
            )
            adapter = object()
            pipeline.set_manual_action_adapter(adapter)
            pipeline.state_by_id = {"123": initial_state(candidate)}
            received = []

            def collect(instance, context):
                received.append((instance.manual_action_adapter, context))
                return instance.paths.product_root

            context = object()
            with patch.object(
                PhaseOneCollector,
                "collect_in_context",
                autospec=True,
                side_effect=collect,
            ):
                pipeline._collect_details(context, [candidate])

            self.assertEqual(received, [(adapter, context)])
            self.assertEqual(set(pipeline.prepared_roots), {"123"})
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_global_detail_limit_caps_monitor_processing_and_all_selected_continue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            candidates = [
                {
                    "product_id": str(index),
                    "product_url": f"https://item.taobao.com/item.htm?id={index}",
                    "rank": index,
                }
                for index in range(1, 5)
            ]
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="酸枣仁",
                    candidate_limit=10,
                    detail_limit=2,
                    output_root=output_root,
                    run_id="monitor-global-limit",
                    product_delay_seconds=0,
                    task_type="monitor",
                    target_id="target-1",
                    search_queries=(
                        {"query_id": "q1", "query_text": "酸枣仁"},
                        {"query_id": "q2", "query_text": "酸枣仁茶"},
                    ),
                    per_query_candidate_limit=10,
                )
            )
            pipeline.state_by_id = {
                item["product_id"]: initial_state(item) for item in candidates
            }
            roots = [pipeline.products_root / "1", pipeline.products_root / "2"]
            for root in roots:
                root.mkdir(parents=True, exist_ok=True)

            with patch("src.main.PhaseOneCollector") as collector:
                collector.return_value.collect_in_context.side_effect = roots
                pipeline._collect_details(object(), candidates)
            with patch("src.main.create_ocr_runtime", return_value=object()), patch(
                "src.main.run_ocr"
            ) as run_ocr, patch("src.main.run_analysis") as run_analysis:
                pipeline._process_products()

            self.assertEqual(collector.call_count, 2)
            self.assertEqual(run_ocr.call_count, 2)
            self.assertEqual(run_analysis.call_count, 2)
            self.assertEqual(
                [pipeline.state_by_id[str(index)]["status"] for index in (1, 2)],
                [ProductStatus.SUCCESS, ProductStatus.SUCCESS],
            )
            self.assertEqual(
                pipeline.state_by_id["3"]["status"], ProductStatus.PENDING
            )
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)
    def test_resume_discovers_only_products_with_real_meta(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            run_root = output_root / "resume_run"
            product_root = run_root / "products" / "123"
            product_root.mkdir(parents=True)
            candidate = {
                "product_id": "123",
                "product_url": "https://item.taobao.com/item.htm?id=123",
                "rank": 1,
            }
            write_json(
                run_root / "search" / "search_candidates.json",
                {"keyword": "酸枣仁", "candidates": [candidate]},
            )
            write_json(
                run_root / "batch_state.json",
                [
                    {
                        "product_id": "123",
                        "rank": 1,
                        "status": ProductStatus.DETAIL_COLLECTED,
                        "attempts": 1,
                        "errors": [],
                    }
                ],
            )
            write_json(product_root / "meta.json", {"productId": "123", "imageCount": 1})
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="酸枣仁",
                    output_root=output_root,
                    run_id="resume_run",
                )
            )
            expected = {"run_root": run_root}
            with patch.object(pipeline, "_process_products") as process:
                with patch.object(pipeline, "_write_outputs", return_value=expected):
                    outputs = pipeline.resume_processing()
            self.assertEqual(outputs, expected)
            self.assertEqual(pipeline.prepared_roots, {"123": product_root})
            process.assert_called_once_with()
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_detail_resume_skips_product_with_verified_meta(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            product_root = output_root / "run" / "products" / "123"
            write_json(product_root / "meta.json", {"productId": "123"})
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="酸枣仁",
                    output_root=output_root,
                    run_id="run",
                    detail_limit=1,
                )
            )
            pipeline.state_by_id = {
                "123": {
                    "product_id": "123",
                    "rank": 1,
                    "status": ProductStatus.SUCCESS,
                    "attempts": 1,
                    "errors": [],
                }
            }
            candidate = {
                "product_id": "123",
                "product_url": "https://item.taobao.com/item.htm?id=123",
                "rank": 1,
            }
            with patch("src.main.PhaseOneCollector") as collector:
                pipeline._collect_details(object(), [candidate])
            collector.assert_not_called()
            self.assertEqual(pipeline.prepared_roots, {"123": product_root})
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)

    def test_interruption_leaves_collected_product_resumable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            product_root = output_root / "run" / "products" / "123"
            write_json(product_root / "meta.json", {"productId": "123", "imageCount": 1})
            pipeline = StandalonePipeline(
                PipelineOptions(
                    keyword="酸枣仁",
                    output_root=output_root,
                    run_id="run",
                )
            )
            candidate = {
                "keyword": "酸枣仁",
                "product_id": "123",
                "product_name": "真实商品",
                "product_url": "https://item.taobao.com/item.htm?id=123",
                "rank": 1,
            }
            pipeline.search_payload = {
                "keyword": "酸枣仁",
                "candidates": [candidate],
            }
            pipeline.state_by_id = {
                "123": {
                    "product_id": "123",
                    "rank": 1,
                    "status": ProductStatus.PROCESSING,
                    "attempts": 1,
                    "errors": [],
                }
            }
            pipeline.mark_interrupted()
            state = read_json(pipeline.state_path)[0]
            snapshot = read_json(pipeline.run_root / "web_snapshot.json")
            self.assertEqual(state["status"], ProductStatus.DETAIL_COLLECTED)
            self.assertEqual(snapshot["task"]["stage"], "interrupted")
            self.assertTrue(snapshot["task"]["terminal"])
            for handler in list(pipeline.logger.handlers):
                handler.close()
                pipeline.logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
