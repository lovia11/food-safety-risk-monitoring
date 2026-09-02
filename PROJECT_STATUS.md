# 项目当前状态

更新时间：2026-09-02

当前版本：v0.5（Monitoring & Discovery Foundation）

当前分支：`main`

当前功能基线提交：`2ffafd749cd20dcdde0346f953c6e8e9a9c67472`（`Establish Monitoring Target and Discovery Foundation v0.5`）
稳定标签：`collector-baseline-v0.2`、`task-runtime-v0.3`、`data-review-v0.4`、`monitoring-discovery-v0.5`

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
| 风险总览、商品监测、风险研判、采集任务 Web 页面 | 已接入真实数据 | `web/` |

当前测试集共有 81 项，2026-09-02 在 v0.5 功能基线及其 documentation-only 后继工作树上执行 `python -m unittest discover -s tests -q`，结果为 `81/81 OK`。仓库实际 HEAD 可用 `git rev-parse HEAD` 查看；文档提交不构成新业务版本。

## 3. 当前架构

### 3.1 运行链路

`src/local_api.py` 使用标准库 `ThreadingHTTPServer` 同时提供静态 Web 页面和本地 API。Web 创建任务后，`TaskManager` 在受控后台线程中调用已经冻结验证的 `StandalonePipeline`，HTTP 请求无需等待整个采集过程结束。

Quick Task 直接将一个关键词交给 `LiveSearchCollector`。Monitor Task 先由 `DiscoveryCoordinator` 按配置顺序串行执行多个 `SearchQuery`，再合并候选并调用同一个详情/OCR/分析主链，没有重写 Collector。

任务实时状态继续以 `output/<run_id>/web_snapshot.json` 为稳定契约，前端轮询读取。关键 JSON 使用“临时文件写完后原子替换”；Windows 短暂文件占用时会有限重试，避免 Web 读到半截 JSON。

### 3.2 数据分层

- `output/<run_id>/` 是原始运行事实与可追溯证据的主存储：搜索 HTML/截图/诊断、详情 HTML、Network 响应、原图、OCR、`analysis.json`、日志及批次报告均保留在此。
- `data/app.db` 是可重建的 SQLite 业务索引，当前 schema version 为 2。它保存任务、商品、商品快照、结构化 Evidence、人工复核、监测对象、搜索词和候选命中关系。
- SQLite 不替代原始证据文件。数据库可从历史 `output` 幂等重建，重复导入不会复制记录，也不会覆盖已经保存的人工复核备注。
- `.browser-profile/`、`output/`、`data/*.db`、`.venv/` 与 OCR 模型缓存均不提交 Git。

## 4. SQLite 与核心数据模型

当前表为：

- `tasks`：一次 Quick 或 Monitor 运行；
- `products`：按淘宝商品 ID 维护的稳定商品身份；
- `product_snapshots`：某商品在某任务中的一次页面快照；
- `evidence`：属于某个 ProductSnapshot 的结构化证据；
- `reviews`：属于某个 ProductSnapshot 的人工复核最新状态与备注；
- `monitor_targets`：被监测的标准对象；
- `search_queries`：某 MonitorTarget 下按确定顺序执行的搜索表达；
- `candidate_hits`：某任务中“哪个 Query、以什么排名命中哪个商品”的来源事实。

Evidence 和 Review 归属于 ProductSnapshot，而不是永久归属于 Product。原因是淘宝页面内容、规则结果和人工判断都可能随采集时间变化。同一 Product 可以拥有多个任务快照。

当前本机数据库在本次文档审计时可正常打开，索引了历史 run；表数量会随导入与新任务变化，因此不作为固定产品指标。

## 5. Web 任务运行能力

当前 Web 支持两种任务：

- Quick Task：输入 `keyword`、`candidate_limit`、`detail_limit`；
- Monitor Task：选择 `target_id`，输入 `per_query_candidate_limit` 和 `detail_limit`。创建时会把 MonitorTarget 及有序 SearchQuery 快照写入 `task_request.json`，避免运行中配置变化改变本次任务含义。

任务状态包括搜索、详情采集、OCR/分析、需要人工登录/验证、完成、带错误完成、失败和中断。服务重启时，未结束且由 Runtime 管理的任务会标记为 `interrupted`；具备 `run_config.json`、搜索候选和批次状态的任务可以恢复。

当前只允许一个活动采集任务。第二个创建请求返回 HTTP 409，以防多个任务争用同一个浏览器 profile 和本机 OCR 资源。

## 6. MonitorTarget / SearchQuery / CandidateHit

v0.5 当前使用 `config/monitor_targets.development.json` 中的开发种子：

- MonitorTarget：`酸枣仁`（`dev-food-medicine-suanzaoren`）；
- SearchQuery 1：`酸枣仁`（base）；
- SearchQuery 2：`酸枣仁茶`（product_form）。

该配置明确是 `development_seed`，只用于工程开发与真实流程验收，不是官方完整食药同源目录，也不是最终搜索词体系。

多 Query 按 `order` 串行执行。候选以 `product_id` 跨 Query 去重，首次有效出现决定合并列表顺序；顺序首先由 Query 顺序决定，再由 Query 内排名决定。前 `detail_limit` 个唯一候选进入详情链。即使同一商品被多个 Query 命中，所有来源仍作为多条 CandidateHit 保留，供后续解释召回来源。

## 7. 当前真实验收结果

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
- MonitorTarget 只有开发种子，没有权威完整监测对象数据集和正式维护界面。
- Product 列表 API/前端尚无正式分页；MonitorTarget 维度的商品筛选尚未实现。

## 9. 下一阶段候选事项（尚未实现）

优先级需要在下一轮需求确认后决定，本文件不代表已经排期：

- `GEO-01`：采集商品页面声明产地；
- `GEO-02`：采集卖家所在省市；
- `GEO-03`：候选商品按地区均衡选择；
- `UI-01`：商品监测分页；
- `UI-02`：按 MonitorTarget 筛选商品；
- `UI-03`：整体 UI/UX 优化；
- 改进人工登录/验证的 Session UX；
- 增加安全的任务取消与状态恢复；
- 建立经过来源核验的正式 MonitorTarget 数据集；
- 以标注样本评估并提升 OCR/风险规则质量。

继续开发前应先阅读 `docs/AI_HANDOFF.md` 和 `docs/DEVELOPMENT_HISTORY.md`，并把 `monitoring-discovery-v0.5` 视为当前稳定回退基线。
