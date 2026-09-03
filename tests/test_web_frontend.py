import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = PROJECT_ROOT / "web"
NODE = shutil.which("node")


def run_node(source: str):
    completed = subprocess.run(
        [
            NODE,
            "--experimental-default-type=module",
            "--input-type=module",
            "-e",
            source,
        ],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


class WebFrontendStructureTest(unittest.TestCase):
    def test_index_references_existing_module_and_css_assets(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        script_match = re.search(
            r'<script\s+type="module"\s+src="([^"]+)"', html
        )
        self.assertIsNotNone(script_match)
        self.assertTrue((WEB_ROOT / script_match.group(1)).is_file())
        stylesheets = re.findall(r'<link\s+rel="stylesheet"\s+href="([^"]+)"', html)
        self.assertEqual(
            stylesheets,
            ["css/base.css", "css/components.css", "css/pages.css"],
        )
        self.assertTrue(all((WEB_ROOT / path).is_file() for path in stylesheets))

    @unittest.skipUnless(NODE, "Node.js不可用")
    def test_all_javascript_modules_pass_node_syntax_check(self):
        javascript_files = sorted(WEB_ROOT.glob("**/*.js"))
        self.assertGreaterEqual(len(javascript_files), 8)
        for path in javascript_files:
            with self.subTest(path=path.relative_to(WEB_ROOT)):
                subprocess.run(
                    [NODE, "--check", str(path)],
                    cwd=PROJECT_ROOT,
                    check=True,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )

    @unittest.skipUnless(NODE, "Node.js不可用")
    def test_product_api_query_contains_server_side_filters_and_pagination(self):
        result = run_node(
            """
            const { buildProductQuery } = await import('./web/js/api.js');
            const query = buildProductQuery({
              filters: {
                targetId: 'target-1',
                query: '酸枣仁',
                reviewStatus: 'recommend_follow_up',
                effect: '助眠',
              },
              page: 2,
              pageSize: 50,
            });
            console.log(JSON.stringify(Object.fromEntries(new URLSearchParams(query))));
            """
        )
        self.assertEqual(
            result,
            {
                "target_id": "target-1",
                "query": "酸枣仁",
                "review_status": "recommend_follow_up",
                "effect": "助眠",
                "page": "2",
                "page_size": "50",
            },
        )

    @unittest.skipUnless(NODE, "Node.js不可用")
    def test_product_filters_reset_page_and_api_result_updates_state(self):
        result = run_node(
            """
            const { defaultProductQueryState } = await import('./web/js/state.js');
            const { applyProductPage, updateProductFilters } = await import('./web/js/pages/products.js');
            const state = defaultProductQueryState();
            state.page = 4;
            updateProductFilters({ targetId: 'target-1' }, state);
            const resetPage = state.page;
            applyProductPage({ products: [], page: 1, pageSize: 20, total: 0, totalPages: 0 }, state);
            console.log(JSON.stringify({ resetPage, state }));
            """
        )
        self.assertEqual(result["resetPage"], 1)
        self.assertEqual(result["state"]["items"], [])
        self.assertEqual(result["state"]["total"], 0)
        self.assertTrue(result["state"]["loaded"])

    @unittest.skipUnless(NODE, "Node.js不可用")
    def test_product_target_effect_and_review_labels_are_explicit(self):
        result = run_node(
            """
            const products = await import('./web/js/pages/products.js');
            const { reviewPresentation } = await import('./web/js/utils.js');
            console.log(JSON.stringify({
              quick: products.productTargetLabel({ targetId: null, targetName: null }),
              target: products.productTargetLabel({ targetId: 'target-1', targetName: '酸枣仁' }),
              noClue: products.productEffectPresentation({ reviewRequired: false, detectedEffects: [] }).label,
              pending: reviewPresentation('pending').label,
              followUp: reviewPresentation('recommend_follow_up').label,
              noAction: reviewPresentation('no_further_action').label,
            }));
            """
        )
        self.assertEqual(
            result,
            {
                "quick": "快速任务",
                "target": "酸枣仁",
                "noClue": "未发现明显线索",
                "pending": "待复核",
                "followUp": "建议进一步关注",
                "noAction": "暂不进一步关注",
            },
        )

    @unittest.skipUnless(NODE, "Node.js不可用")
    def test_task_payload_builder_preserves_quick_and_monitor_requests(self):
        result = run_node(
            """
            const { buildTaskPayload } = await import('./web/js/pages/tasks.js');
            console.log(JSON.stringify({
              quick: buildTaskPayload({ taskType: 'quick', keyword: ' 酸枣仁 ', candidateLimit: '10', detailLimit: '2' }),
              monitor: buildTaskPayload({ taskType: 'monitor', targetId: 'target-1', perQueryCandidateLimit: '20', detailLimit: '3' }),
            }));
            """
        )
        self.assertEqual(
            result["quick"],
            {
                "task_type": "quick",
                "keyword": "酸枣仁",
                "candidate_limit": 10,
                "detail_limit": 2,
            },
        )
        self.assertEqual(
            result["monitor"],
            {
                "task_type": "monitor",
                "target_id": "target-1",
                "per_query_candidate_limit": 20,
                "detail_limit": 3,
            },
        )

    def test_product_workspace_contains_required_states_columns_and_controls(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        for identifier in (
            "productTargetFilter",
            "productSearch",
            "productReviewFilter",
            "productEffectFilter",
            "productPageSize",
            "runProductQuery",
            "resetFilters",
            "productWorkspaceStatus",
            "productEmpty",
            "productPreviousPage",
            "productNextPage",
        ):
            self.assertIn(f'id="{identifier}"', html)
        for heading in (
            "商品名称",
            "监测对象",
            "店铺",
            "搜索页地区",
            "功效线索",
            "人工复核状态",
            "采集时间",
        ):
            self.assertIn(f"<th>{heading}</th>", html)

    def test_product_workspace_no_longer_merges_current_and_history_runs(self):
        app_source = (WEB_ROOT / "app.js").read_text(encoding="utf-8")
        product_source = (WEB_ROOT / "js" / "pages" / "products.js").read_text(
            encoding="utf-8"
        )
        combined = app_source + product_source
        self.assertNotIn("monitorProductEntries", combined)
        self.assertNotIn("filteredProducts", combined)
        self.assertIn("getProducts", product_source)
        self.assertIn("loadProductsPage", app_source)

    def test_api_module_centralizes_snapshot_review_task_and_product_calls(self):
        source = (WEB_ROOT / "js" / "api.js").read_text(encoding="utf-8")
        for function_name in (
            "getProducts",
            "getMonitorTargets",
            "getProductSnapshots",
            "getSnapshot",
            "updateReview",
            "getTasks",
            "createTask",
            "resumeTaskRequest",
            "getRun",
        ):
            self.assertIn(f"export function {function_name}", source)


if __name__ == "__main__":
    unittest.main()
