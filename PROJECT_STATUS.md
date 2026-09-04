# 项目当前状态

更新时间：2026-09-04

当前开发版本：v0.8-D2（Evidence-to-Risk Taxonomy Bridge）

当前稳定冻结基线：v0.7 Product Monitoring Workspace，commit `98e732b88ef74dd5505646abaef0134e23a7adaf`，标签为 `product-workspace-v0.7`。v0.8-A 系列建立 Inspection Reference 基础；v0.8-B1—B5 已逐批加入核验的 BJS 202209、BJS 201701、BJS 201710、KJ201903 与 GB/T 45443-2025，并首次纳入褪黑素 RegulatoryContext。v0.8-C 阶段已完成 Risk→Group/Substance Verified Data；v0.8-D1/D1.1 建立并强化只读 Knowledge Trace。v0.8-D2 新增独立 Evidence-to-Risk taxonomy bridge，只按 Phase 3 `evidence_details` 中的 `effect + matched_keyword` 精确匹配：当前正式配置仅有“减脂+减肥→weight_loss”“男性相关+壮阳→male_function”“男性相关+补肾→male_function”3 条内部 Bridge，未桥接关键词显式保留，`content_origin` 原样保留。D2 不调用 KnowledgeResolver、不生成 InspectionRecommendation，也不接入 Product Workspace、Web 或 Pipeline。

当前分支：`main`

v0.6-C1 提交：`e8cf28d`（`Validate SearchQuery Policy and Pilot Targets v0.6-C1`）
稳定标签：`collector-baseline-v0.2`、`task-runtime-v0.3`、`data-review-v0.4`、`monitoring-discovery-v0.5`、`reference-data-v0.6`、`product-workspace-v0.7`

## 1. 当前结论

项目已经从单次技术验证发展为可重复运行的本地工程化 MVP。目前真实验证过的完整主链是：

> Web 或命令行创建任务 → 项目自行启动可见 Chrome → 淘宝真实搜索 → 候选提取与去重 → 商品详情采集 → DOM 归属的详情原图 → PaddleOCR → 配置化功效线索分析 → Evidence → 文件输出、SQLite 索引与 Web 展示。

项目不依赖 Codex、ChatGPT 桌面应用或浏览器控制插件才能运行。淘宝要求登录或人工验证时，程序只暂停并提示用户在项目打开的可见浏览器中处理，不破解验证码，也不绕过平台安全控制。

当前版本的结论仅适用于已经验证的小规模、低并发、本机运行场景。它不代表大规模爬取能力，也不代表系统可以认定违法、验证功效真实性或检测实际非法添加物。

## 2. 当前已完成能力

| 能力 | 当前状态 | 主要实现 |
| --- | --- | --- |
| 可见 Chrome/CDP 启动、独立持久化 profile | 已真实验证 | `src/taobao_live.py` |
| 淘宝首页正常搜索流程、搜索卡片解析、去重与 Search Diagnostics | 已真实验证 | `src/taobao_live.py` |
| `candidate_limit` 与 `detail_limit` 分离 | 已真实验证 | `src/main.py`、`src/taobao_live.py` |
| 详情页打开、图文详情定位、内容边界感知滚动 | 已真实验证 | `src/phase1_experiment.py` |
| DOM 详情图归属、Network 原图响应/补取、页面截图留证 | 已真实验证 | `src/phase1_experiment.py` |
| PaddleOCR CPU 逐图识别、manifest 与文本/JSON 输出 | 已真实验证 | `src/phase2_ocr.py` |
| 配置化功效词匹配、来源归属、推荐商品排除 | 已真实验证 | `src/phase3_analysis.py` |
| Evidence、批次 JSON/CSV/Markdown、日志与 Web Snapshot | 已真实验证 | `src/phase3_analysis.py`、`src/phase5_batch.py`、`src/web_contract.py` |
| 中断状态保存、详情/OCR 断点续跑、单商品失败隔离与重试 | 已实现并有真实/离线证据 | `src/main.py` |
| Web 创建、轮询、恢复任务；单活动任务 409 保护 | 已真实 Web E2E 验证 | `src/task_runtime.py`、`src/local_api.py` |
| SQLite 业务索引与人工复核状态持久化 | 已实现并通过离线/重启测试 | `src/data_store.py` |
| MonitorTarget、多 SearchQuery、跨 Query 去重与 CandidateHit | 已真实 Web E2E 验证 | `src/discovery.py`、`src/data_store.py` |
| development/reference 数据集分离、106 项正式食药物质、来源校验与幂等导入 | 已实现并通过离线测试 | `src/data_store.py`、`config/monitor_targets.*.json` |
| SearchQuery 来源/验证状态、6对象Pilot与search-only验证记录 | 已真实搜索验证 | `src/search_query_validation.py`、`docs/search_query_pilot_v0.6-c1.md` |
| 商品服务端分页、MonitorTarget筛选与范围内最新快照语义 | 已实现并通过离线/API测试 | `src/data_store.py`、`src/local_api.py` |
| 风险总览、商品监测、风险研判、采集任务 Web 页面 | 已接入真实数据；商品监测使用 SQLite Product API | `web/` |
| 原生 ES Modules 与分层 CSS | 已完成并通过语法、契约和本地浏览器验证 | `web/app.js`、`web/js/`、`web/css/` |
| 统一 B2B 视觉、密集商品表、状态反馈与 1080px/1440px 响应式布局 | 已完成并通过本地浏览器验收 | `web/index.html`、`web/css/`、`web/js/pages/` |
| Inspection Method/Substance/Applicability/RegulatoryContext 独立 Reference Data 基础 | verified dataset 已含三项 BJS、KJ201903 与 GB/T 45443-2025；GB/T 是首个 `national_standard_gbt`，并新增首个 SubstanceRegulatoryContext。褪黑素可同时是方法目标物及限定产品范围和时间下的合法保健食品原料；GB/T 45443 是正常质量/含量检测标准，不是非法添加补充检验方法 | `src/inspection_reference.py`、`src/data_store.py`、`config/inspection_reference.json` |
| Risk→Substance/Group 独立 Reference Data | schema version 1；正式数据共 8 条：保留 3 条 A/current Group Mapping，新增 5 条同级别 Substance Mapping，具体目标仅为来源点名且已存在的西布曲明、西地那非、他达拉非；不按方法目标物清单推断其他 Group 成员 | `src/risk_substance_reference.py`、`src/data_store.py`、`config/risk_substance_reference.json` |
| Inspection Knowledge Trace | 以 SQLite 为运行时查询索引且只消费 verified Risk Dataset，动态执行 Risk Mapping→Substance→MethodSubstance→Method；Group/Substance 按 identity 唯一输出，多来源保存在 `mapping_evidence` 列表，并分别挂载 Applicability 与 RegulatoryContext；Group 保持 `partial`，缺口显式输出，不排序推荐、不判断商品适用性或违法性 | `src/inspection_knowledge.py`、`src/data_store.py` |
| Evidence-to-Risk Taxonomy Bridge | 按 Phase 3 Evidence 的 `effect + matched_keyword` exact match 生成唯一 RiskSignal；仅含 3 条 verified internal bridge，保留 seller-managed/UGC `content_origin` 与未桥接证据；不按 category 整体映射，不调用 KnowledgeResolver、不生成 InspectionRecommendation；`anti_fatigue` 尚无 Phase 3 detection bridge | `src/effect_risk_bridge.py`、`config/effect_risk_bridge.json` |

当前测试集共有 253 项，其中 D2 新增 28 项 Bridge 测试，覆盖正式 3 条配置、交叉引用 validator、exact keyword matching、RiskSignal 去重、确定性 Mapping 排序、seller-managed/UGC 来源保留、显式 unmapped evidence 与空/未知输入；D1/D1.1 的 19 项 Knowledge Trace 测试及既有 Inspection、Risk Reference、Phase 3 测试继续保留。v0.7 冻结时的 137 项基线仍由 `product-workspace-v0.7` 保留。

## 3. 当前架构

### 3.1 运行链路

`src/local_api.py` 使用标准库 `ThreadingHTTPServer` 同时提供静态 Web 页面和本地 API。Web 创建任务后，`TaskManager` 在受控后台线程中调用已经冻结验证的 `StandalonePipeline`，HTTP 请求无需等待整个采集过程结束。

Quick Task 直接将一个关键词交给 `LiveSearchCollector`。Monitor Task 先由 `DiscoveryCoordinator` 按配置顺序串行执行多个 `SearchQuery`，再合并候选并调用同一个详情/OCR/分析主链，没有重写 Collector。

任务实时状态继续以 `output/<run_id>/web_snapshot.json` 为稳定契约，前端轮询读取。关键 JSON 使用“临时文件写完后原子替换”；Windows 短暂文件占用时会有限重试，避免 Web 读到半截 JSON。

### 3.2 数据分层

- `output/<run_id>/` 是原始运行事实与可追溯证据的主存储：搜索 HTML/截图/诊断、详情 HTML、Network 响应、原图、OCR、`analysis.json`、日志及批次报告均保留在此。
- `data/app.db` 是同一个 SQLite 业务数据库，当前 schema version 为 7。除既有任务、商品、Evidence、Review、Monitor 与 Inspection 数据外，现可保存独立的 Risk-Substance Reference 数据；version 6 数据库升级时只新增两张空表，旧业务数据与 5/117/132/37/1 Inspection 数据均原位保留。
- SQLite 不替代原始证据文件。数据库可从历史 `output` 幂等重建，重复导入不会复制记录，也不会覆盖已经保存的人工复核备注。
- `.browser-profile/`、`output/`、`data/*.db`、`.venv/` 与 OCR 模型缓存均不提交 Git。

## 4. SQLite 与核心数据模型

当前表为：

- `monitor_datasets`：数据集身份、版本、状态、来源与核验时间；
- `tasks`：一次 Quick 或 Monitor 运行；
- `products`：按淘宝商品 ID 维护的稳定商品身份；
- `product_snapshots`：某商品在某任务中的一次页面快照；
- `evidence`：属于某个 ProductSnapshot 的结构化证据；
- `reviews`：属于某个 ProductSnapshot 的人工复核最新状态与备注；
- `monitor_targets`：被监测的标准对象；
- `search_queries`：某 MonitorTarget 下按确定顺序执行的搜索表达，并保存 query_source、validation_status、query_note（SQLite schema v4）；
- `candidate_hits`：某任务中“哪个 Query、以什么排名命中哪个商品”的来源事实。
- `inspection_datasets`：Inspection 数据集身份、状态、来源与核验时间；与 `monitor_datasets` 独立；
- `inspection_methods`：检验方法编号、类型、状态、替代编号及方法级 provenance；
- `inspection_substances`：物质规范身份，不承载固定“违法”属性；
- `inspection_method_substances`：方法与物质关系，同时保留来源原始名称和显式归一化说明；
- `inspection_method_applicabilities`：`substance_id=NULL` 表示 Method-level 范围；非空时表示该 Method 对已关联 Substance 的特殊适用、排除或条件范围；
- `substance_regulatory_contexts`：物质在特定产品范围、辖区和有效期内的监管语境及独立 provenance。
- `risk_mapping_datasets`：独立 Risk Mapping 数据集身份、版本、状态与 provenance；
- `risk_substance_mappings`：Risk Category/Clue 到一个既有 Inspection Substance 或来源 Group 文字的关系，不直接关联 Inspection Method。

Evidence 和 Review 归属于 ProductSnapshot，而不是永久归属于 Product。原因是淘宝页面内容、规则结果和人工判断都可能随采集时间变化。同一 Product 可以拥有多个任务快照。

当前本机数据库在本次文档审计时可正常打开，索引了历史 run；表数量会随导入与新任务变化，因此不作为固定产品指标。

## 5. Web 任务运行能力

当前 Web 支持两种任务：

- Quick Task：输入 `keyword`、`candidate_limit`、`detail_limit`；
- Monitor Task：选择 `target_id`，输入 `per_query_candidate_limit` 和 `detail_limit`。创建时会把 MonitorTarget 及有序 SearchQuery 快照写入 `task_request.json`，避免运行中配置变化改变本次任务含义。

任务状态包括搜索、详情采集、OCR/分析、需要人工登录/验证、完成、带错误完成、失败和中断。服务重启时，未结束且由 Runtime 管理的任务会标记为 `interrupted`；具备 `run_config.json`、搜索候选和批次状态的任务可以恢复。

当前只允许一个活动采集任务。第二个创建请求返回 HTTP 409，以防多个任务争用同一个浏览器 profile 和本机 OCR 资源。

## 6. MonitorTarget / SearchQuery / CandidateHit

`config/monitor_targets.development.json` 中继续保留开发种子：

- MonitorTarget：`酸枣仁`（`dev-food-medicine-suanzaoren`）；
- SearchQuery 1：`酸枣仁`（base）；
- SearchQuery 2：`酸枣仁茶`（product_form）。

该配置明确是 `development_seed`，只用于工程开发与真实流程验收，不是官方完整食药同源目录，也不是最终搜索词体系。

`config/monitor_targets.reference.json` 已标记为 `verified_reference`（版本 `2024.08`），包含国家卫生健康委 2002 年基础 87 项、2019 年新增 6 项、2023 年新增 9 项和 2024 年新增 4 项，共 106 个 MonitorTarget；2025 年官方答复用于核验总数。每个对象都指向首次纳入它的官方文件。2019 年新增 6 项保留“仅作为香辛料和调味品使用”的适用边界。

v0.6-C1 为 6 个 Pilot 建立 9 个 Query，并完成真实淘宝 search-only 验证。当前正式启用 5 个对象：酸枣仁、茯苓、龙眼肉（桂圆）、铁皮石斛、化橘红；当归 Query 虽能稳定召回，但前 10 条几乎都是中药材/饮片，结合“仅作为香辛料和调味品使用”的限制继续停用。其余 100 项无 Query 且停用。`query_source` 区分 standard_name、official_alias、observed_product_form、manual；只有 `validation_status=search_validated` 且 Query 启用时才可进入 Monitor Task。开发酸枣仁仍以独立 ID 和数据集存在。

多 Query 按 `order` 串行执行。候选以 `product_id` 跨 Query 去重，首次有效出现决定合并列表顺序；顺序首先由 Query 顺序决定，再由 Query 内排名决定。前 `detail_limit` 个唯一候选进入详情链。即使同一商品被多个 Query 命中，所有来源仍作为多条 CandidateHit 保留，供后续解释召回来源。

## 7. 当前真实验收结果

### v0.7-C 本地 Web 验收

使用现有 SQLite 与历史 output 启动本地服务，不访问淘宝、不运行 OCR、不创建采集任务。通过浏览器真实 CSS 视口分别验收 1440px 完整布局和 1080px 紧凑布局；1080px 下侧栏收为图标栏，筛选区切换为两列，商品表可横向查看，研判与任务页按响应式规则重排，没有严重遮挡或重叠。

商品工作台通过 Product API 读取 67 件跨任务商品；已验证 20 条/页与第 2/4 页服务端分页、正式铁皮石斛筛选为 5 件、关键词无结果与一键清除、加载骨架、接口断开时的局部错误与服务恢复后的重试、详情打开和中性缩略图占位。正式/开发同名酸枣仁在筛选与任务选择中分别显示为“酸枣仁 · 正式”和“酸枣仁 · 开发”。

研判页分别检查了有 `user_generated` Evidence 的酸枣仁历史样本和 0 Evidence 的铁皮石斛正式样本，确认商品信息、系统分析、Evidence、人工复核、原图/OCR 层级清晰；图片弹窗可由 Esc 关闭，复核保存有可见反馈。任务页明确分开当前任务、新建 Quick/Monitor 任务和历史任务，未启动新任务。基础词库与统计分析只显示“规划中/后续版本”说明，没有伪造图表、统计或检验能力。

v0.7-C2 随后用同一批本地 SQLite 数据复核 1440px 风险总览/采集任务和 1080px collapsed 商品工作台：已完成任务的 `1/5` 明确表示详情采集数量，不再绘制成总体 20% 进度；Dashboard 使用“候选未深采”；`stop_reason` 显示中文但未知值保留原文；任务名称与 `task_id` 分层；collapsed Sidebar 不显示分组文字；当前 run 文件入口统一使用“当前任务”。控制台仍为 0 error / 0 warning。

### v0.6 正式 Reference Monitor Web E2E

运行目录：`output/20260903T014401_task`。该任务从 Web 页面选择正式 `verified_reference` 对象“铁皮石斛”创建，没有通过命令行绕过任务层。

| 指标 | 实际结果 |
| --- | ---: |
| MonitorTarget | 铁皮石斛（`food-medicine-2023-003`） |
| 数据集 | `food-medicine-reference` / `verified_reference` / `2024.08` |
| SearchQuery | 铁皮石斛（`standard_name`、`search_validated`） |
| 搜索页实际可见卡片 | 46 |
| CandidateHit / 去重候选 | 5 / 5 |
| 进入详情 / 详情成功 | 1 / 1 |
| 保存原始详情图 | 31 |
| OCR 成功图片 | 26 |
| 完成分析 | 1 |
| Evidence | 0（未发现配置词库中的明显功效表达） |
| 失败 / 重试 | 0 / 0；详情尝试 1 次 |
| 停止原因 | Query：`candidate_limit_reached`；Discovery：`all_queries_completed` |
| 运行时间 | 01:44:01—01:54:08，约 10 分 7 秒 |

任务未要求登录或验证码，未发生淘宝采集失败。Web 自动显示新任务、5 个候选和已完成商品；风险研判页可查看 31 张真实原图、26 张 OCR 结果以及 Evidence 为 0 的正常业务结论。SQLite 中存在对应 Task、5 条 CandidateHit、1 条 ProductSnapshot 和稳定 Product；历史 development 酸枣仁任务仍可读取。

### v0.5 Monitor Web E2E

运行目录：`output/20260902T192913_task`。该任务由 Web 创建，不是手工命令启动 Pipeline。

| 指标 | 实际结果 |
| --- | ---: |
| MonitorTarget | 酸枣仁 |
| SearchQuery | 酸枣仁、酸枣仁茶 |
| 每个 Query 请求候选 | 10 |
| 两页实际可见卡片合计 | 92（各 46） |
| CandidateHit | 20 |
| 跨 Query 去重候选 | 19 |
| 完成详情 | 2 |
| 保存原始详情图 | 32 |
| OCR 成功图片 | 27 |
| 完成分析 | 2 |
| 检测到配置词库线索/建议人工复核 | 2 |
| Evidence | 8（分别 3、5） |
| 失败商品 | 0 |
| 运行时间 | 19:29:13—19:38:31，约 9 分 18 秒 |

两个 Query 均以 `candidate_limit_reached` 停止；两件详情均以 `detail_container_stable` 停止滚动。完整生成了 `products.json`、`products.csv`、`summary.md`、`web_snapshot.json`、合并候选、discovery summary 和两份独立 Search Diagnostics，Web 可查看商品、图片、OCR 与 Evidence。

同日第一次 Monitor 预检目录 `output/20260902T192644_task` 在 Playwright 创建子进程前因受限执行环境触发 `PermissionError: [WinError 5]`。它不是淘宝风控或 Collector 失败；在普通本地进程环境重新启动后，上述 E2E 完成。

### 仍保留的基线证据

- `output/20260902T005526_task`：v0.3 Web E2E；10 个候选、2 件详情、37 张原图、30 张 OCR 成功图、2 件完成分析、0 失败，约 11 分 49 秒。
- `output/20260901_collector_v02_e2e`：v0.2 CLI 完整 E2E；10 个候选、2 件详情、25 张原图、23 张 OCR 成功图、2 件完成分析、0 失败，约 7 分 18 秒。
- `output/20260901_collector_v02_test_b`：请求 50 个候选，真实搜索页获得 46 个去重候选；采集 5 件详情、76 张原图。该 run 使用 `--skip-ocr`，不能视作完整 E2E。
- `output/20260828_cdp_smoke2`：10 件详情、176 张原图，只有 1 件完整分析；后续 OCR 被用户停止，不能声称 10 件全部分析完成。

## 8. 当前主要限制

- 只验证了小批量、串行、本机单用户运行；没有 100 商品、长期连续运行或并发吞吐结论。
- 淘宝 DOM、类名、登录和平台风控均可能变化；Selector Health 只能告警，不能自动修复选择器。
- 普通 Chrome 的淘宝登录状态不会自动等同于项目 `.browser-profile` 的登录状态；必须以项目打开的可见浏览器为准。
- 任务需要人工验证时仍依赖服务终端按 Enter；Session UX 尚不完善，也没有任务取消接口。
- 详情正文主要围绕当前观察到的 `#imageTextInfo-container`；不同淘宝/天猫模板仍需持续真实回归。
- OCR 在 CPU 上耗时明显，识别范围受详情图筛选和图像质量影响；未做性能优化或质量模型评估。
- 功效分析是配置化字面规则，不能覆盖隐含表达、否定、反讽和复杂语义；用户评价/问答只作辅助线索。
- 当前 `region` 来自搜索卡片展示字段，不能等同于商品声明产地或卖家注册所在地。
- 正式 reference dataset 已包含 106 项，但仅 6 项做过 SearchQuery Pilot、5 项具备当前运行资格；剩余 101 项（包含已验证召回但因场景边界停用的当归）不能直接创建正式 Monitor Task。5 个已启用对象中，目前只有铁皮石斛完成了正式 verified target 的详情/OCR/分析 Web E2E。
- Product API 当前没有商品列表缩略图字段；商品表使用明确的中性图片占位，而不是伪造商品图。详情页继续展示历史 run 中的真实原图。
- 1080px 下密集商品表保留横向滚动以维持字段可读性；本轮覆盖桌面与紧凑桌面，不承诺手机端完整适配。
- 基础词库与统计分析仍是明确的后续版本规划页，没有 CRUD、图表或分析能力。
- MonitorTarget 下拉当前按既有 API 只展示 enabled target；这不代表其余正式对象已经具备 Monitor Task 运行资格。
- 正式 Inspection Reference 当前仅逐项核验并纳入 BJS 202209、BJS 201701、BJS 201710、KJ201903 与 GB/T 45443-2025，不代表全部现行检验方法或全部监管知识；褪黑素 RegulatoryContext 只适用于明确的保健食品原料目录、产品要求和有效时间，不能外推为普通食品可任意添加。Risk-Substance 当前只有 3 条 Group 与 5 条具体 Substance Mapping；D2 也只有 3 条 keyword-level Bridge，且 `anti_fatigue` 尚无 Phase 3 detection bridge。D1/D2 仍未组合，不做完整 Group Expansion、商品范围匹配、方法推荐或法律判断。BJS 202405 尚未逐项核验和导入，也没有 Web/API 展示或商品级 Recommendation。

## 9. 下一阶段候选事项（尚未实现）

优先级需要在下一轮需求确认后决定，本文件不代表已经排期：

- `GEO-01`：采集商品页面声明产地；
- `GEO-02`：采集卖家所在省市；
- `GEO-03`：候选商品按地区均衡选择；
- `INSPECTION-01`：Foundation 已由 v0.8-A 完成；v0.8-B1—B5 已逐批完成三项 BJS、KJ201903、GB/T 45443-2025 与首条 RegulatoryContext 的 Verified Data，其余方法和监管语境仍需逐批核验；
- `INSPECTION-02`：C 阶段已完成首批 Verified Risk→Group/Substance 数据，D2 已完成首批 3 条 Phase 3 Evidence keyword bridge；完整 Group Expansion 与更多 lexical alignment 仍未实现；
- `INSPECTION-03`：D1 已完成只读动态 Knowledge Trace；商品级方法适用性与 Recommendation 仍未实现；
- `INSPECTION-04`：商品检测建议生成；
- `INSPECTION-05`：最终结果增加产品名、链接、可能风险、建议检测成分和相关标准；
- 改进人工登录/验证的 Session UX；
- 增加安全的任务取消与状态恢复；
- 后续按业务需要评估产品场景并逐批验证新的 SearchQuery；不在 v0.6 内批量补齐剩余对象，也不允许模型按常识随意生成搜索词；
- 以标注样本评估并提升 OCR/风险规则质量。

`INSPECTION-01` 当前已完成数据 Foundation，并纳入五个已核验方法和首条监管语境，但仍不是完整知识库。v0.8-C 阶段完成首批 Verified Risk→Group/Substance 数据；v0.8-D1 只通过既有外键关系动态生成 Knowledge Trace；v0.8-D2 只把 3 个明确 Phase 3 `effect + matched_keyword` 对齐到稳定 Risk Category。D1 与 D2 尚未组合，不新增 Risk→Method 持久关系。不得根据 Method 目标物清单推断 Group 成员。BJS 202405、完整 Group→Substance 展开、商品级 InspectionRecommendation 及 `INSPECTION-05` 仍为 planned / not implemented。

继续开发前应先阅读 `docs/AI_HANDOFF.md` 和 `docs/DEVELOPMENT_HISTORY.md`，并把 `product-workspace-v0.7` 视为当前整体稳定回退基线；正式数据与 Query 策略以 `reference-data-v0.6` 为基线，修改 Collector 时仍以 `collector-baseline-v0.2` 为专门对照。
