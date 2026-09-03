# 项目当前状态

更新时间：2026-09-04

当前开发版本：v0.8-A1（Inspection Reference Integrity Tightening）

当前稳定冻结基线：v0.7 Product Monitoring Workspace，commit `98e732b88ef74dd5505646abaef0134e23a7adaf`，标签为 `product-workspace-v0.7`。v0.8-A/A1 只新增 Inspection Reference schema、校验与导入基础并收紧 verified 数据完整性，不改变 v0.7 的 Product Workspace、Web、Pipeline 或风险规则。

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
| Inspection Method/Substance/Applicability/RegulatoryContext 独立 Reference Data 基础 | 已实现并通过离线测试；尚无正式监管数据 | `src/inspection_reference.py`、`src/data_store.py` |

当前测试集共有 156 项，其中 v0.8-A/A1 包含 19 项 Inspection Reference contract、幂等/非删除导入、状态/所有权、事务和 v4→v5 升级测试；v0.7 冻结时的 137 项基线仍由 `product-workspace-v0.7` 保留。

## 3. 当前架构

### 3.1 运行链路

`src/local_api.py` 使用标准库 `ThreadingHTTPServer` 同时提供静态 Web 页面和本地 API。Web 创建任务后，`TaskManager` 在受控后台线程中调用已经冻结验证的 `StandalonePipeline`，HTTP 请求无需等待整个采集过程结束。

Quick Task 直接将一个关键词交给 `LiveSearchCollector`。Monitor Task 先由 `DiscoveryCoordinator` 按配置顺序串行执行多个 `SearchQuery`，再合并候选并调用同一个详情/OCR/分析主链，没有重写 Collector。

任务实时状态继续以 `output/<run_id>/web_snapshot.json` 为稳定契约，前端轮询读取。关键 JSON 使用“临时文件写完后原子替换”；Windows 短暂文件占用时会有限重试，避免 Web 读到半截 JSON。

### 3.2 数据分层

- `output/<run_id>/` 是原始运行事实与可追溯证据的主存储：搜索 HTML/截图/诊断、详情 HTML、Network 响应、原图、OCR、`analysis.json`、日志及批次报告均保留在此。
- `data/app.db` 是同一个 SQLite 业务数据库，当前 schema version 为 5。除既有任务、商品、Evidence、Review 和 Monitor 数据外，现可保存独立的 Inspection Reference 数据；已有 version 4 数据库原位升级时只创建新表，不重建或清空旧记录。
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
- `inspection_method_applicabilities`：方法的适用、排除或条件性产品/基质范围；
- `substance_regulatory_contexts`：物质在特定产品范围、辖区和有效期内的监管语境及独立 provenance。

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
- v0.8-A 只有 Inspection Reference 数据结构、validator 和 SQLite import 基础；尚未导入任何正式 BJS/KJ/GB/T 数据，也没有 RiskClue→Substance、自动检测建议、Web/API 展示或商品级 Recommendation。

## 9. 下一阶段候选事项（尚未实现）

优先级需要在下一轮需求确认后决定，本文件不代表已经排期：

- `GEO-01`：采集商品页面声明产地；
- `GEO-02`：采集卖家所在省市；
- `GEO-03`：候选商品按地区均衡选择；
- `INSPECTION-01`：Foundation 已由 v0.8-A 完成；Verified Inspection Dataset（正式 BJS/KJ/GB/T 数据）计划在 v0.8-B 单独建设；
- `INSPECTION-02`：风险线索与目标化合物关联；
- `INSPECTION-03`：目标化合物与检验方法/标准关联；
- `INSPECTION-04`：商品检测建议生成；
- `INSPECTION-05`：最终结果增加产品名、链接、可能风险、建议检测成分和相关标准；
- 改进人工登录/验证的 Session UX；
- 增加安全的任务取消与状态恢复；
- 后续按业务需要评估产品场景并逐批验证新的 SearchQuery；不在 v0.6 内批量补齐剩余对象，也不允许模型按常识随意生成搜索词；
- 以标注样本评估并提升 OCR/风险规则质量。

`INSPECTION-01` 当前只完成数据 Foundation，正式 Verified Data 仍为 planned / not implemented；`INSPECTION-02`—`INSPECTION-05` 均为 planned / not implemented。当前没有关联数据、建议生成逻辑或前端字段，不得用假数据或写死映射提前展示。

继续开发前应先阅读 `docs/AI_HANDOFF.md` 和 `docs/DEVELOPMENT_HISTORY.md`，并把 `product-workspace-v0.7` 视为当前整体稳定回退基线；正式数据与 Query 策略以 `reference-data-v0.6` 为基线，修改 Collector 时仍以 `collector-baseline-v0.2` 为专门对照。
