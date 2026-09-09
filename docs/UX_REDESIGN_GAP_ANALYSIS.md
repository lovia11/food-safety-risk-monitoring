# UI/UX 正式重构差距分析（Phase 0）

> 状态：Phase 0 设计基线<br>
> 审计日期：2026-09-09<br>
> 工作分支：`ux-redesign-v1`<br>
> 审计 HEAD：`c8d962cfc20dfe7761a74ebea9a45b57fbe68711`<br>
> 基线提交：`Integrate Inspection Recommendation Workflow v0.8-D6`

## 1. 审计范围与结论

本轮只分析现状并形成开发设计，不创建 React 工程，不修改 Python 业务代码、SQLite schema 或现有 `web/`，不启动淘宝、不运行 Collector、不访问外部视觉网站。

审计依据包括：

- `PROJECT_STATUS.md`、`docs/AI_HANDOFF.md`；
- `src/local_api.py`、`src/task_runtime.py`、`src/data_store.py`、`src/web_contract.py`、`src/inspection_runtime.py`；
- 与人工验证直接相关的 `src/taobao_live.py`，以及 Recommendation、Product Context 的现有契约；
- 当前 `web/` 的页面、API client、商品、研判和任务实现；
- 本地 Figma Make 原型的 `package.json`、`src/App.tsx`、`src/index.css`、`src/types.ts`、`src/imports/*`、`vite.config.ts`。

总体结论：后端 D1-D6、Pipeline、任务 Runtime、文件事实源和 SQLite 业务索引都可继续使用。重构不应重写采集或知识算法。目标体验无法只靠换 React 页面完成，至少需要补齐以下四个 P0 后端契约：

1. Web 可用、且不跨线程操作 Playwright page 的人工验证 gate；
2. 与 Review 完全分离的“当前抽检清单成员关系”；
3. 当前清单导出、冻结和历史只读清单；
4. 支撑 Product 一行、多 Snapshot 时间线和真实筛选项的聚合 API。

React + TypeScript + Vite + Tailwind CSS 4 + Lucide React 与当前系统匹配：它能承载多页面状态、Master-Detail、Drawer、typed API 和可维护组件拆分，同时仍可构建为静态文件并由现有 `ThreadingHTTPServer` 服务。无需替换 Python 服务或引入额外状态管理框架。

## 2. 当前技术基线

### 2.1 后端与运行时

| 领域 | 当前实现 | 判断 |
| --- | --- | --- |
| HTTP 服务 | Python 标准库 `ThreadingHTTPServer` | 保留 |
| 任务执行 | `TaskManager` + 单一 daemon worker thread | 保留单活动任务约束 |
| 主业务链 | `StandalonePipeline`、淘宝 Collector、OCR、Phase3、D2-D6 | 冻结复用 |
| 原始事实 | `output/<run_id>/` 下 HTML、图片、OCR、分析和 Recommendation JSON | 保留为事实源 |
| 查询索引 | SQLite `data/app.db`，schema version 7 | 增量升级，不重建 |
| 人工复核 | Snapshot 级 `reviews`，状态为 `pending`、`recommend_follow_up`、`no_further_action` | 原语义保留 |
| Recommendation | 商品目录 `inspection_recommendation.json` | 原样消费，不复制到 SQLite |
| Product Context | 商品目录 `inspection_context.json` + run-scoped PUT API | 原样复用 |

当前工作树没有 `output/` 或本机 `data/app.db`，因此 Phase 0 只依据代码契约、配置和已记录的真实验收结论，不声称本工作树内已有可直接浏览的运行数据。交付体验仍应默认进入商品总览；只有 API 返回 `total=0` 时才进入初始化空状态。

### 2.2 当前 Web

当前 `web/` 是无构建流程的 HTML、分层 CSS 和原生 ES Modules SPA，已经具备：

- 商品服务端分页、关键词、MonitorTarget、Review 和功效筛选；
- Product 全局最新 Snapshot 与 Target 范围内最新 Snapshot 语义；
- 商品历次 Snapshot、Evidence、Review、真实原图/OCR、Recommendation 和 Context 更新；
- Quick/Monitor 任务创建、单活动任务保护、轮询和中断恢复；
- 加载、错误、空状态与 Toast。

但当前一级导航仍是“风险总览、商品监测、风险研判、采集任务、基础词库、统计分析”；默认页是总览；商品详情是独立一级视图；任务表单仍含仅存于 localStorage 的“草稿”；商品表缺少清单状态、历史次数和右侧时间线详情；任务流程仍突出 OCR/原图等技术阶段。

### 2.3 Figma 参考栈与可用部分

Figma Make 原型采用 React 19、TypeScript 5.7、Vite 8、Tailwind CSS 4、Lucide React，并使用浅色工作区、深色 Sidebar、白色 Card、细边框、Split View、Modal/Drawer、状态标签与紧凑表格。

可继承：

- Sidebar 的展开/收缩视觉、三栏导航、工作区比例；
- 排查卡片、流程条、队列与详情的 Master-Detail；
- Evidence-first 的信息节奏、amber 线索卡、green 清单状态；
- 商品总览的列表/右侧详情、抽检清单表格与历史卡片；
- Lucide 图标、轻阴影、圆角、间距层级。

不可继承：

- `INITIAL_TASKS`、`INITIAL_EVIDENCES`、`INITIAL_HISTORICAL_LISTS`、`SAMPLE_PRODUCTS`；
- `included/excluded` 作为 Review 状态的模型；
- 暂停/恢复假逻辑、前端拼 Monitor Query、前端制造任务统计；
- 前端拼接淘宝 URL、硬编码筛选项和 Product Context 选项；
- 虚构成分、方法、适用性、商品图片和外部 Unsplash 图片；
- 导出后把 `included` 改成 `excluded` 的假实现；
- Figma Make 插件、`.figma` 运行设施、原型产生的根目录 `.gitattributes`、`Web Page Layout Design/` 和 Google Fonts 网络导入。这些内容仅作本地视觉参考，不进入设计或实现提交。

## 3. 当前能力与目标能力差距

| 领域 | 当前能力 | 目标能力 | 差距归类 |
| --- | --- | --- | --- |
| 默认入口 | 风险总览 | 商品总览 | 纯前端 |
| 一级导航 | 6 个平级模块 | 商品总览、排查档案、抽检清单 | 纯前端 |
| Sidebar | 仅断点自动收缩 | 智能默认 + 手动选择优先，会话内保持 | 纯前端 |
| 商品列表 | Product 一行、全局/范围内最新 Snapshot | 增加最近排查、清单状态、历史次数、更多筛选 | API + 前端 |
| 商品详情 | 独立详情页，可读历史 Snapshot | 右侧详情、时间线、当前/历史 Snapshot 明示 | API 组合 + 前端 |
| 排查档案 | 任务列表/当前任务分散 | 以一次排查为卡片和二级工作区 | API 汇总 + 前端 |
| 新建排查 | Quick/Monitor API 已有，无服务端名称 | 可选排查名称，高级设置折叠，真实 Query 只读 | 小型 DB/API + 前端 |
| 任务状态 | 技术 stage + web_snapshot 统计 | 业务状态、业务流程条、异常单独显示 | API presentation + 前端 |
| 人工淘宝验证 | 日志触发 Web 状态，但 worker 阻塞 `input()` | Web 确认/周期检测后继续，不碰终端 | P0 后端 + 前端 |
| 工作区队列 | 当前无 ProductSnapshot 队列页面 | 一张卡一个 Snapshot，多 Evidence 聚合 | API + 前端 |
| Evidence | 已区分 seller-managed/UGC，有原图/OCR | 来源分组、主要证据展开、UGC 折叠、反查入口 | 主要为前端 |
| Recommendation | D5 文件和 Web contract 已有 | 按建议/需 Context/其他方法分层 | 前端复用现有契约 |
| Product Context | API 选项真实、PUT 可重算 | 仅在确有 `methods_needing_context` 时显示 | 纯前端 |
| Review | Snapshot 级三种真实状态 | 继续保留，不承担清单成员关系 | 保留 |
| 当前清单 | 不存在 | 全局唯一、Product 唯一、绑定依据 Snapshot | P0 DB/API + 前端 |
| 历史清单 | 不存在 | 导出时冻结 JSON/XLSX，历史只读可下载 | P0 后端 + 前端 |
| Excel 导出 | 仅 run 级 CSV/JSON/Markdown | 服务端 `.xlsx`，导出即冻结并清空当前成员 | P0 后端 |
| 旧 Web 切换 | Python 默认服务 `web/` | 验收后服务 `frontend/dist`，`web/` 暂留回退 | 后期集成 |

## 4. 可原样复用的后端能力

以下能力不需要业务重写：

1. `StandalonePipeline` 及其断点、单商品失败隔离、原子 JSON 写入；
2. `TaskManager` 的单活动任务锁、409 保护、后台 worker、启动时中断标记和 resume；
3. `DataStore` 的 Product/ProductSnapshot/Evidence/Review 关系、幂等 run 导入和按 Product 取最新 Snapshot；
4. MonitorTarget/SearchQuery/CandidateHit 的真实配置、排序、来源和验证状态；
5. `GET /api/monitor-targets` 与目标的真实 SearchQuery；
6. `GET /api/inspection-context-options`、Context 校验、人工 provenance 和重算；
7. D2-D6 输出中的 `risk_findings`、`evidence_qualification`、`suggested_methods`、`methods_needing_context`、`other_known_methods` 和 gaps；
8. run 文件服务的路径穿越保护、回环绑定和真实 `product_url`；
9. seller-managed、user-generated、excluded-other-product 的证据边界；
10. 旧 run 缺 Recommendation 时 `available=false` 的兼容行为。

## 5. 只需前端修改的内容

- 默认路由、一级导航和二级工作区信息架构；
- Sidebar 展开/收缩优先级和 `sessionStorage` 会话保持；
- Figma 视觉落地、字号提升、响应式和独立滚动容器；
- Evidence 分组、默认展开层级和真实资产查看；
- Recommendation 的用户语言、方法分层和 Knowledge Gap 空状态；
- Context 表单按需显示；
- Filter、Table、Drawer、Timeline、Toast、轻量导出确认；
- 禁用词和克制色彩规则；
- 不从商品 ID 构造 URL，不在浏览器生成 Query、统计、成分或方法。

## 6. 必须新增或扩展的后端能力

### 6.1 P0 必须新增

1. Manual-action gate：worker 可等待 Web acknowledgement，并始终由 worker 自己检查 Playwright page；
2. 当前抽检清单 membership CRUD，且一个 Product 最多一条；另提供应用层人工决策事务，原子协调 Review 与当前 membership；
3. 导出服务：冻结 JSON、生成 XLSX、创建历史清单、清空当前 membership；
4. 历史清单列表、详情和重复下载；
5. Product/Task 列表聚合：清单状态、历史纳入次数、Snapshot 次数、排查业务名称和业务统计；
6. Snapshot 工作区 DTO：组合 SQLite Snapshot/Evidence/Review 与 run 文件中的 assets/Recommendation，不让前端跨多个不稳定契约拼业务结论。

Task/archive summary 至少分别返回 `recommendFollowUpCount`、`noFurtherActionCount`、`currentSamplingItems`。前两项是持久 Review 统计，供档案卡片展示人工处理结果；`currentSamplingItems` 是会在导出后清空的当前关系，只能作为“当前清单中”次级信息。

### 6.2 小型扩展

- `tasks` 增加可选 `display_name` 索引列；用户显式名称同时写入 run 的持久配置事实文件 `task_request.json`，SQLite 不作为唯一事实副本；旧 run 不存在显式名称时由服务端按真实 MonitorTarget 或 keyword 生成 fallback，不引入 Draft 实体；
- 商品查询增加 `sampling_status=current|historical_only|never`、`collected_from`、`collected_to`；`historicalCount` 独立返回，`current` 不排除同时存在历史记录；`task_id` 继续作为采集批次；
- 增加真实筛选选项接口，输出实际任务、风险方向、Review 和 Sampling 枚举；
- `OPTIONS` 增加 `DELETE`，并对新增 JSON 和 XLSX 路径继续执行严格路径校验。

## 7. 推荐数据模型变化

建议一次性把 SQLite 升级到 schema version 8，只增加列和表，不删除、改写既有数据：

### 7.1 现有表增量

`tasks`：

- `display_name TEXT NOT NULL DEFAULT ''`，仅作查询索引。创建任务时的显式 `display_name` 必须同步写入该 run 的 `task_request.json`；导入优先读取该事实文件中的非空显式值，其次保留数据库已有非空 `tasks.display_name`，再按真实 MonitorTarget/keyword 生成 fallback，禁止用缺失或空值覆盖已有显式名称。

### 7.2 当前清单成员

`sampling_list_memberships`：

| 字段 | 约束/含义 |
| --- | --- |
| `product_id` | PK/FK `products`，保证当前清单一件 Product 一条 |
| `source_snapshot_id` | FK `product_snapshots`，加入依据 |
| `source_task_id` | FK `tasks`，冗余索引用，必须与 Snapshot 一致 |
| `added_from` | CHECK：`product_overview` / `inspection_workspace` |
| `added_at` | 服务端时间 |
| `updated_at` | 服务端时间 |

该表只表达“当前是否在清单”，不保存 note、不写 Review、不复制 Recommendation。MVP 唯一人工备注是 Snapshot Review note，历史导出冻结导出时的 Review note。

### 7.3 历史清单元数据与索引

`sampling_lists`：`list_id`、`status(preparing/exported)`、`exported_at`、`item_count`、`snapshot_path`、`workbook_path`、两个 SHA-256、`created_at`、`updated_at`。

`sampling_list_item_index`：`list_id`、`ordinal`、`product_id`、`source_snapshot_id`、`source_task_id`；只用于历史次数、定位和一致性检查，不保存 Evidence 或 Recommendation 正文。只有 `list_id` 稳定归属于 `sampling_lists`；三个来源 ID 是导出时冻结的文本/索引值，不对 `products`、`product_snapshots`、`tasks` 建强制外键。这样即使原 run 或 Snapshot 后续不存在，仍可仅依据冻结 JSON 幂等重建历史索引。

历史完整事实位于：

```text
output/sampling_lists/<list_id>/
  sampling_list_snapshot.json
  sampling_list.xlsx
  evidence/
```

冻结 JSON 深拷贝导出时的商品字段、来源 Snapshot/Task、Evidence、Review、Product Context、Recommendation、清单元数据和免责声明；`evidence/` 至少复制被清单展示引用的主要证据图片/截图。SQLite 只保存索引与路径，符合“文件事实源 + SQLite 索引”。

## 8. Manual-action gate 最小方案

### 8.1 当前问题

`TaskManager` 通过日志 Handler 把阻塞提示映射成 `manual_action_required`，但 `src/taobao_live.py` 随后直接执行 `input()`。因此 Web 只能看见提示，不能解除等待；HTTP 线程也不能安全调用属于 worker 的 Playwright page。

### 8.2 目标结构

新增一个进程内、每个活动任务独占的 `ManualActionGate`，内部使用 `threading.Condition` 或 `Event`，只保存纯数据和唤醒信号：

```text
Collector worker 检测阻塞
  -> gate.request(reason)
  -> Task stage = waiting_for_manual_action
  -> worker 在 gate 中等待 acknowledgement/短周期超时

Web POST acknowledge
  -> HTTP 线程只调用 gate.acknowledge()
  -> 不接触 browser/page

worker 被唤醒
  -> worker 调用 blocker_reason(page)
  -> 已解除：gate.resolve()，继续 Pipeline
  -> 未解除：gate.wait_again()，Web 显示仍需处理
```

状态至少包括：`inactive`、`waiting`、`rechecking`、`resolved`；对外字段包括 `reason`、`requestedAt`、`lastCheckedAt`、`attempt`、`canAcknowledge`。acknowledgement 使用递增 generation，旧请求不能解除新一轮验证。

CLI adapter 仍可使用原 `input()`。Web adapter 注入 gate；两者复用同一个 `blocker_reason(page)`，不改变验证码边界。服务退出时 worker 终止，任务按现有机制变为 `interrupted`；重启后不能伪装为仍持有旧 page。

建议 API：

- `POST /api/tasks/{task_id}/manual-action/acknowledge`；
- `GET /api/tasks/{task_id}` 中增加 `manualAction`；
- 新任务 stage 使用 `waiting_for_manual_action`，读取旧 `manual_action_required` 时兼容映射。

自动周期复检可以由 worker 在 gate 等待超时后执行，例如 3-5 秒一次；不得由 HTTP 轮询线程操作 page。

## 9. Sampling List 最小方案

### 9.1 不变量

- 全系统只有一份当前可编辑清单；
- 当前清单按 Product 唯一；
- membership 必须记录 source Snapshot；
- 历史曾纳入不阻止再次加入；
- Knowledge Gap 或 UGC-only 不阻止人工加入，但 UI 必须明确提示证据边界；
- 移出只删除 membership，不修改 Review、Evidence、Recommendation 或历史；
- 导出不修改 Review；
- 历史清单永远读取冻结 JSON，不重新计算最新 Product/Recommendation/Reference。

工作区队列状态按 Review + 当前 membership 投影：

1. membership 存在 -> “已纳入当前清单”；
2. 无 membership 且 Review=`no_further_action` -> “暂不纳入”；
3. 无 membership 且 Review=`recommend_follow_up` -> “已复核 / 建议跟进，当前未在清单”；
4. Review=`pending` -> “待复核”。

导出清空或单独移出 membership 后，已完成的 Review 保持原值，绝不能重新进入“待复核”队列。筛选与状态标签必须分别表达以上四种业务状态；`historicalCount` 只作历史次数信息，不能替代 Review 状态。

### 9.2 API 最小集合

- `GET /api/sampling-list`：当前清单和计数；
- `POST /api/snapshots/{snapshot_id}/review-decision`：应用层人工决策事务；`recommend_follow_up` 原子保存 Review note 并创建/确认当前 membership，`no_further_action` 原子保存 Review note 并确保当前 membership 不存在；
- `POST /api/sampling-list/items`：仅用于 membership 恢复等独立关系操作，按 Product + source Snapshot 幂等加入，永不写 Review；主界面的“加入抽检清单”不得调用它代替完整人工决策；
- `DELETE /api/sampling-list/items/{product_id}`：单独“移出当前清单”，只删 membership 并返回被移除记录，前端可在 Toast 中用 membership 恢复操作撤销；
- `POST /api/sampling-list/export`：轻量确认后冻结并导出；
- `GET /api/sampling-lists`：历史清单元数据；
- `GET /api/sampling-lists/{list_id}`：冻结详情；
- `GET /api/sampling-lists/{list_id}/download`：重复下载 XLSX。

Sampling repository 永远不隐式写 Review，Review repository 永远不隐式写 membership；跨实体变化只允许由 application/service 在同一后端事务中显式协调。商品总览和排查工作区的“加入抽检清单”都属于明确人工决策，必须形成 `Review=recommend_follow_up`、保存 Review note 并创建/确认 membership；“暂不纳入”必须形成 `Review=no_further_action` 并安全移除已有 membership。React 禁止连续调用两个 mutation 自行承担半成功状态。“移出当前清单”仍只调用 membership API，永远不改 Review。

### 9.3 导出一致性

导出需要进程内 export lock + SQLite `BEGIN IMMEDIATE`。建议使用 `preparing` 两阶段：先冻结待导出成员并写临时 JSON/XLSX，再原子替换为最终文件，最后把历史索引标记为 `exported` 并清除与冻结集合完全一致的当前 memberships。启动时可恢复或清理 `preparing` 记录。这样中途失败时不会把当前清单无声清空。

## 10. API 差距摘要

| API | 当前 | 目标 |
| --- | --- | --- |
| `GET /api/products` | 基础筛选、最新 Snapshot | 加清单状态、历史次数、Snapshot 次数、时间筛选 |
| `GET /api/products/{id}/snapshots` | Snapshot 列表 | 增加清单状态和稳定展示名称 |
| `GET /api/snapshots/{id}` | SQLite Snapshot/Evidence/Review | 增加 assets、inspection、sampling 组合 DTO |
| `GET /api/tasks` | 技术摘要 | 增加可重建 display name、业务状态、持久 Review 统计和当前清单次级计数 |
| `POST /api/tasks` | Quick/Monitor + limits | 增加可选 `name`，不增加 Draft |
| Manual action | 无可操作 API | acknowledge + task manualAction |
| Review decision / Sampling List | 不存在 | 应用层原子人工决策 + 独立 membership/export/history API |
| Filter options | 分散/部分硬编码 | 真实选项聚合 API |

## 11. 主要风险与控制

| 风险 | 后果 | 控制 |
| --- | --- | --- |
| HTTP 线程操作 Playwright page | 跨线程异常、浏览器状态损坏 | gate 只发信号，worker 复检 |
| 把 Review 当 membership | 移出/导出改写人工结论或把已复核商品重新排队 | 分表、repository 不交叉写；应用服务事务协调明确人工决策；测试状态投影不变量 |
| 列表按 Snapshot 重复 | 同商品多行、清单重复 | Product PK + representative Snapshot |
| 历史页读取最新结果 | 历史内容漂移 | 冻结 JSON 为唯一事实源 |
| 历史索引强绑原 run/Snapshot | 原记录删除后历史无法重建 | 历史来源 ID 使用冻结文本，只对 `sampling_lists.list_id` 保持稳定归属 |
| SQLite 成为任务名称唯一副本 | 重建索引后丢失显式名称 | 创建时同步写 `task_request.json`；导入按明确优先级保留非空值和生成 fallback |
| 导出半成功 | 文件/DB/当前清单不一致 | preparing 状态、原子文件、事务和恢复 |
| Product 列表读取每件 Recommendation | N+1 文件 I/O、分页变慢 | 列表只返回摘要，详情按需组合 |
| 硬编码 Context/Query/筛选 | 与 Reference 和配置漂移 | 全部来自 API |
| 前端拼淘宝 URL | 链接错误或越界 | 只使用保存的 `product_url` |
| Excel 公式注入 | 打开表格时执行意外公式 | 对 `= + - @` 开头文本转义，URL 只允许 http/https |
| Figma 小字号照搬 | 长时间复核可读性差 | 正文 13-14px、表格 13px、辅助 12px |
| 术语越过业务边界 | 用户误读为检测或裁决 | 文案白名单、禁用词测试、免责声明 |
| 没有本地运行数据 | 视觉开发依赖假业务数据 | 使用测试 fixture/静态 contract fixture；不提交假产品到生产路径 |

## 12. 迁移策略

1. 保持 `web/` 不删、不改默认服务；正式创建 `frontend/` 前先记录 `node --version` 和 `npm --version`，再按当前 Node 选择兼容的 React、TypeScript、Vite、Tailwind CSS 4 与 Lucide React 版本，用 Vite proxy 开发并生成、提交 `package-lock.json`，不得为匹配 Figma 版本号静默要求不兼容 Node；
2. 先稳定 DB/API 契约和 typed client，再实现页面，避免 Figma mock 反向定义后端；
3. schema 7 到 8 只做 additive migration，旧 run 与 Review 原位保留；
4. Recommendation 继续使用商品目录 JSON；Sampling 历史使用独立冻结文件；
5. 每个 Phase 做定向 Python 测试、TypeScript 检查和 Vite build；涉及 Python 核心后再跑全量 unittest；
6. Phase 末才做一次本地浏览器视觉验收，第一轮不访问淘宝；
7. Phase 3 验收后才把 Python 静态根默认切到 `frontend/dist`，并保留显式 `--web-root web` 回退。

## 13. Phase 0 Gate 结论

可以进入 Phase 1，但前提是实现时继续遵守：D1-D6 不改业务规则、Review 与 Sampling repository 分离且明确人工决策由应用层事务协调、manual-action page 只由 worker 操作、历史清单读取冻结事实、无真实依据不补齐成分/方法。`waiting_for_manual_action` 只表示“等待淘宝验证”，`awaiting_review` 只表示“待人工复核”，两者不得混用。Phase 1 创建前必须完成 Node/npm preflight；`.figma/`、Figma 原型产生的 `.gitattributes` 与 `Web Page Layout Design/` 始终只作本地参考，不纳入提交。本文件和 `docs/UX_REDESIGN_SPEC.md` 是后续实现的正式基线。
