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
            const { monitorTargetPresentation, reviewPresentation, stopReasonPresentation } = await import('./web/js/utils.js');
            console.log(JSON.stringify({
              quick: products.productTargetLabel({ targetId: null, targetName: null }),
              target: products.productTargetLabel({ targetId: 'target-1', targetName: '酸枣仁' }),
              noClue: products.productEffectPresentation({ reviewRequired: false, detectedEffects: [] }).label,
              pending: reviewPresentation('pending').label,
              followUp: reviewPresentation('recommend_follow_up').label,
              noAction: reviewPresentation('no_further_action').label,
              official: monitorTargetPresentation({ dataset_status: 'verified_reference' }).label,
              development: monitorTargetPresentation({ dataset_status: 'development_seed' }).label,
              candidateLimit: stopReasonPresentation('candidate_limit_reached'),
              allQueries: stopReasonPresentation('all_queries_completed'),
              stagnant: stopReasonPresentation('stagnant'),
              unknown: stopReasonPresentation('future_reason'),
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
                "official": "正式",
                "development": "开发",
                "candidateLimit": "达到候选数量上限",
                "allQueries": "所有搜索词执行完成",
                "stagnant": "页面结果连续无新增",
                "unknown": "future_reason",
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
            "productEmptyTitle",
            "productEmptyHint",
            "clearProductFilters",
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

    def test_design_tokens_inline_navigation_and_responsive_rules_are_present(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        base_css = (WEB_ROOT / "css" / "base.css").read_text(encoding="utf-8")
        pages_css = (WEB_ROOT / "css" / "pages.css").read_text(encoding="utf-8")
        self.assertIn("--sidebar-width", base_css)
        self.assertIn("--font-sans", base_css)
        self.assertNotIn("min-width: 1180px", base_css)
        self.assertIn("@media (max-width: 1099px)", base_css)
        self.assertIn("@media (max-width: 1199px)", pages_css)
        self.assertGreaterEqual(html.count('<svg viewBox="0 0 24 24">'), 6)

    def test_unfinished_pages_use_explicit_planning_states_without_fake_charts(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("基础词库管理尚未开放", html)
        self.assertIn("统计分析将在后续版本完善", html)
        self.assertNotIn("skeleton-grid", html)
        self.assertNotIn("placeholder-grid", html)

    def test_task_page_separates_current_task_creation_and_history(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        tasks_source = (WEB_ROOT / "js" / "pages" / "tasks.js").read_text(
            encoding="utf-8"
        )
        for identifier in ("currentTaskSummary", "newTaskForm", "taskRecordBody"):
            self.assertIn(f'id="{identifier}"', html)
        self.assertIn("renderCurrentTaskSummary", tasks_source)
        self.assertIn("· ${kind.label}", tasks_source)

    def test_v07_c2_semantic_cleanup_is_explicit(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        base_css = (WEB_ROOT / "css" / "base.css").read_text(encoding="utf-8")
        overview_source = (WEB_ROOT / "js" / "pages" / "overview.js").read_text(
            encoding="utf-8"
        )
        tasks_source = (WEB_ROOT / "js" / "pages" / "tasks.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("候选未深采", overview_source)
        self.assertIn("本批候选中未进入详情采集链", overview_source)
        self.assertIn("selected - stats.detailCollectedProducts", overview_source)
        self.assertNotIn("等待OCR与规则处理", overview_source)
        self.assertIn("<th>详情采集</th>", html)
        self.assertIn("detailCollectedProducts", tasks_source)
        self.assertNotIn("progress-track", tasks_source)
        self.assertIn("stopReasonPresentation(item.stop_reason)", tasks_source)
        self.assertIn(".nav-section-secondary { display: none; }", base_css)
        for label in ("导出当前任务", "当前任务JSON", "当前任务报告"):
            self.assertIn(label, html)

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
            "getInspectionContextOptions",
            "updateInspectionContext",
        ):
            self.assertIn(f"export function {function_name}", source)

    @unittest.skipUnless(NODE, "Node.js不可用")
    def test_inspection_status_labels_and_ugc_boundary_are_explicit(self):
        result = run_node(
            """
            const judgment = await import('./web/js/pages/judgment.js');
            const statuses = [
              'suggest_testing', 'needs_context_review',
              'auxiliary_evidence_only', 'knowledge_integrity_gap',
              'no_applicable_verified_method',
            ];
            const applicability = [
              'applicable', 'conditional', 'not_applicable', 'insufficient_context',
            ];
            const followUps = Object.fromEntries(statuses.map(value => [value, judgment.followUpPresentation(value).label]));
            const applicabilityLabels = Object.fromEntries(applicability.map(value => [value, judgment.applicabilityPresentation(value).label]));
            const followUp = { suggested_methods: [{ method_no: 'BJS 201701' }] };
            console.log(JSON.stringify({
              followUps,
              applicabilityLabels,
              sellerCount: judgment.visibleSuggestedMethods({ evidence_qualification: 'seller_managed_primary' }, followUp).length,
              ugcCount: judgment.visibleSuggestedMethods({ evidence_qualification: 'user_generated_auxiliary_only' }, followUp).length,
            }));
            """
        )
        self.assertEqual(result["followUps"]["suggest_testing"], "建议重点关注/检测")
        self.assertEqual(result["followUps"]["needs_context_review"], "需补充商品信息")
        self.assertEqual(result["followUps"]["knowledge_integrity_gap"], "知识完整性待核对")
        self.assertEqual(result["applicabilityLabels"]["applicable"], "Reference范围匹配")
        self.assertEqual(result["applicabilityLabels"]["insufficient_context"], "信息不足")
        self.assertEqual(result["sellerCount"], 1)
        self.assertEqual(result["ugcCount"], 0)

    def test_judgment_contains_context_update_gaps_and_old_run_fallback(self):
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        judgment = (WEB_ROOT / "js" / "pages" / "judgment.js").read_text(
            encoding="utf-8"
        )
        api = (WEB_ROOT / "js" / "api.js").read_text(encoding="utf-8")
        for identifier in (
            "inspectionStateBadge",
            "inspectionContent",
        ):
            self.assertIn(f'id="{identifier}"', html)
        for text in (
            "抽检辅助建议",
            "该历史任务尚未生成抽检辅助建议",
            "需补充商品信息",
            "知识链组合缺口",
            "Group（partial）",
            "保存并重新评估",
        ):
            self.assertIn(text, html + judgment)
        self.assertIn("inspection-context-options", api)
        self.assertIn("inspection-context`,", api)


if __name__ == "__main__":
    unittest.main()
