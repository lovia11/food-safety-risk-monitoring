# Pipeline Integration & Environment Audit

> [!WARNING]
> **HISTORICAL INTEGRATION AUDIT / RESOLVED IN PART / NON-NORMATIVE**<br>
> 本文记录当时发现的集成问题，其中 OCR 锁定、readiness、Review eligibility 和 Task Flow 等 P0 项已由后续代码处理。当前 contract 以 code/tests 和后续 V2 canonical docs 为准。

审计日期：2026-09-11
审计分支：`ux-redesign-v1`
审计基线：`4e00ee7822b3d6e16890a73e39a768f006130597`

## 1. 审计范围与结论

本轮只审计真实主链的环境、文件契约、阶段准入和 UI 状态投影。未访问淘宝，未修改 Python、React、schema、Reference、Risk、Sampling Export 或任何业务实现。

结论如下：

1. 当前 OCR 失败是独立虚拟环境中的包版本漂移，不是 `PP-OCRv6` 参数写错。历史成功环境使用 `paddleocr==3.7.0`，明确支持 `PP-OCRv6`；UX worktree 使用 `paddleocr==3.5.0`，其安装包只接受 `PP-OCRv3`、`PP-OCRv4`、`PP-OCRv5`。
2. 两个环境均使用 Python 3.10.0 和 `paddlepaddle==3.2.0`。当前代码、历史 D6 基线和 `requirements-ocr.txt` 都仍请求 `PP-OCRv6`，所以失败不是 Python 解释器版本或模型参数变化造成的。
3. `requirements-ocr.txt` 中的 `paddleocr>=3.0,<4` 不能复现真实成功环境；它同时允许本次失败的 3.5.0 和历史成功的 3.7.0。
4. 当前 Detail、OCR 和 Phase3 之间缺少强制成功门槛：Detail 可以在零张原图时返回成功；OCR 可以在零张图片成功时返回成功；Phase3 会接受零张成功 OCR 的 manifest，继续仅使用标题和 DOM 分析。
5. `DataStore.import_run()` 为 `web_snapshot.json` 中的每个商品无条件创建默认 `pending` Review，包括仅搜索发现、详情失败和 OCR/分析失败的 Snapshot。
6. `taskFlowIndex()` 将所有未显式识别的终态映射到人工复核步骤，`FlowStrip` 再把前三步全部渲染为完成，因此 `completed_with_errors` 会伪装成“搜索、详情、线索均成功”。
7. 当前 Phase3、D2-D5 和 D6 核心文件相对 D6 基线没有 Git blob 变化。旧成功 fixture 运行当前 Phase3 后业务语义一致，运行当前 Recommendation 后结果与历史文件完全一致。因此：**风险分析核心未发生 UX 重构回归**。

## 2. OCR 环境溯源

### 2.1 已确认的真实成功基线

采用以下真实商品作为稳定基线：

- Run：`D:/毕业设计/output/20260905T164428_task`
- Product：`982036041270`
- OCR 运行信息：`products/982036041270/ocr/run_info.json`
- OCR manifest：`products/982036041270/ocr/manifest.json`
- Phase3：`products/982036041270/analysis.json`
- Recommendation：`products/982036041270/inspection_recommendation.json`

真实 `run_info.json` 记录：

| 字段 | 历史成功值 |
| --- | --- |
| Python | 产物未记录；当前保留的原稳定 `.venv` 为 Python 3.10.0 |
| paddlepaddleVersion | 3.2.0（文件字段名为 `paddleVersion`） |
| paddleocrVersion | 3.7.0 |
| ocrVersion | PP-OCRv6 |
| modelSource | bos |
| device | cpu |
| scoreThreshold | 0.5 |

该 manifest 共 13 项，13 项全部为 `success`，每项均指向实际存在的 `ocr/original_###.txt` 和 `ocr/original_###.json`；`ocr/combined_text.txt` 存在且非空。该商品随后成功生成 `analysis.json` 和 `inspection_recommendation.json`。

### 2.2 原稳定目录与 UX worktree 环境对比

所有包信息均使用对应解释器执行 `python -m pip show`，没有混用裸 `pip`。

| 项目 | 原稳定目录 `D:/毕业设计` | 当前 UX worktree `D:/毕业设计-ux` |
| --- | --- | --- |
| `sys.executable` | `D:/毕业设计/.venv/Scripts/python.exe` | `D:/毕业设计-ux/.venv/Scripts/python.exe` |
| Python | 3.10.0 | 3.10.0 |
| PaddlePaddle | 3.2.0 | 3.2.0 |
| PaddleOCR | **3.7.0** | **3.5.0** |
| PaddleX | 3.7.2 | 3.5.2 |
| Pillow（当前环境观察值，历史产物未记录） | 12.1.0 | 12.3.0 |
| NumPy | 2.2.6 | 2.2.6 |
| opencv-contrib-python | 4.10.0.84 | 4.10.0.84 |
| 安装包声明的 OCR 版本 | v3、v4、v5、**v6** | v3、v4、v5 |

系统级 `C:/Program Files/Python310/python.exe` 同为 Python 3.10.0，但没有安装 PaddleOCR 或 PaddlePaddle。它不是完成真实 OCR E2E 时使用的 Web 解释器；本次有效 Web E2E 使用的是 UX worktree 的 `.venv/Scripts/python.exe`。

### 2.3 模型参数、模型源与缓存

- `src/phase2_ocr.py` 自 Collector Baseline `3c77b79` 起一直默认 `ocr_version="PP-OCRv6"`、`model_source="bos"`、`device="cpu"`。
- 当前 Web Task 没有覆盖这些值，`run_config.json` 中的 cache 为 `C:/Users/LEGION/.cache/paddlex`。
- 当前 shell 没有预设 `PADDLE_*` 环境变量；代码会设置相同的 BOS 模型源和缓存目录。
- 共享缓存中存在 `PP-OCRv6_medium_det` 和 `PP-OCRv6_medium_rec`。
- 当前异常发生在 `PaddleOCR(...)` 对 `ocr_version` 的构造参数校验阶段，发生在模型加载/下载之前。因此缓存内容、BOS 源和网络均不是本次第一原因。

### 2.4 根因判定

第一原因是 **PaddleOCR/PaddleX 包版本漂移**：

- 3.7.0 的 `_SUPPORTED_OCR_VERSIONS` 包含 `PP-OCRv6`；
- 3.5.0 的 `_SUPPORTED_OCR_VERSIONS` 不包含 `PP-OCRv6`；
- 代码和模型参数未变；
- Python 与 PaddlePaddle 主版本未变；
- 当前失败在缓存使用前发生。

无法仅从现有文件证明 UX `.venv` 当初为何停留在 3.5.0；可以确认的是宽范围依赖允许两个 worktree 的独立虚拟环境产生不同结果。

## 3. Pipeline Artifact Contract Matrix

下表先记录**当前代码的真实契约**，并在“UI 应显示状态”中给出应执行的产品语义。凡标为“当前缺口”的内容均尚未在本轮修改。

| 阶段 | 输入前置条件 | 成功产物 | 失败产物 | 当前下一阶段准入条件 | UI 应显示状态 |
| --- | --- | --- | --- | --- | --- |
| Search Discovery | Quick：非空 keyword、正整数 candidate/detail limit、有效浏览器上下文。Monitor：有效 MonitorTarget、至少一个启用且 `search_validated` 的 Query、正整数 per-query/detail limit。 | Quick 必须返回非空 candidates，并写 `search/search_candidates.json`、`search/search_diagnostics.json`、`search/search_candidates.csv`、`search/search_results.png`、`search/search_page.html`、`search/scroll_states.json`。Monitor 还写聚合后的 `search/discovery_summary.json`，并保留逐 Query 诊断。 | `search/search_diagnostics.json` 写入 `error_type`、`error_message` 和 stop reason；尽力写 `search_error.png/html`。异常逃逸 worker 时写 `task_runtime_error.json`，Task stage=`failed`。 | Pipeline 直接使用 Collector 返回的非空 `candidates`；Monitor 先跨 Query 合并、按 product ID 去重，再由全局 `detail_limit` 选取详情对象。 | 搜索执行中=`active`；获得候选=`completed`；终态且没有成功候选=`failed`。候选本身只能显示“仅搜索发现，尚未分析”，不得显示“待复核”。 |
| Detail Collection | 位于全局 `detail_limit` 内的 Candidate，必须有 product ID、product URL 和可用 Playwright context。 | `meta.json` 在成功路径最后写入，是当前最强完成标记；同一路径此前写 `dom_text.txt`、`manifests/dom_before_scroll.json`、`detail_click.json`、`dom_after_scroll.json`、`scroll_states.json`、`network_responses.json`、`original_images.json`，并写 HTML/页面截图。`meta.crawlStatus=detail_collected`。 | 写 `collection_error.json`；尽力写 `page/collection_error.png` 和 `.html`；每次尝试写入 `batch_state.json.errors`，重试耗尽后 status=`failed_collection`。中途文件可能存在但不能当作成功。 | 当前只要求 Collector 正常返回；resume 只检查 `meta.json` 存在。**当前缺口：不要求 `savedOriginalCount>0`，零原图也可标记 Detail 成功。** | 采集中=`active`；存在完整合法 meta 且满足原图门槛=`completed`；部分目标成功=`partial`；全部目标失败=`failed`；未被选入详情的候选保持“仅搜索发现”。 |
| OCR | Product root 下存在 `images/original/`；优先按 `meta.ocrImageNumbers` 或 image flags 选图，否则选择编号 2-16 的支持格式图片；至少要选到一张，否则抛 `FileNotFoundError`。 | 对每张成功图写 `ocr/original_###.txt` 与 `.json`；逐图持续写 `ocr/manifest.json`；循环结束写 `ocr/combined_text.txt`、`ocr/run_info.json`、`phase2_ocr_report.md`。 | Runtime 初始化失败时可能完全没有 OCR 产物，本次 PP-OCRv6 异常即属于此类。逐图识别失败只在 manifest item 中记录 `status=failed/error`；顶层异常由 Pipeline 记录为 `failed_processing`。 | 当前 `run_ocr()` 在 manifest 全部失败时仍正常返回，Phase3 随后运行。**当前成功图片数量要求实际为 0，这是契约缺口。** 正式契约应要求 manifest 至少一项 `success`，且其 txt/json 文件存在，同时 run_info 与 combined_text 已完成。 | OCR 运行中=`active`；满足正式成功门槛=`completed`；存在部分成功且部分失败时按业务容忍规则显示 `partial`；零成功或 runtime 初始化失败=`failed`，文案“线索识别失败”，不得进入 Review。 |
| Phase3 Analysis | 当前代码硬要求可解析的 `meta.json`、`dom_text.txt`、`ocr/manifest.json` 和有效 `effect_keywords.json`。manifest 中 success 项的 `textPath` 若缺失会被静默跳过。`combined_text.txt` 不是实际输入前置条件。 | Web Pipeline 使用 `write_run_outputs=False`，写 `analysis.json`、`analysis_input.txt`、`phase3_analysis_report.md`。`analysis.json` 含输入 hash、input summary、证据来源、detected effects 和 `review_required`。 | 没有独立的 `phase3_analysis_error.json`；异常与 OCR 顶层异常一起映射为 `failed_processing`，可能留下部分文件。 | 当前只要 `run_analysis()` 返回就先把商品 status 置为 `success`，随后才运行 Recommendation。当前 Phase3 允许零张成功 OCR，仅使用标题/DOM 继续分析。正式主链应在 OCR 成功门槛之后准入。 | 生成合法 `analysis.json`=`completed`；运行中=`active`；终态无 analysis=`failed`；不得因 Task 已结束自动显示完成。只有 Analysis-ready Snapshot 才有资格进入待复核。 |
| Inspection Recommendation | 必须有可解析的 `analysis.json`；Reference 数据须成功导入 SQLite；`inspection_context.json` 可缺失，缺失时使用显式 unknown context。 | 写 `inspection_recommendation.json`，并删除旧 `inspection_recommendation_error.json`。 | `InspectionRuntime.record_error()` 写 `inspection_recommendation_error.json` 并删除不可信的 recommendation 文件。 | Recommendation 是 Phase3 后的可降级能力。生成失败不会把已成功的 Phase3 Product 从 `success` 改成失败，也不应取消其人工复核资格。 | 成功显示“抽检辅助建议”；失败显示“抽检辅助建议暂不可用”及可审计错误，同时继续展示 Phase3 页面证据和 Review。不得把 Recommendation 失败伪装成普通可用。 |
| DataStore Import | Run 必须是 output root 的直接子目录，且有可解析的 `web_snapshot.json`；task ID 必须等于目录名。 | Upsert Task、Product、ProductSnapshot；导入 Evidence；导入 Monitor candidate hits。当前对每个 Snapshot 执行 `INSERT OR IGNORE INTO reviews`。 | `import_all_runs()` 捕获文件/JSON/SQLite 异常并把整个 run 计为 skipped；TaskManager 的在线索引失败会记录日志但文件事实仍保留。 | 当前任何被写进 web snapshot 的商品都获得默认 `pending` Review，不检查 status、meta、OCR 或 analysis。 | 所有 Candidate 可进入商品总览，但只有派生 `analysisReady=true` 的 Snapshot 可投影为 `pending` 并进入正常 Review Queue。采集/OCR/分析失败必须保留其真实失败状态。 |
| Human Review | 当前 Review API 只要求 Snapshot 存在、状态值合法、note 不超过 2000 字；没有 Analysis-ready 前置检查。 | Review-only 保存写 SQLite Review。完整决策在同一事务中写 Review，并按结论创建/保留或删除 current Sampling Membership。 | 非法状态/note、Snapshot 不存在等返回错误；事务失败不应产生半完成 Review/Membership。 | 当前任何 Snapshot（包括搜索候选和失败项）都可被复核。正式准入必须统一调用 Analysis-ready predicate；Recommendation 失败不阻断。 | Analysis-ready 且 Review pending=`待人工复核`；未 ready 的 Snapshot 显示采集/识别失败或仅搜索发现，不展示决策按钮。 |
| Sampling List | 正常加入通过 `ReviewDecisionService.decide(recommend_follow_up)`；restore 要求 source Snapshot 的 Review 仍为 `recommend_follow_up`。Membership 绑定 Product、source Snapshot、source Task。 | 当前清单 Membership 写入 SQLite；Review 与 Membership 在应用层决策事务中协调，repository 仍互不偷写。 | 验证冲突返回 4xx/409，事务回滚；低层 restore 不得改变 Review。 | 正式加入必须来源于已准入并完成的 Review；单独移出只删除 Membership。当前缺口来自上游：未 ready Snapshot 仍可调用 Review decision。 | 已纳入、已复核/当前未在清单、暂不纳入按持久 Review 与 current membership 分开显示。未 Analysis-ready 的商品不得进入这些人工决策状态。 |

### 3.1 应固定的跨阶段不变量

1. `meta.json` 是 Detail 完成标记，但还必须验证其身份、`crawlStatus`、原图清单和至少一张 OCR candidate；仅目录或截图存在不算完成。
2. OCR 完成必须有可解析的 `run_info.json`、完整 `manifest.json`、`combined_text.txt`，且 manifest 至少一张 `success`，对应 txt/json 实际存在。
3. Phase3 只在 OCR 正式成功后运行；Analysis 完成以可解析的 `analysis.json` 及其输入 hash 为准。
4. `analysisReady` 不依赖是否命中功效词，也不依赖 Recommendation 是否成功；没有线索的已完成分析商品仍可由人工确认“暂不纳入”。
5. 普通待复核的唯一准入集合应为：`status=success`、meta/analysis 路径有效、OCR success count 至少 1。`pending_detail_collection`、`collecting_detail`、`detail_collected`、`processing_ocr_analysis`、`failed_collection`、`failed_processing` 均不得进入正常 pending Review。

## 4. 搜索 Candidate 与 Review Queue 边界

### 4.1 当前真实问题

问题确定存在，且数据库已能复现：

| Run | Snapshot 状态 | 数量 | 当前 Review |
| --- | --- | ---: | --- |
| `20260911T003529_task` | `failed_collection` | 2 | 全部 `pending` |
| `20260911T003529_task` | `pending_detail_collection` | 3 | 全部 `pending` |
| `20260911T012231_task` | `failed_processing`，有 meta、45 张原图、无 analysis | 1 | `pending` |
| `20260911T012231_task` | `pending_detail_collection` | 4 | 全部 `pending` |

原因链：

1. Pipeline 为所有搜索 candidates 写入 web snapshot；这一步本身正确，因为商品总览需要保留搜索发现事实。
2. `DataStore.import_run()` 对每个 product snapshot 无条件创建 Review 默认行。
3. `_snapshot_dict()` 只根据 Review 状态和 Membership 生成 `decisionStatus`，不知道该 Snapshot 是否 Analysis-ready。
4. Inspection Workspace 默认选择第一个 `decisionStatus=pending`，因此搜索候选和失败项进入正常人工复核队列。
5. Review API 和 `ReviewDecisionService` 没有 Analysis-ready 前置条件，UI 也会显示正式决策按钮。

### 4.2 最小修正方案

建立一个后端唯一的派生谓词，所有 import、统计、查询和 mutation 共用：

```text
analysisReady =
    snapshot.status == "success"
    AND snapshot.metaPath 指向安全且存在的 meta.json
    AND snapshot.analysisPath 指向安全且可解析的 analysis.json
    AND snapshot.ocrImageCount >= 1
```

最小实现不要求改 schema：

1. Snapshot DTO 增加只读 `reviewEligibility`，至少包含 `eligible` 和稳定 reason code；不要把 eligibility 塞进 Review status。
2. 商品总览继续返回所有 Snapshot，并按真实 pipeline status 展示。
3. Review Queue、`pendingReview` 统计和 `awaiting_review` 业务状态只计算 `analysisReady` Snapshot。
4. Review 与 ReviewDecision mutation 在同一后端应用层再次检查该谓词；不满足时返回 409，React 不自行拼装检查。
5. 新 import 不应为未 ready Snapshot 创建业务 Review；为兼容既有 1:1 查询，可先将 reviews join 改为 LEFT JOIN。若第一轮实现选择暂时保留 placeholder row，则它必须被明确标为 `eligible=false`，不得投影成 pending、不得计数、不得操作。
6. 历史自动生成但从未人工处理的 pending rows 按相同谓词屏蔽；不得删除已有人工作出结论或已有关联 Membership 的历史事实。
7. Recommendation error 不影响 `analysisReady`，详情显示真实证据、Review 和“抽检辅助建议暂不可用”。

## 5. 流程条状态投影审计

### 5.1 当前错误

`taskFlowIndex()` 仅识别运行中的三个技术阶段，其他所有 stage 都返回索引 3。`FlowStrip` 采用 `index < activeIndex => done`，因此：

- `completed_with_errors`、`failed`、`interrupted`、`collection_completed`、`completed` 都会把搜索、详情、线索识别显示为完成；
- `businessStatus=partial_error` 只改变 Task badge，不参与各步骤状态；
- `archiveSummary.errorCount`、`detailCompleted/detailTarget` 和 `statistics.analyzedProducts` 未参与流程条判断；
- `pendingReview` 又包含未 ready Snapshot，使人工复核分母虚高。

真实例子：

- `20260911T003529_task` 为 `completed_with_errors`，Detail 真实为 0/2、错误 2，但现有算法会勾选“采集详情”和“线索识别”。
- `20260911T012231_task` 为 `completed_with_errors`，Detail 真实为 1/1、Analysis 为 0、错误 1，但现有算法仍勾选“线索识别”，并显示人工复核 0/5。

### 5.2 最小投影设计

不增加持久状态机。新增一个纯 presentation 函数，以 Task stage/business status、现有 statistics、archive summary 和本 Task 的 Snapshot statuses/paths 计算四步状态：

| 步骤 | completed | active | partial/failed | future |
| --- | --- | --- | --- | --- |
| 搜索商品 | 已形成至少一个任务 Candidate，且阶段已离开搜索 | initializing/searching，或人工验证发生在尚未形成 Candidate 时 | Task 已终止且没有成功 Candidate；当前 Collector 的零候选会作为搜索错误 | 尚未启动 |
| 采集详情 | `detailSucceeded == detailTarget > 0` | stage=`collecting_details`，或人工验证发生在详情阶段 | 终态且 `0 < detailSucceeded < detailTarget` 为 partial；`detailSucceeded=0` 且 target>0 为 failed | 搜索尚未完成 |
| 线索识别 | `analysisReadyCount == plannedAnalysisCount > 0` | stage=`processing_ocr_analysis` | 终态且部分 Analysis-ready 为 partial；零 Analysis-ready 且计划数>0 为 failed | 尚无 Detail 成功商品 |
| 人工复核 | 存在 eligible Snapshot 且 eligible pending=0 | eligible pending>0 | 不把上游采集/识别失败伪装成人工复核失败；Task 的 partial_error badge继续承载批次异常 | eligible Snapshot=0，显示“尚无可复核商品” |

其中：

- `detailSucceeded` 不能只看目录，应使用有效 meta 和正式 Detail 门槛；现有 `archiveSummary.detailCompleted` 可作为过渡，但必须修正零原图成功问题。
- `analysisReadyCount` 使用第 4.2 节的统一谓词。
- `plannedAnalysisCount` 是合并去重后进入详情/OCR/分析的全局目标，不是搜索 Candidate 总数。
- 各步骤允许使用 `completed`、`active`、`partial/failed`、`future` 四类视觉状态，但不新增 Task business status。

## 6. Phase3 与 D6 离线独立验证

### 6.1 代码变化审计

以下文件在 D6 集成基线 `c8d962c` 与当前 HEAD 之间的 Git blob 完全相同：

- `src/phase2_ocr.py`
- `src/phase3_analysis.py`
- `src/inspection_runtime.py`
- `src/effect_risk_bridge.py`
- `src/inspection_knowledge.py`
- `src/inspection_applicability.py`
- `src/inspection_recommendation.py`
- `config/effect_keywords.json`
- `config/inspection_reference.json`
- `config/risk_substance_reference.json`

因此 OCR 模型参数、Phase3 规则分析以及 D2-D6 Recommendation 核心没有被 UX 重构改写。

### 6.2 旧 OCR fixture 运行当前 Phase3

测试方法：将旧成功商品 `982036041270` 的 `meta.json`、`dom_text.txt` 和完整 `ocr/` 复制到系统临时目录，只使用当前 worktree 的 `src/phase3_analysis.py` 和当前 `config/effect_keywords.json` 运行，未修改原 run。

结果：

- 成功生成 `analysis.json`、`analysis_input.txt`、`phase3_analysis_report.md`；
- 输入统计仍为 title 1、DOM 58 行、OCR 成功 13 张/322 行、总输入单元 381；
- `detected_effects`、matched keywords、evidence、来源计数、risk reason、review_required、排除证据等业务字段与历史 `analysis.json` 全部一致；
- 仅时间和绝对配置路径等运行环境字段允许变化，不构成业务差异。

### 6.3 旧 Analysis 运行当前 Recommendation

测试方法：在同一临时副本和临时 SQLite 中使用当前 `InspectionRuntime.create()` 导入当前已核验 Reference，再对当前生成的 `analysis.json` 运行 `generate()`。

结果：

- 成功生成 `inspection_recommendation.json`；
- 新结果与历史 Recommendation JSON **逐字段完全一致**；
- 本 fixture 仍为 0 个 mapped risk findings、1 个 unmapped evidence、0 个 knowledge gaps，符合历史事实，没有补造成分或方法。

结论：**风险分析核心未发生 UX 重构回归；当前后半链 contract 可消费历史成功产物。**

## 7. 依赖可重复性方案

### 7.1 当前缺口

`requirements-ocr.txt` 当前为：

```text
paddlepaddle==3.2.0
paddleocr>=3.0,<4
Pillow>=10,<13
```

该文件只固定 PaddlePaddle，不能固定 PaddleOCR、PaddleX 或图像依赖闭包，也没有声明运行 Web 服务必须使用哪个解释器。Git worktree 不会自动复制或同步虚拟环境，因此两个目录即使代码相同也会漂移。

### 7.2 建议的最小稳定基线

下一轮应基于已被真实 run 验证的环境建立 `requirements-ocr-lock.txt` 或等价 constraints 文件，核心至少固定：

```text
# Runtime: CPython 3.10.0, Windows x86-64
paddlepaddle==3.2.0
paddleocr==3.7.0
paddlex==3.7.2
Pillow==12.1.0
numpy==2.2.6
opencv-contrib-python==4.10.0.84

# Runtime contract, recorded outside pip requirement syntax:
# ocrVersion=PP-OCRv6
# modelSource=bos
# device=cpu
```

其中 PaddleOCR/PaddlePaddle/PP-OCRv6 是历史产物直接证明的事实；PaddleX 和图像依赖版本来自当前保留的稳定 `.venv`，应在生成 lock 后用一张历史原图做离线 OCR smoke 再定稿。

运行和安装必须始终使用同一解释器，例如：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr-lock.txt
.\.venv\Scripts\python.exe -m src.local_api --output-root output
```

Web 服务启动前应做 fail-fast preflight，至少记录并校验：`sys.executable`、Python、PaddlePaddle、PaddleOCR、PaddleX、requested OCR version、supported OCR versions、model source、device 和 cache path。版本不匹配时在启动任务前报告环境错误，不应等到真实商品采集完才失败。

## 8. 一次性修正清单

### P0 — 下一次真实 E2E 前必须完成

1. **固定并验证 OCR 环境**：以 Python 3.10.0 / PaddlePaddle 3.2.0 / PaddleOCR 3.7.0 / PaddleX 3.7.2 / PP-OCRv6 / BOS / CPU 为基线建立 lock，并增加 Web worker 启动前 preflight。
2. **收紧 OCR 完成契约**：manifest 至少一个 success 且对应 txt/json 存在；零成功必须抛明确错误，不得进入 Phase3。
3. **建立统一 Analysis-ready predicate**：Task 统计、DataStore import、Snapshot DTO、Review Queue、Review mutation 和 Sampling decision 必须复用同一准入逻辑。
4. **阻止未 ready Review**：搜索候选、详情失败、OCR/Phase3 失败不计 pending、不进入默认待复核筛选、不显示 Review decision；后端 mutation 必须返回 409 防止绕过 UI。
5. **替换 ordinal `taskFlowIndex` 投影**：使用真实候选、计划分析、Detail 成功、Analysis-ready 和失败计数，至少呈现 completed / active / partial-or-failed / future。
6. **增加混合结果集成测试**：同一 Task 同时包含搜索-only、Detail 失败、OCR 失败、Analysis 成功、Recommendation 失败，验证流程条、业务状态、pending count、队列和 mutation 边界一致。

### P1 — 与 P0 同批或紧随其后

1. Detail 成功增加最小原图/OCR-candidate 门槛，避免零原图 `meta.json` 被视为完整 Detail。
2. 为 `failed_processing` 增加只读 stage-specific failure projection，至少区分 `ocr_failed` 与 `analysis_failed`；无需增加新的持久 Task 状态机。
3. OCR `run_info.json` 增加 Python 版本、`sys.executable`、PaddleX、cache path 和 supported versions，避免以后只能从残留 `.venv` 推断环境。
4. 为 Phase3 顶层失败保留结构化错误文件，避免只靠 `batch_state.json` 文本区分 OCR 与 Analysis。
5. 对历史未 ready 的自动 pending rows 做兼容投影/修复：只屏蔽系统自动默认且从未人工处理的行，不覆盖任何已完成 Review 或 Membership。

## 9. 明确无需修改的范围

本次证据表明以下部分无需为当前问题修改：

- 不把 `PP-OCRv6` 降为 PP-OCRv5；历史真实数据已经验证 v6 可工作。
- 不修改 `src/phase3_analysis.py` 的风险分类规则或 `config/effect_keywords.json`。
- 不修改 D2-D5 bridge、knowledge、applicability、recommendation 核心。
- 不修改 `InspectionRuntime` 的 Recommendation 生成规则。
- 不修改 Reference 或 Risk 数据及其 SHA/来源。
- 不修改淘宝 DOM selector、详情 tab、滚动、Network 图片选择或 Collector 算法。
- 不修改 ManualActionGate 语义；上一轮 adapter 接线修复已通过回归和真实 Detail 采集。
- 不修改 Sampling Export、XLSX、历史清单或现有 Review/Membership 实体分离原则。
- 不需要为本 Gate 改 schema；准入、统计和投影可以通过应用层/查询层收紧。
- 不增加新的 UI 信息架构或业务功能。

## 10. Gate 停止点

本审计已完成 OCR 环境根因、完整 Artifact Contract Matrix、Review Queue 边界、流程条投影、Phase3/D6 离线兼容验证及修正优先级。下一步应先批准 P0 修正集合，再一次性实现和定向验证；在此之前不应继续真实淘宝 E2E。
