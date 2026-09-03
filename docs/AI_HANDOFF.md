# AI 接手指南

本文面向没有既往对话上下文的新 ChatGPT、Codex 或开发人员。它描述最终冻结 v0.7 的代码结构、运行边界和不可轻易破坏的工程约束。项目演进原因与踩坑过程见 `docs/DEVELOPMENT_HISTORY.md`；当前完成度见根目录 `PROJECT_STATUS.md`。

## 1. Current Version

- 当前冻结版本：**v0.7 — Product Monitoring Workspace**；标签为 `product-workspace-v0.7`。
- v0.6-A、v0.6-B、v0.6-C1 和最终正式 Monitor Web E2E 均已完成；当前整体稳定回退基线为 `product-workspace-v0.7`，正式数据与 Query 策略基线为 `reference-data-v0.6`。
- v0.7-A 已完成商品服务端分页与 Target 范围内 latest Snapshot 语义；v0.7-B 已把商品监测前端迁移到 Product API 并拆分原生 ES Modules/分层 CSS；v0.7-C 完成统一 B2B 视觉、状态反馈与 1440px/1080px 响应式验收；v0.7-C2 进一步校正候选深采、历史任务进度、task_id、stop_reason、collapsed Sidebar 和当前任务文案。SQLite schema 仍为 version 4。
- 当前阶段：本地、单用户、单活动任务的工程化 MVP。
- 状态口径：
  - **已真实验证**：存在真实淘宝 run，可从输出文件核查；
  - **已实现并离线验证**：代码与自动化测试存在，但没有为该能力单独执行新的真实淘宝 E2E；
  - **规划中**：只记录需求，不得描述成已实现。

## 2. Current Commit

v0.7 最终冻结基于已经推送的 v0.7-C2：

```text
6f95313a70c507ef34fbe68dace30c0237a49b94
Refine UI Semantics v0.7-C2
```

v0.7 最终冻结提交由 `product-workspace-v0.7` tag 指向，应以 `git rev-parse product-workspace-v0.7` 核查。v0.6 数据与 Query 策略基线仍由 `reference-data-v0.6` 指向；不要依赖旧对话中的短哈希。

## 3. Stable Tags

| Tag | Commit | 含义 |
| --- | --- | --- |
| `collector-baseline-v0.2` | `3c77b795332f5e961d1c28a74cfd82caf37760e7` | 淘宝采集核心稳定基线 |
| `task-runtime-v0.3` | `6225635f28fe7767136baca4bd3d9d28ddce3efc` | Web 创建/运行/轮询任务基线 |
| `data-review-v0.4` | `53f0b88638dcd0daea6ea59436c4e2cdc35af9f9` | SQLite 与人工复核基线 |
| `monitoring-discovery-v0.5` | `2ffafd749cd20dcdde0346f953c6e8e9a9c67472` | MonitorTarget、多 Query 与 CandidateHit 基线 |
| `reference-data-v0.6` | 以 `git rev-parse reference-data-v0.6` 为准 | 正式目录、来源追踪、Query 策略与 Pilot 验证基线 |
| `product-workspace-v0.7` | 以 `git rev-parse product-workspace-v0.7` 为准 | 跨任务 Product Workspace、前端模块化与 UI/UX 冻结基线 |

修改 Collector 前先比较 `collector-baseline-v0.2`；修改正式数据/Query 策略前先比较 `reference-data-v0.6`；修改当前整体系统前先比较 `product-workspace-v0.7`。不要补造 v0.1 Git 历史。

## 4. Project Goal

系统面向淘宝上的食药同源及保健食品相关商品，自动完成商品发现、页面证据采集、图片 OCR、配置化功效表达匹配和结果组织，为人工复核以及后续抽检候选筛选提供可追溯线索。

当前完整流程是：

```text
MonitorTarget/关键词
  → 淘宝搜索
  → 候选商品及命中来源
  → 前 N 件详情采集
  → DOM 正文与详情原图
  → PaddleOCR
  → 功效规则分析
  → Evidence
  → 人工复核
  → output 文件证据 + SQLite 索引 + Web 展示
```

## 5. Explicit Non-goals

当前明确不做或尚未具备：

- 不认定商品违法、违规或构成虚假宣传；
- 不验证页面功效表达是否真实；
- 不通过网页、图片或 OCR 检测食品中的实际非法添加物；
- 不替代实验室检验、执法调查或专业人员判断；
- 不破解淘宝验证码，不自动绕过登录、滑块或平台安全控制；
- 不承诺大规模、高并发、无人值守或长期稳定爬取；
- 不支持多用户、权限、分布式任务队列、数据库服务集群；
- 不把 `development_seed` 当作官方食药同源完整目录；
- 不把搜索卡片的 `region` 当作商品声明产地或卖家注册地。

## 6. Business Boundary

系统输出的是“风险线索”，核心对象是可回溯的 Evidence。规则命中只说明某个页面范围内的文本出现了配置词库中的表达。最终页面必须使用“检测到功效相关表达”“建议人工复核”等措辞。

证据来源必须区分：

- `seller_managed`：商品标题、当前商品 DOM 正文、当前商品详情图 OCR；可作为商家管理页面内容的主要线索，但仍需核对语境；
- `user_generated`：用户评价、用户问答；只能作为辅助信号，不能自动归因为商家承诺；
- `excluded_other_product`：推荐商品区域；不得计入当前商品的 `detected_effects` 或 Evidence。

即使 Evidence 全部来自 `seller_managed`，系统也不能直接给出法律结论。实验室检测与网页证据属于不同证据层级：本系统只处理公开页面内容，不产生理化或成分检验数据。

## 7. Current Architecture

系统刻意保持轻量：

1. `src/local_api.py` 用标准库 `ThreadingHTTPServer` 提供静态页面和 JSON API；
2. `src/task_runtime.py` 维护一个受控后台 worker thread，同一时间只运行一个 Pipeline；
3. `src/main.py` 的 `StandalonePipeline` 仍是采集、OCR、分析的唯一主链；
4. Quick Task 直接调用 `LiveSearchCollector`；Monitor Task 只在搜索前增加 `DiscoveryCoordinator`；
5. `output/<run_id>` 保存原始事实、实时状态和导出结果；
6. `data/app.db` 保存可查询、可重建的业务索引与人工复核状态；
7. `web/` 是无框架的 HTML/CSS/JavaScript 单页应用，通过 API 读取真实数据。

没有 Flask、FastAPI、Vue、React、Celery、Redis 或消息队列。当前规模不需要这些依赖；除非出现明确需求，不要为了“架构正规”替换现有主链。

## 8. Main Modules

| 文件 | 职责 | 修改风险 |
| --- | --- | --- |
| `main.py` | 根入口，转发到 `src.main.main` | 低 |
| `src/main.py` | `PipelineOptions`、`StandalonePipeline`、状态、断点与批次输出 | 高，贯穿全链 |
| `src/taobao_live.py` | 浏览器启动、登录/验证检测、真实搜索、卡片解析、Diagnostics | 很高，Collector 核心 |
| `src/phase1_experiment.py` | 详情打开、滚动、DOM/Network/截图、原图与 meta | 很高，Collector 核心 |
| `src/phase2_ocr.py` | PaddleOCR runtime、图片选择、逐图 OCR、manifest/report | 高，耗时链路 |
| `src/phase3_analysis.py` | 文本归属、规则命中、推荐区排除、Evidence 与报告 | 高，业务口径 |
| `src/phase4_search_snapshot.py` | 保存的真实搜索页 fixture 解析 | 中，离线回归辅助 |
| `src/phase5_batch.py` | 批次记录、CSV/JSON/Markdown 汇总 | 中 |
| `src/web_contract.py` | `web_snapshot.json` 数据契约、状态中文展示 | 高，前后端契约 |
| `src/runtime.py` | 时间、哈希、原子 JSON、run logger | 高，横切基础设施 |
| `src/task_runtime.py` | Web 任务校验、后台线程、单任务保护、恢复与状态装饰 | 高 |
| `src/data_store.py` | SQLite schema、run 幂等导入、查询和人工复核 | 高 |
| `src/discovery.py` | 多 Query 串行发现、跨 Query 去重、CandidateHit | 高，v0.5 核心 |
| `src/search_query_validation.py` | 低频 search-only Pilot 编排与验证结果记录 | 中，仅验证搜索策略，不代替完整 E2E |
| `src/local_api.py` | 静态文件、本地 API、路径隔离、组件装配 | 高 |
| `web/index.html` | 单页视图结构与 CSS/ES Module 入口 | 中 |
| `web/app.js` | 初始化、页面切换、全局事件和模块协调 | 中 |
| `web/js/api.js` | 前端 API 请求统一封装 | 中，高复用边界 |
| `web/js/state.js` | 跨页面状态与 Product 查询状态 | 中 |
| `web/js/utils.js` | 转义、日期、URL、资源路径等共享纯工具 | 中 |
| `web/js/pages/overview.js` | 总览统计、地图、最近任务/商品 | 中 |
| `web/js/pages/products.js` | Product API 筛选、分页、列表状态与展示 | 高，商品工作台核心 |
| `web/js/pages/judgment.js` | 商品快照、图片/OCR、Evidence 与人工复核 | 高，业务口径 |
| `web/js/pages/tasks.js` | Quick/Monitor 表单、任务状态、恢复与日志 | 高，任务交互 |
| `web/css/base.css`、`components.css`、`pages.css` | 基础布局、通用组件和页面样式 | 低至中 |

## 9. Runtime Workflow

### 9.1 Quick Task

`POST /api/tasks` 提交 `task_type=quick`、`keyword`、`candidate_limit`、`detail_limit`。`TaskManager` 创建 run 目录和 `task_request.json`，写入初始 `web_snapshot.json`，随后在后台线程实例化 `StandalonePipeline`。

Pipeline 启动项目 Chrome，先访问淘宝首页建立正常页面会话，再从可见搜索框提交关键词。`LiveSearchCollector` 提取卡片，按商品 ID 去重并生成 Search Diagnostics。前 `detail_limit` 件进入 Phase 1；完成浏览器阶段后顺序执行 PaddleOCR 与规则分析，最后写批次输出并索引 SQLite。

### 9.2 Monitor Task

`POST /api/tasks` 提交 `task_type=monitor`、`target_id`、`per_query_candidate_limit`、`detail_limit`。服务从 SQLite 读取启用的 MonitorTarget，并且只执行 `enabled=true`、`validation_status=search_validated` 的有序 SearchQuery，随后把完整快照冻结到 `task_request.json`。

`DiscoveryCoordinator` 串行调用既有 `LiveSearchCollector`。每个 Query 有独立目录：

```text
output/<run_id>/search_queries/<order>_<query_id>/search/
```

最终在 `output/<run_id>/search/` 写兼容旧主链的合并候选和 `discovery_summary.json`，之后仍由同一个 `StandalonePipeline` 处理详情、OCR 和分析。

### 9.3 状态与恢复

主要商品状态为 `pending_detail_collection`、`collecting_detail`、`detail_collected`、`processing_ocr_analysis`、`success`、`failed_collection`、`failed_processing`。

Web 任务阶段包括 `initializing`、`searching`、`collecting_details`、`processing_ocr_analysis`、`manual_action_required`、`completed`、`completed_with_errors`、`failed`、`interrupted` 等。前端每 2 秒轮询活动任务，错误后退到 4 秒。

恢复任务需要该 run 同时具有 `run_config.json`、`search/search_candidates.json` 和 `batch_state.json`，且阶段属于可恢复状态。服务重启会把未终结的 Runtime 任务标记为 `interrupted`，而不是假定它仍在运行。

## 10. Core Data Model

核心关系：

```text
MonitorDataset 1 ── N MonitorTarget 1 ── N SearchQuery
Task          1 ── N CandidateHit N ── 1 Product
Task          1 ── N ProductSnapshot N ── 1 Product
ProductSnapshot 1 ── N Evidence
ProductSnapshot 1 ── 1 Review
```

- `Product` 表示稳定的淘宝商品 ID，不承载某次页面内容；
- `ProductSnapshot` 表示某个 Task 中该商品的采集与分析状态；
- `Evidence` 和 `Review` 都属于 Snapshot，因为页面、规则和人工结论具有时间性；
- `CandidateHit` 表示检索来源，不等同于详情已采集；
- `MonitorDataset` 保存 development/reference 数据集身份、版本和来源；`MonitorTarget` 保存目标级来源并关联所属数据集；
- Monitor 任务可能有 19 个候选，但只有前 2 个 Snapshot 完成详情/OCR，其余保持待采集状态，这是正常且必须如实展示的状态。

## 11. SQLite Tables

当前 `SCHEMA_VERSION = 4`，旧 version 2/3 数据库通过项目现有轻量 schema 机制升级。表如下：

| 表 | 关键字段/约束 | 用途 |
| --- | --- | --- |
| `tasks` | `task_id` PK、`task_type`、`target_id`、limits、stage、run_path | 任务索引 |
| `products` | `taobao_product_id` PK | 稳定商品身份 |
| `product_snapshots` | `snapshot_id` PK、`UNIQUE(task_id, product_id)` | 某任务的商品页面与分析快照 |
| `evidence` | `evidence_id` PK、`UNIQUE(snapshot_id, ordinal)` | 结构化证据及来源 |
| `reviews` | `snapshot_id` PK、状态 CHECK | 人工复核最新状态/备注 |
| `monitor_datasets` | `dataset_id` PK、version、status、source、timestamps | development/reference 数据集 provenance |
| `monitor_targets` | `target_id` PK、`dataset_id`、目标级来源、启用状态 | 标准监测对象 |
| `search_queries` | `query_id` PK、`UNIQUE(target_id, query_text)`、order、query_source、validation_status、query_note | 对象下的有序搜索表达与验证依据（SQLite schema v4） |
| `candidate_hits` | `hit_id` PK、`UNIQUE(task_id, product_id, query_id)` | Query 对商品的命中来源 |

人工复核状态只允许：`pending`、`recommend_follow_up`、`no_further_action`。

数据库文件是本机运行数据，不提交 Git。重建命令：

```powershell
.\.venv\Scripts\python.exe -m src.data_store `
  --output-root output `
  --database data\app.db
```

原图、HTML、Network response body、OCR 全文和日志不能塞进 SQLite；它们继续由文件系统保存。不要把可重建索引误当成原始证据唯一副本。

## 12. Main APIs

服务默认只绑定 `127.0.0.1:8765`。

| Method | Path | 用途 |
| --- | --- | --- |
| GET | `/api/health` | 服务健康检查 |
| GET | `/api/runs` | 含有效 `web_snapshot.json` 的 run 列表 |
| GET | `/api/runs/{run_id}` | 读取 run 的 Web Snapshot |
| GET | `/api/runs/{run_id}/files/{path}` | 读取 run 内图片、OCR、导出和报告 |
| GET | `/api/tasks` | 任务列表与当前活动任务 ID |
| POST | `/api/tasks` | 创建 Quick 或 Monitor 完整任务，返回 202 |
| GET | `/api/tasks/{task_id}` | 轮询任务状态与结果 |
| POST | `/api/tasks/{task_id}/resume` | 恢复具备安全断点的任务 |
| GET | `/api/tasks/{task_id}/candidate-hits` | 查看 Monitor 检索来源 |
| GET | `/api/monitor-targets` | 启用的监测对象列表 |
| GET | `/api/monitor-targets/{target_id}` | 对象及其有序 Query |
| GET | `/api/products` | 商品索引；支持 `query`、`review_status`、`effect`、`task_id`、`target_id`、`page`、`page_size` |
| GET | `/api/products/{product_id}/snapshots` | 商品历次快照 |
| GET | `/api/snapshots/{snapshot_id}` | 快照、Evidence 与 Review |
| PUT | `/api/snapshots/{snapshot_id}/review` | 更新人工复核状态和备注 |

`GET /api/monitor-targets` 与单对象接口保持原路径；每个 target 现在额外返回 `dataset_id`、`dataset_version`、`dataset_status` 和完整 `dataset` provenance，不需要新增 API。启动服务或运行 `src.data_store` 时，`--monitor-config` 可以重复指定；未指定时依次导入 development 与 reference 配置。

`GET /api/products` 默认 `page=1`、`page_size=20`，单页最大 100，并返回 `count`、`total`、`page`、`pageSize`、`totalPages`。无 `task_id`/`target_id` 时每个 Product 返回全局最新 Snapshot；有 `target_id` 时返回每个 Product 在该 Target 范围内的最新 Snapshot；`task_id` 与 `target_id` 同时出现时按 AND 过滤。商品项中的 `targetId`、`targetName` 来自 Snapshot 所属 Task；Quick Task 两字段为 `null`。

Quick 创建示例：

```json
{"task_type":"quick","keyword":"酸枣仁","candidate_limit":10,"detail_limit":2}
```

Monitor 创建示例：

```json
{"task_type":"monitor","target_id":"dev-food-medicine-suanzaoren","per_query_candidate_limit":10,"detail_limit":2}
```

第一版公开 limit 只接受 1—50；Quick 的 `detail_limit` 不能大于 `candidate_limit`。有活动任务时再次创建会返回 409 和 `activeTaskId`。静态文件与 run 文件路径都有目录穿越校验，不要放宽。

## 13. Frontend Structure

`web/index.html`、`web/app.js`、`web/js/` 和 `web/css/` 组成无构建流程的原生 ES Modules 单页界面。页面包括：

- 风险总览；
- 商品监测；
- 风险研判；
- 采集任务；
- 基础词库占位；
- 统计分析占位。

`app.js` 只负责初始化、页面切换、全局事件和必要协调；API、共享状态/工具及 overview/products/judgment/tasks 页面职责已拆出。没有引入 npm、框架或构建步骤。

商品监测工作台以 `GET /api/products` 为唯一列表数据源，把 `target_id`、`query`、`review_status`、`effect`、`page`、`page_size` 发送到服务端。`productQuery` 状态保存筛选条件、页码、每页数量、总数、总页数、加载/错误状态和当前 items；筛选变化与重置均回到第 1 页。MonitorTarget 下拉来自 `GET /api/monitor-targets`，展示名称并提交 `target_id`。UI 必须用 API 返回的数据集状态区分同名对象：`verified_reference` 显示“正式”，`development_seed` 显示“开发”，当前酸枣仁分别显示为“酸枣仁 · 正式”和“酸枣仁 · 开发”。旧的 current run + history run 浏览器端拼接及完整过滤已删除；run snapshot 仍服务于总览、任务进度和单 run 展示。

采集任务页继续支持 Quick/Monitor 两种模式，并将真实当前任务、新建表单与历史任务明确分区。商品详情可读取对应历史 run 的真实快照、原图、OCR 和 Evidence，人工复核通过 PUT API 持久化；Evidence 必须继续显示 `seller_managed` / `user_generated` 来源边界。中国地图使用 `web/data/china-provinces.geojson`，标题明确为“搜索页地区分布”。当前统计受数据量和字段语义限制，不得把搜索卡片地区渲染成“产地风险分布”结论，也不得制造不存在的统计数字。基础词库和统计分析仍是明确的后续版本规划页。

v0.7-C2 只修改 presentation：Dashboard 的剩余候选称为“候选未深采”；历史任务的 `1/5` 表示详情采集数量而不是总体完成率；task 名称与 `task_id` 分层；已知 `stop_reason` 显示中文且未知值回退原值；collapsed Sidebar 隐藏分组标签；Product Workspace 的 CSV/JSON/报告入口明确指向“当前任务”。这些语义不得重新改回误导性总体进度。

## 14. MonitorTarget / SearchQuery / CandidateHit Mechanism

当前开发种子在 `config/monitor_targets.development.json`：一个 `酸枣仁` MonitorTarget，两个 Query：`酸枣仁` 和 `酸枣仁茶`。它始终标记为 `development_seed`。

正式入口为 `config/monitor_targets.reference.json`。当前为 `verified_reference`、版本 `2024.08`，按首次纳入来源收录国家卫生健康委 2002 年 87 项、2019 年 6 项、2023 年 9 项和 2024 年 4 项，共 106 个 MonitorTarget；2025 年官方答复用于核验总数。2019 年新增 6 项仅作为香辛料和调味品使用。系统不会把 development seed 静默升级或转移到正式数据集。

v0.6-C1 只选择酸枣仁、茯苓、龙眼肉（桂圆）、当归、铁皮石斛、化橘红 6 个 Pilot，共执行 9 次真实淘宝 search-only。最终启用前五者；当归虽可召回，但结果几乎全为中药材/饮片且有官方食用限制，继续停用。其余 100 个正式对象仍 `enabled=false`、`queries=[]`。完整结果见 `docs/search_query_pilot_v0.6-c1.md` 和两个对应 output run。

最终验收 run `20260903T014401_task` 从 Web 选择正式 `verified_reference` 铁皮石斛创建：5 个 CandidateHit、5 个唯一候选、1 件详情、31 张原图、26 张 OCR、1 件分析、0 Evidence、0 失败/重试。它证明正式 reference 对象能够进入完整系统；Evidence 为 0 是如实分析结果，不是验收缺陷。

机制约束：

1. Query 只执行 `enabled=true` 项，按 `order`、再按 `query_id` 稳定排序；
2. 多 Query **串行**，避免并发争用同一浏览器上下文并降低平台压力；
3. 每个 Query 复用冻结的 `LiveSearchCollector`，保留独立 Search Diagnostics；
4. 对每个有效商品卡片写 CandidateHit；
5. 合并候选按 `product_id` 去重，第一次出现决定其主候选位置；
6. 合并后的 rank 是确定性的：Query 顺序优先，Query 内 rank 次之；
7. 同一商品被多个 Query 命中时，合并列表只有一项，但 CandidateHit 保留多项；
8. 只有前 `detail_limit` 个唯一候选进入高成本详情/OCR链；
9. 配置快照被冻结到任务请求，不能运行中悄悄改变既有任务含义；
10. `search/search_candidates.json` 维持旧 Pipeline 兼容，`discovery_summary.json` 提供 Monitor 解释数据。
11. 正式 Query 不能由模型按常识批量生成或启用；必须记录来源、场景依据、真实搜索验证状态和证据 run。

不要把 CandidateHit 当作风险证据；它只解释商品为何被搜索召回。

## 15. Important Config Files

### `config/effect_keywords.json`

当前 version 1，包含助眠、降压、降脂、减脂、男性相关五类字面词。命中只触发人工复核建议。修改后会改变分析结果，必须补规则测试并记录 config hash；不要添加没有业务依据的词来“提高命中数”。

### `config/monitor_targets.development.json`

当前 schema version 2、`dataset_status=development_seed`。只能作为开发验证样本，不能在论文或 UI 中称为官方完整目录。

### `config/monitor_targets.reference.json`

正式 reference dataset 入口。当前 `dataset_status=verified_reference`、`dataset_version=2024.08`、共 106 项，每项均保存首次纳入它的国家卫生健康委文件名称、引用和日期。6 个 Pilot 共配置 9 个已验证 Query，5 个对象启用；其余 100 项无 Query 且停用，当归虽有已验证 Query 也因商品场景与官方适用边界继续停用。开发种子仍单独保存在 development 文件中。

### `.gitignore`

必须继续排除 `.venv/`、`.browser-profile/`、`output/`、`data/*.db`、缓存、OCR/Paddle 模型、日志和本地环境变量。真实证据与 profile 含运行数据/登录状态，不能误提交。

### Requirements

- `requirements-phase1.txt`：Playwright、Pillow；
- `requirements-ocr.txt`：PaddlePaddle 3.2.0、PaddleOCR 3.x、Pillow；
- `requirements.txt`：聚合前两者。

## 16. Tests

当前共有 137 项 `unittest`。v0.6 稳定基线为 118 项；v0.7-A 增加 6 项后端查询测试；v0.7-B 增加 9 项前端结构/契约测试；v0.7-C 增加 3 项前端验收测试；v0.7-C2 增加 1 项语义契约测试。现有 13 项前端测试覆盖模块与 CSS 路径、JS 语法、Product API 参数、筛选/分页/空结果、Quick/Monitor 请求、复核状态、设计令牌、响应式规则、显式规划状态、同名 MonitorTarget 数据集标识及 C2 语义。2026-09-04 C2 收口时只执行一次全量回归，结果为 `Ran 137 tests in 6.910s ... OK`。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

各稳定 tag 的测试方法数量可由 Git 直接核查：v0.2 为 48、v0.3 为 58、v0.4 为 75、v0.5 为 81。

覆盖重点包括：

- 真实保存的搜索页/分析 fixture；
- 搜索去重、字段补全、代理、CDP 参数、Diagnostics 与 Selector Health；
- 详情图片 MIME、尺寸、正文边界和滚动停止；
- OCR 图片选择、置信度结构和提示词；
- seller/user/recommendation 内容归属；
- candidate/detail limits、断点与中断；
- Web Snapshot；
- 任务参数、单活动任务、失败、恢复和服务重启；
- SQLite 初始化、幂等导入、多快照、Evidence、Review 持久化；
- Monitor 配置顺序、CandidateHit 幂等/重开、跨 Query 去重；
- development/reference 数据集状态、来源 provenance、非法正式来源拒绝、target/query 唯一与关联、SQLite v2→v3 升级；
- API 路径安全和前后端业务接口。

测试默认离线，不应在单元测试中访问淘宝。修改 Collector 核心时，离线测试通过仍不等于真实页面通过，必须增加最小真实 smoke/E2E。

## 17. Verified Real Runs

| Run | 类型 | 可证明的事实 |
| --- | --- | --- |
| `20260817T171318` | Codex Browser 辅助页面侦察 | 单商品 DOM/Network/Screenshot 路线；17 张正文原图；不是 standalone 验收 |
| `20260817T181659_batch` | 早期真实批次串联 | 20 候选中 2 件具有详情、OCR、分析与 Evidence；不能证明实时自动搜索全链 |
| `20260828_cdp_smoke2` | standalone 小批量详情 | 46 去重、入选 10、详情 10、原图 176；仅 1 件完整分析 |
| `20260901_collector_v02_test_a_retry1` | v0.2 采集测试，跳过 OCR | 20 候选、3 详情、44 原图 |
| `20260901_collector_v02_test_b` | v0.2 候选/详情测试，跳过 OCR | 请求 50、实际 46 去重、5 详情、76 原图；一次广告跳转超时后重试成功 |
| `20260901_collector_v02_e2e` | v0.2 CLI E2E | 10 候选、2 详情、25 原图、23 OCR、2 分析、有 Evidence、0 失败，约 7:18 |
| `20260902T005526_task` | v0.3 Web E2E | Web 创建；10 候选、2 详情、37 原图、30 OCR、2 分析、有 Evidence、0 失败，约 11:49 |
| `20260902T192913_task` | v0.5 Monitor Web E2E | Web 创建；2 Query、20 hits、19 unique、2 详情、32 原图、27 OCR、2 分析、8 Evidence、0 失败，约 9:18 |
| `20260903T014401_task` | v0.6 正式 Reference Monitor Web E2E | Web 选择 verified 铁皮石斛；1 Query、5 hits/5 unique、1 详情、31 原图、26 OCR、1 分析、0 Evidence、0 失败/重试，约 10:07 |

`20260902T192644_task` 是受限执行环境阻止 Playwright 创建子进程的失败预检，不是淘宝 E2E。详见 `task_runtime_error.json`。

## 18. Known Limitations

- 淘宝页面和风控是外部不稳定依赖；登录有效也不保证搜索页不会再次要求验证。
- `.browser-profile` 与用户日常 Chrome profile 隔离，日常 Chrome 已登录不能作为项目已登录的证据。
- 搜索 Selector 使用观察到的动态类名片段，Selector Health 只发现覆盖率下降，不能自动选择新 DOM。
- 当前真实单 Query 最大观察为 46 个去重候选，不存在 100 商品能力证据。
- 详情模板仍以当前淘宝/天猫样本为主；找不到详情容器时的兜底路径真实覆盖不足。
- 广告跳转 URL 可能超时；当前逐商品有限重试可以恢复部分瞬时错误，但不能保证所有跳转。
- PaddleOCR CPU 处理占大部分运行时间，首次运行还可能下载模型；没有 GPU 或批量性能承诺。
- OCR 的成功数是成功处理的候选详情图数，不等于所有网页文字都被识别。
- 规则是字面匹配，没有否定、语境、同义隐喻或模型级判断；词库质量尚未系统评估。
- 人工复核只保存一个最新状态和备注，没有审核人、历史版本或审计日志。
- 没有任务取消；人工验证仍需在服务终端确认；崩溃恢复依赖已有断点文件。
- API 没有登录鉴权，但默认只监听回环地址；不要未经安全设计直接暴露到局域网/公网。
- Product API 没有商品列表缩略图字段，商品表使用中性占位；不得为视觉完整度伪造商品图。详情页仍读取历史 run 的真实原图。
- 1080px 紧凑桌面下商品表通过横向滚动保持字段可读；本轮没有承诺手机端完整适配。
- 基础词库与统计分析仍为规划页，不具备 CRUD、图表或分析能力。
- MonitorTarget 下拉只展示既有 API 返回的 enabled target，不得把其余正式对象误解为已经具备运行资格。

## 19. Technical Debt

- `ThreadingHTTPServer`、后台 daemon thread 和进程内锁只适合单机进程；多进程时无法保证唯一活动任务。
- `web_snapshot.json` 与 SQLite 同时承载状态展示，虽有明确主次，但仍需维护字段映射一致性。
- SQLite schema 通过 `CREATE TABLE IF NOT EXISTS` 和少量 `_ensure_column` 演进，还没有正式 migration framework。
- Review 只有最新状态，无历史审计；将来若进入真实监管流程必须重新评估。
- Monitor config 通过启动时导入 SQLite，没有 CRUD 和版本管理页面。
- 正式 reference 文件已有 106 项，但只验证了 6 个 Pilot；5 个对象具备 Monitor Task 资格。铁皮石斛已完成正式 verified target 的详情/OCR/分析 Web E2E，其余 4 个已启用正式对象没有逐一做同等 E2E；剩余 101 项（含停用的当归）不具备直接 Monitor 资格。
- 多 Query 仍把所有唯一候选按固定 first-hit 顺序送入详情，没有质量评分、地区平衡或随机抽样。
- 页面结构诊断有覆盖率告警，但缺少详情模板分型、选择器版本和自动回归样本管理。
- 历史 run 的字段存在版本差异，导入层做兼容；删除旧兼容逻辑前必须用保留 run 回归。
- `docs/output_inventory.md` 生成于较早阶段，尚未覆盖全部 v0.5—v0.7 状态；后续如整理证据清单应按真实 output 更新。

## 20. Requirement Backlog

以下是 v0.7 之后仍未实现的事项：

| ID | 需求 | 关键边界 |
| --- | --- | --- |
| `GEO-01` | 商品页面声明产地 | 必须记录字段来源和页面证据，不能与发货地混同 |
| `GEO-02` | 卖家所在省市 | 需确认页面/店铺信息来源、缺失率和更新时间 |
| `GEO-03` | 后续地区均衡选择 | 应建立在 GEO-01/GEO-02 语义明确后，不能直接使用现有 `region` 替代 |
| `INSPECTION-01` | 非法添加补充检验方法标准知识库 | 仅记录需求；未建设数据，不得创建假知识库 |
| `INSPECTION-02` | 风险线索与目标化合物关联 | 仅记录需求；不得写死“功效→化合物”映射 |
| `INSPECTION-03` | 目标化合物与检验方法/标准关联 | 仅记录需求；需要可核验的标准来源与版本 |
| `INSPECTION-04` | 商品检测建议生成 | 仅记录需求；没有可靠关联数据前不得生成建议 |
| `INSPECTION-05` | 结果增加产品名、链接、可能风险、建议检测成分和相关标准 | 仅记录需求；当前 UI 不显示不存在的字段或空标准卡片 |
| `SESSION-01` | 登录/人工验证体验 | 保持人工处理边界，减少对终端 Enter 的依赖 |
| `TASK-01` | 安全任务取消 | 要处理浏览器、OCR、状态原子化与可恢复性 |
| `QUERY-02` | 后续分批扩大正式 SearchQuery | 按业务需要先评估产品场景，再设计和真实验证下一批；禁止按常识批量扩词或用功效词改变候选池 |
| `RISK-01` | 风险识别质量评估与提升 | 先建设人工标注样本和指标，再讨论复杂模型 |
| `REVIEW-01` | 复核历史/审计 | 当前只有最新状态，未来按真实业务需求设计 |

## 21. Do Not Break / Stable Baselines

以下行为是当前核心资产：

1. 关闭 Codex 后，项目代码可在普通终端独立启动浏览器并完成链路；
2. 登录/验证码只允许人工处理，程序不绕过平台控制；
3. 使用项目专用 `.browser-profile`，不要默认接管用户日常 Chrome 数据目录；
4. 详情图片归属以当前商品 DOM 容器为主，Network 只补取/保存原始响应，Screenshot 只作上下文证据；
5. 不用固定 70%/80% 页面比例作为主要滚动终点；详情容器稳定边界优先；
6. Network 图片不能不经 DOM 归属过滤直接送 OCR，早期真实样本中 108 个资源只有 17 个匹配正文；
7. 推荐商品内容必须排除；seller-managed 与 user-generated 必须分开；
8. `candidate_limit` 和 `detail_limit` 必须保持独立语义；
9. 每个 Query 必须保留独立 Diagnostics，跨 Query 去重后仍保留全部 CandidateHit；
10. Monitor 合并顺序必须确定、可复现；不要在没有需求时改成并行或随机；
11. `output` 是原始证据主存储，SQLite 是可重建业务索引；不要反转两者角色；
12. Evidence/Review 属于 ProductSnapshot，不能直接提升为 Product 的永久属性；
13. 人工复核不能被历史 run 重导入覆盖；
14. 活动任务单例与 HTTP 409 保护不能移除，除非先实现真正的资源隔离/队列；
15. 实时 JSON 要原子写入，Windows 文件占用重试逻辑不能无验证删除；
16. `/api/runs/.../files/...` 的路径穿越保护和服务回环绑定不能放宽；
17. 页面和报告不得使用“违法”“非法添加已检出”等超出证据的结论。

Collector 核心改动至少要：运行全部离线测试、核查保留 fixture、执行最小真实淘宝 E2E、对比 Diagnostics/原图/OCR/Evidence，并说明相对 `collector-baseline-v0.2` 的行为变化。

## 22. How a New AI Should Inspect the Project Before Modifying Code

新 AI 必须按以下顺序工作，不要仅凭 README 或旧对话猜测：

1. 运行 `git status --short --branch`，确认分支、用户未提交改动和工作树边界；
2. 运行 `git log --oneline --decorate -10` 与 `git tag -n`，确认当前 HEAD 和六个稳定基线；
3. 阅读 `PROJECT_STATUS.md`、本文件、`docs/DEVELOPMENT_HISTORY.md`、`docs/output_inventory.md`；
4. 阅读需求涉及模块及对应测试，不先做大规模重构；
5. 检查 `config/effect_keywords.json`、`config/monitor_targets.development.json` 和 `config/monitor_targets.reference.json` 的来源边界；
6. 优先对照 `output/20260903T014401_task` 的 `task_request.json`、`run.log`、`search/discovery_summary.json`、Search Diagnostics、`products.json`、`web_snapshot.json` 和商品 `analysis.json`；需要多 Query 样本时再看 `output/20260902T192913_task`；
7. 若涉及 Collector，再检查 `collection_experiment.md`、`20260901_collector_v02_test_b` 与 `collector-baseline-v0.2`；
8. 运行当前 137 项离线测试，不能把“代码能导入”当作验收；
9. 明确写出本轮改动属于“已实现”“离线验证”还是“真实验证”；
10. 只做需求内最小改动，保护用户已有运行数据和未提交文件；
11. 需要真实淘宝验证时使用普通本地终端/有权创建子进程的环境，避免把 `[WinError 5]` 误判成平台风控；
12. 遇到登录或验证，等待用户处理；不得尝试验证码绕过、批量账号或规避平台安全机制；
13. 修改后先离线回归，再决定是否需要最小真实 E2E；没有真实 run 就明确写“未充分真实验证”；
14. 最终报告列出修改文件、测试、真实 run、失败/重试和遗留风险，不能只写“已完成”。

常用启动命令：

```powershell
# 本地 Web、API、SQLite 索引和任务 Runtime
.\.venv\Scripts\python.exe -m src.local_api --output-root output --port 8765

# Quick CLI 完整链路示例
.\.venv\Scripts\python.exe main.py `
  --keyword 酸枣仁 `
  --candidate-limit 10 `
  --detail-limit 2 `
  --browser-mode cdp `
  --direct-browser
```

注意：本地服务默认启用 `--direct-browser`，只让项目启动的浏览器绕过 Windows 系统代理；如果当前网络访问淘宝必须经过代理，应显式调整 `--no-direct-browser` 或 `--browser-proxy`。不要改动 Codex 或其他应用的代理设置。
