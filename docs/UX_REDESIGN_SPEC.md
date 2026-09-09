# 网络食品风险线索发现与抽检辅助筛查系统 UI/UX 重构设计书

> 文档状态：Approved-for-implementation candidate（等待 Phase 0 确认）<br>
> 版本：UX Redesign v1 / Phase 0<br>
> 日期：2026-09-09<br>
> 代码基线：`c8d962cfc20dfe7761a74ebea9a45b57fbe68711`<br>
> 配套差距分析：`docs/UX_REDESIGN_GAP_ANALYSIS.md`

## 1. 文档用途与优先级

本文是后续 Phase 1-3 的产品、前端、后端契约和验收 Source of Truth。发生冲突时按以下顺序处理：

1. 当前真实后端代码与冻结业务边界；
2. 已确认的 UX 重构需求；
3. 本设计书；
4. 本地 Figma Make 原型的视觉、布局和交互；
5. Figma mock 类型与 mock 数据。

Figma mock 不能定义真实业务。任何成分、方法、商品、任务、筛选项和状态必须来自真实文件或 API。

## 2. 产品边界

### 2.1 产品定位

本系统是“网络食品风险线索发现与抽检辅助筛查系统”。用户通过系统：

```text
查看已有商品
  -> 核对页面 Evidence
  -> 理解可能风险方向
  -> 查看已核验的成分与方法建议
  -> 人工决定是否进入当前抽检清单
  -> 导出并保存历史只读清单
```

用户也可主动创建一次专项排查：

```text
创建排查
  -> 搜索商品
  -> 采集详情
  -> 线索识别
  -> 人工复核
  -> 加入同一份全局当前抽检清单
```

### 2.2 不是本系统的能力

系统不执行自动法律裁决、实验室检测、成分确认、风险评分或概率预测。界面不得把页面线索写成样品事实。

生产 UI 禁止使用会暗示已完成成分或法律确认的措辞，包括“检出”“含有”“确认非法添加”“违法商品”“疑似违法”“高风险/低风险”“风险概率”“置信度”。

统一推荐区说明：

> 结果基于网络商品页面宣传线索形成，仅用于风险线索发现与抽检辅助；不表示商品实际含有相关化合物，不构成违法认定或实验室检出结论。

### 2.3 明确不做

不增加 BJS 202405、新 Risk Mapping、新 Bridge、新 Effect Keyword、Group Expansion、LLM、自动食品分类、自动 Context 推断、GEO、多用户 RBAC、多任务队列、Redis/Celery、多平台、Dashboard 大屏、视频识别或复杂统计。

## 3. 技术方案

### 3.1 冻结技术栈

前端：React、TypeScript、Vite、Tailwind CSS 4、Lucide React。优先使用 React state、`useReducer` 和 Context；HTTP 使用原生 `fetch` + typed API client。

后端继续使用 Python、`ThreadingHTTPServer`、SQLite、Playwright 和 PaddleOCR。不得因 UI 重构切换到 Flask、FastAPI、Django、Next.js、Vue、Angular、Electron、Redux、Zustand、React Query 或大型 UI 组件库。

实现应从干净的 Vite 配置开始，只保留 React/Tailwind 插件和 `/api -> http://127.0.0.1:8765` 开发代理。不得复制 Figma Make 插件、`.figma` 设施或网络字体依赖；`.figma/`、Figma 原型产生的根目录 `.gitattributes` 和 `Web Page Layout Design/` 仅作本地视觉参考，不得提交。

### 3.2 运行结构

```text
frontend/ (Vite dev / static dist)
      |
      | typed fetch /api
      v
src/local_api.py (127.0.0.1:8765)
      |-- TaskManager -> StandalonePipeline worker
      |-- DataStore -> SQLite index
      |-- output/<run_id> -> evidence/recommendation facts
      `-- output/sampling_lists -> frozen sampling-list facts
```

开发期由 Vite 服务前端，Python 只提供 API 和 run assets。Phase 3 验收前，Python 默认静态根仍为 `web/`。验收后默认服务 `frontend/dist`，显式 `--web-root web` 保留回退。

## 4. 核心实体与不可破坏的不变量

### 4.1 实体关系

```text
Product 1 ---- N ProductSnapshot N ---- 1 Task
                         |
                         |---- N Evidence
                         `---- 1 Review

CurrentSamplingMembership N ---- 1 Product
                          N ---- 1 source ProductSnapshot

SamplingList 1 ---- N SamplingListItemIndex
      |
      `---- frozen JSON/XLSX/evidence files (事实源)
```

### 4.2 不变量

1. Product 是稳定商品身份；页面状态、Evidence、Recommendation 和 Review 都属于具体 Snapshot；
2. 商品总览一件 Product 一行，列表使用筛选范围内的代表 Snapshot；
3. Review 与 Sampling Membership 是两个实体；repository 不得互相隐式写入，任何“移出”或“导出”都不得改 Review；“加入抽检清单”和“暂不纳入”作为完整人工决策，只能由 application/service transaction 显式协调两者；
4. 当前清单内一个 Product 最多一条 membership；
5. membership 必须记录其依据的 source Snapshot；
6. Recommendation 事实源仍是商品目录 JSON，不能复制到 SQLite；
7. 历史清单事实源是导出时冻结的文件，不读取最新 Product 或重新运行 D5；
8. seller-managed 是主要页面证据，UGC 只作辅助线索；
9. Knowledge Gap 是合法结果，不得为了填满 UI 制造成分或方法；
10. 淘宝 URL 只使用已保存的 `product_url`。

## 5. 信息架构与路由

### 5.1 一级导航

固定顺序：

1. 商品总览；
2. 排查档案；
3. 抽检清单。

默认路由是商品总览。单次排查工作区属于排查档案的二级页面，不进入一级导航。

第一版不增加 router 依赖，采用轻量 hash route 并支持浏览器前进/后退：

| Route | 页面 |
| --- | --- |
| `#/products` | 商品总览 |
| `#/products/:productId?` | 商品总览 + 右侧详情 |
| `#/inspections` | 排查档案 |
| `#/inspections/:taskId` | 单次排查工作区 |
| `#/sampling` | 当前/历史抽检清单 |
| `#/sampling/history/:listId` | 历史只读清单 |

### 5.2 Sidebar

自动默认规则：

| 场景 | 自动状态 |
| --- | --- |
| 商品总览纯列表 | 展开 |
| 商品总览已打开详情 | 收缩 |
| 排查档案 | 展开 |
| 单次排查工作区 | 收缩 |
| 抽检清单普通表格 | 展开 |
| 抽检清单已打开 Drawer | 可收缩 |
| 窄屏 | 收缩 |

用户点击切换按钮后，将 `expanded/collapsed` 保存到 `sessionStorage`。当前会话内手动选择优先于路由自动规则；新会话重新使用智能默认。收缩状态保留导航图标、Tooltip、当前栏目状态和抽检清单数量 Badge。禁止 hover 自动展开。动画时长 180-220ms，并尊重 `prefers-reduced-motion`。

## 6. 商品总览

### 6.1 首次进入

- API `total > 0`：直接显示商品表；
- `total = 0`：显示初始化空状态，说明尚无已索引商品，并提供“前往排查档案”；
- API 失败：显示局部错误和重试，不伪装为空数据。

不得在生产代码中提供 mock 商品作为空状态替代。

### 6.2 列表语义

一件 Product 一行。代表 Snapshot 规则：

1. 无 Snapshot 范围筛选时，取全局最近 Snapshot；
2. 有 Task、MonitorTarget、风险方向、Review 或时间筛选时，先得到匹配 Snapshot，再取该 Product 在匹配集合中的最近一条；
3. 相同 `collected_at` 时按 `task_id` 稳定决胜；
4. 列表必须明确它显示的是“筛选范围内最近快照”。

主表字段：

- 商品（名称、店铺、低优先级商品 ID）；
- 最近所属排查；
- 最近可能风险方向；
- 人工复核状态；
- 当前抽检清单状态及“曾纳入 N 次”；
- 最近采集时间；
- 历史记录次数；
- 操作。

不把 OCR 张数、原图数量、Pipeline stage 或 `region` 当作核心列；`region` 只能在次级信息中称为“搜索页地区”，不得称为产地。

### 6.3 筛选

筛选项：商品名/店铺/商品 ID、所属排查、MonitorTarget、可能风险方向、Review 状态、Sampling 状态、采集批次、采集时间。选项来自真实 API；时间使用用户输入的起止日期。

Sampling 状态至少包括：

- 当前已在清单；
- 曾进入历史清单但当前不在；
- 从未进入清单。

查询条件变化回到第 1 页，服务端分页；默认每页 20，最大 100。

### 6.4 右侧详情

打开详情后主表收窄、Sidebar 自动收缩（未被手动偏好覆盖），右侧详情独立滚动。详情包含：

1. 商品基础档案；
2. ProductSnapshot 时间线；
3. 当前选中 Snapshot 摘要；
4. Evidence；
5. 抽检辅助建议；
6. 必要时 Product Context；
7. Review 与清单操作。

时间线默认选最新 Snapshot。选择历史 Snapshot 时，所有证据、Recommendation、Review 和清单依据提示都切换到该 Snapshot。加入前显示“将依据 YYYY-MM-DD HH:mm 的页面快照加入当前清单”。

## 7. 排查档案与新建排查

### 7.1 排查档案卡片

卡片字段：排查名称、状态、MonitorTarget/搜索词、创建时间、详情采集进度、发现线索、建议跟进数、暂不纳入数、异常数量（仅大于 0 时显示）。技术 task ID 放低优先级。人工处理统计必须使用持久 Review 语义：`recommendFollowUpCount` 与 `noFurtherActionCount`；`currentSamplingItems` 若显示，只能作为“当前清单中”的次级信息，不能充当长期“已纳入”统计。

业务状态映射：

| 条件 | code | UI 标签 | 操作 |
| --- | --- | --- | --- |
| 初始化/搜索/详情/OCR 正在运行 | `running` | 排查中 | 查看执行进度 |
| `waiting_for_manual_action` | `waiting_for_manual_action` | 等待淘宝验证 | 查看验证提示 |
| Pipeline 完成且仍有待处理 Snapshot | `awaiting_review` | 待人工复核 | 继续人工复核 |
| 完成且无待处理项 | `completed` | 已完成 | 查看排查结果 |
| 完成且有失败项 | `partial_error` | 部分异常 | 查看执行结果 |
| 中断且可恢复/不可恢复 | `interrupted` | 已中断 | 继续任务/查看原因 |

禁止把淘宝人工验证和业务人工复核混为一类：`waiting_for_manual_action` 的 UI 固定表达“等待淘宝验证”，`awaiting_review` 固定表达“待人工复核”，后者操作可使用“继续人工复核”或“处理待复核商品”。禁止显示“暂停/恢复”。只有已有安全断点且 `runtime.resumable=true` 时显示“继续任务”。

### 7.2 新建排查

两种模式仍映射现有后端 `quick` / `monitor`：

#### 快速任务（单搜索词）

- 排查名称（可选）；
- 目标平台：淘宝（只读）；
- 搜索关键词（必填）；
- 高级设置：候选数量、详情采集数量；
- 主按钮：“开始排查”。

#### 检测任务（对象词组）

- 排查名称（可选）；
- 目标平台：淘宝（只读）；
- 从 `/api/monitor-targets` 选择真实 MonitorTarget；
- 只读展示该对象的已启用、已验证 SearchQuery；
- 高级设置：每个搜索词候选数量、详情采集数量；
- 主按钮：“开始排查”。

不提供“保存草稿”，不建立 Draft 表，不在 localStorage 制造业务记录。前端不得拼接“对象茶/对象膏”等 Query。单活动任务期间表单禁用，并显示活动排查入口。

## 8. 单次排查工作区

### 8.1 布局

```text
Header
紧凑流程条
商品队列（独立滚动） | 商品研判详情（独立滚动）
```

主页面容器本身不产生第三层长滚动。桌面视口优先；紧凑桌面可调整队列宽度，窄屏改为队列/详情单列切换。

### 8.2 流程条

只展示业务步骤：

```text
搜索商品 -> 采集详情 -> 线索识别 -> 人工复核
```

允许示例：“搜索 ✓ — 详情 ✓ — 线索 ✓ — 人工复核 5/8”。DOM、Network、PaddleOCR 只在技术详情中出现。

### 8.3 左侧队列

一张卡表示一件 ProductSnapshot，不是一条 Evidence。卡片字段按顺序为：商品名称、队列状态、可能风险方向、代表性 Evidence 原文、Evidence 来源数量。

筛选固定为：全部、待复核、已纳入当前清单、已复核/当前未在清单、暂不纳入。

为同时满足 Review 与 Membership 分离，队列状态是 UI 投影，不是数据库 Review 枚举：

1. 当前有 membership -> “已纳入当前清单”；
2. 无 membership 且 Review=`no_further_action` -> “暂不纳入”；
3. 无 membership 且 Review=`recommend_follow_up` -> “已复核 / 建议跟进，当前未在清单”；
4. Review=`pending` -> “待复核”。

原始 Review 状态仍在详情内单独可见。判断顺序先看当前 membership，再看 Review；`historicalCount` 另行显示历史次数，不参与上述状态覆盖。导出清空 membership 或用户单独移出当前清单后，`recommend_follow_up` 仍是已完成 Review，不得重新显示为“待复核”或进入待复核筛选。

若存在待复核项，首次进入默认筛选“待复核”并选中第一件。成功完成加入或暂不纳入后，自动选择下一件待复核商品；没有下一件时保持当前项并显示完成提示。

## 9. 商品研判详情

固定信息顺序：

```text
商品信息
-> 可能风险方向
-> 页面证据
-> 抽检辅助建议
-> 必要时 Product Context
-> 人工复核与清单操作
```

### 9.1 商品信息

显示名称、店铺、商品 ID、真实保存 URL、所属排查、Snapshot 采集时间、搜索页地区。不得从 ID 拼 URL。

### 9.2 可能风险方向

使用 Recommendation `risk_labels` / `possible_risk_summary`，没有可桥接风险时显示中性空状态。使用 amber/orange 线索色，不使用红色大面积渲染或风险等级。

### 9.3 Evidence

Evidence 必须明确分组：

- 商家管理内容：主要证据，默认展开；
- 用户生成内容：辅助线索，默认折叠。

每条支持实际可用时查看：原文、来源路径、OCR 原图、OCR 全文、页面截图。无法建立某种反查关系时不显示空按钮。代表性 Evidence 优先选 seller-managed；只有 UGC 时明确“仅辅助线索”。

### 9.4 抽检辅助建议

UI 名称固定为“抽检辅助建议”。不得向普通用户显示 D1-D6、Knowledge Trace、Reference Mapping ID 等内部词。

每个成分显示：规范名称、CAS、follow-up 说明。方法按 D5 原字段分组：

1. `suggested_methods` -> “相关已核验方法”，主层级；
2. `methods_needing_context` -> “需补充商品信息后判断”，次层级；
3. `other_known_methods` -> “其他已知方法”，默认折叠。

`revoked`、`superseded`、`not_applicable` 只能在次级区域展示，视觉不得等同正式建议。官方来源只使用保存的 `source_reference`，通过安全 URL 校验后打开。

Knowledge Gap 标准空状态：

> 暂无已核验的检测建议。当前页面发现相关宣传线索，但现有知识库暂无足够核验依据关联至具体检测成分。页面证据仍可供人工复核。

不能用 UI 常识补充任何成分或方法。

### 9.5 Product Context

仅当当前 Recommendation 存在非空 `methods_needing_context` 时显示。选项来自 `/api/inspection-context-options`；空字符串在提交时转换为 `null`，并以“无法确认”展示。保存后调用现有 Context API 重新计算 D5，显示局部 loading、成功或错误；已有 Evidence/Review 不因重算失败消失。

### 9.6 Review 与 Sampling 操作

Review 继续写现有三种值：

- `pending`；
- `recommend_follow_up`；
- `no_further_action`。

用户主操作是完整人工决策：

- “加入抽检清单”：在一个后端 application/service transaction 中设置 Review=`recommend_follow_up`、保存 Snapshot Review note，并创建或确认当前 Sampling Membership；
- “暂不纳入”：在同一类应用层事务中设置 Review=`no_further_action`、保存 Snapshot Review note，并确保当前 membership 不存在；如已存在则在该事务中安全移除；
- 备注（可选）：只保存为 Snapshot Review note。

Sampling repository 永不偷偷修改 Review，Review repository 永不偷偷修改 Membership；实体和 repository 边界保持独立。跨实体变更只由明确命名的 application/service 决策操作在同一数据库事务中协调，React 不得连续调用两个 mutation 自行处理半成功状态。从商品总览直接点击“加入抽检清单”也属于同一明确人工决策，必须形成 `recommend_follow_up` Review。

单独的“移出当前清单”只删除 membership，永远不改变 Review。移出后若 Review=`recommend_follow_up`，presentation 应显示“已复核 / 建议跟进，当前未在清单”。

加入成功后显示“已在当前抽检清单”；Knowledge Gap 不阻止加入；UGC-only 加入前显示弱证据提示，但用户明确操作后允许加入。

## 10. 当前与历史抽检清单

### 10.1 页面结构

一级栏目打开后直接显示标签：

```text
[当前清单 N] [历史清单]
```

不显示“当前草稿卡 -> 查看详情 -> 巨型 Modal”的多余层级。详情使用右侧 Drawer；当前表格与历史列表是页面主体。

### 10.2 当前清单

核心字段：

- 商品；
- 商品链接；
- 来源排查；
- 可能风险方向；
- 建议关注/检测成分；
- 相关方法/标准；
- 加入时间；
- 历史是否曾纳入；
- 操作。

页面视觉上必须突出教师要求的“产品名、链接、可能风险、建议检测成分、相关标准”。没有 Method 的商品可以保留，显示“暂无已核验方法”。

移出后显示 Toast，约 5 秒内可撤销。撤销使用 DELETE 返回的原 membership 再调用仅恢复 membership 的幂等 POST；不弹 Confirm Modal，也不改变原 Review。

### 10.3 导出

主按钮：“导出当前抽检辅助清单（N）”。点击后显示轻量确认，说明：将生成 Excel、冻结历史清单并清空当前 membership，Review 不会改变。

XLSX 至少包含：

- 商品名称；
- 商品链接；
- 店铺；
- 来源排查；
- 页面采集时间；
- 可能风险方向；
- 主要页面证据；
- Evidence qualification；
- 建议关注/检测成分；
- 相关方法编号；
- 方法名称；
- 方法适用状态；
- 人工备注。

建议工作簿包含“抽检辅助清单”和“说明”两个 worksheet；说明页写清导出时间、清单编号、字段解释和完整免责声明。所有用户/页面文本写入单元格前防止公式注入；商品链接只接受已保存的 http/https URL。

导出成功后：

1. 创建只读历史清单；
2. 当前 memberships 清空；
3. Review、Evidence、Recommendation 不变；
4. 返回历史清单编号和下载入口；
5. Sidebar Badge 更新为 0。

### 10.4 历史清单

历史列表显示编号、导出时间、商品数、只读状态。允许查看和重新下载；不允许修改、重算、移出或更改 Context。

历史详情只读取 `sampling_list_snapshot.json`。每个 item 保存导出时的：

- product ID、source Snapshot ID、source Task ID、added_from/added_at；
- 商品名称、链接、店铺、页面采集时间；
- Evidence 与 qualification；
- 风险方向、成分、方法、适用性；
- Product Context、Review 和备注；
- Recommendation gaps 和免责声明；
- 被展示的证据资产副本及 SHA-256。

历史详情不得查询最新 Recommendation 来替换冻结结果。

## 11. 后端 API 契约

所有时间使用带时区的 ISO 8601；所有错误保持 `{error: {code, message}}`。新增 mutation 做输入大小、枚举、长度、外键和路径校验。

### 11.1 Product

扩展：

```text
GET /api/products
  ?query=
  &target_id=
  &task_id=
  &review_status=
  &effect=
  &sampling_status=current|historical_only|never
  &collected_from=
  &collected_to=
  &page=1&page_size=20
```

每项新增：

```json
{
  "snapshotCount": 3,
  "sampling": {
    "inCurrentList": true,
    "sourceSnapshotId": "ps_...",
    "historicalCount": 2
  }
}
```

`sampling_status` 语义为：`current` 表示当前 membership 存在，`historical_only` 表示当前 membership 不存在但 `historicalCount > 0`，`never` 表示当前与历史都未纳入。`current` 商品仍可能同时 `historicalCount > 0`，因此列表响应必须始终独立返回 `historicalCount`。

新增：

- `GET /api/product-filter-options`：实际 tasks、risk directions、Review/Sampling 可选值；
- `GET /api/snapshots/{snapshot_id}/workspace`：返回 Snapshot、Evidence、Review、assets、inspection、sampling 的组合 DTO。

保留旧 `GET /api/snapshots/{id}` 以兼容当前 Web；React 使用 workspace DTO。

### 11.2 Tasks / inspections

`POST /api/tasks` 增加可选 `name`，最大 120 字符。用户提供的非空名称规范化为 `display_name`，必须在创建 run 时同时写入该 run 的持久配置事实文件 `task_request.json`；`tasks.display_name` 只做 SQLite 查询索引，不能成为唯一事实副本。旧 run 没有显式名称时，按真实 MonitorTarget 显示名或 keyword 生成 fallback。

重新 import run 时按以下优先级解析：`task_request.json` 中的非空显式 `display_name` > SQLite 中已有的非空 `tasks.display_name` > 真实 MonitorTarget/keyword fallback > task ID。缺失或空字符串不得覆盖已有显式名称；旧 run 无名称时允许重新生成相同语义的 fallback，但不得把 fallback 回写到 `task_request.json` 冒充用户显式输入。

`GET /api/tasks` 每项增加：

```json
{
  "displayName": "酸枣仁专项排查",
  "businessStatus": {"code": "awaiting_review", "label": "待人工复核"},
  "archiveSummary": {
    "detailCompleted": 2,
    "detailTarget": 2,
    "clueProducts": 2,
    "pendingReview": 1,
    "recommendFollowUpCount": 1,
    "noFurtherActionCount": 0,
    "currentSamplingItems": 1,
    "errorCount": 0
  }
}
```

`recommendFollowUpCount`、`noFurtherActionCount` 来自持久 Review，供排查档案卡片展示人工处理统计；`currentSamplingItems` 来自当前 membership，只能作为“当前清单中”次级信息。导出清空当前清单后，前两个 Review 计数不变，不能用 `currentSamplingItems` 回推长期“已纳入”。

继续使用 `POST /api/tasks/{id}/resume`；仅 `runtime.resumable=true` 时可调用。

### 11.3 Manual action

新增：

```text
POST /api/tasks/{task_id}/manual-action/acknowledge
```

请求体：

```json
{"generation": 1}
```

成功返回 202。非活动任务、generation 过期或当前不在 waiting 状态返回 409。`GET /api/tasks/{id}` 新增：

```json
{
  "manualAction": {
    "status": "waiting",
    "generation": 1,
    "reason": "淘宝人工验证",
    "requestedAt": "...",
    "lastCheckedAt": null,
    "attempt": 0,
    "canAcknowledge": true
  }
}
```

HTTP handler 只能 acknowledge gate，不得持有或调用 page。

### 11.4 Sampling

```text
GET    /api/sampling-list
POST   /api/snapshots/{snapshot_id}/review-decision
POST   /api/sampling-list/items
DELETE /api/sampling-list/items/{product_id}
POST   /api/sampling-list/export
GET    /api/sampling-lists
GET    /api/sampling-lists/{list_id}
GET    /api/sampling-lists/{list_id}/download
```

完整人工决策请求：

```json
{
  "decision": "recommend_follow_up",
  "added_from": "product_overview",
  "note": ""
}
```

`decision` 只允许 `recommend_follow_up` / `no_further_action`。application/service 从路径中的 Snapshot 反查 Product 与 Task 并校验关系，不接受客户端伪造 `product_id` 或 `source_task_id`。`recommend_follow_up` 在同一数据库事务中写 Review + Review note 并创建/确认 membership；`no_further_action` 在同一事务中写 Review + Review note 并删除可能存在的 membership。任何一步失败都整体回滚。

`POST /api/sampling-list/items` 是独立 membership 恢复/维护接口，请求仅含 `product_id`、`source_snapshot_id`、`added_from`，不含 note，也不写 Review。相同 Product 重复 POST 幂等返回现有 membership，不静默更换依据 Snapshot。“更新依据”留作 Should Have；第一版可要求先移出再恢复。商品总览和工作区的“加入抽检清单”必须调用 `review-decision`，不得用该低层 membership mutation 代替。

导出请求：

```json
{"confirmed": true}
```

空清单返回 409。成功返回 201 和 list metadata/download URL。

## 12. SQLite 与文件事实源

### 12.1 Schema version 8

增量变更：

```sql
ALTER TABLE tasks ADD COLUMN display_name TEXT NOT NULL DEFAULT '';

CREATE TABLE sampling_list_memberships (...);
CREATE TABLE sampling_lists (...);
CREATE TABLE sampling_list_item_index (...);
```

正式实现继续使用项目现有的 `CREATE TABLE IF NOT EXISTS` + `_ensure_column` 风格，并设置 `PRAGMA user_version = 8`。禁止删除/重建已有表。

关键约束：

- `sampling_list_memberships.product_id` 为 PK；
- 当前 membership 的 Product/Snapshot/Task 都使用严格外键，三者必须一致，由 service/repository transaction 校验；
- `sampling_list_memberships` 不含 note；MVP 人工备注唯一保存于 Snapshot Review，历史文件冻结导出时的 Review note；
- `added_from` 只允许 `product_overview` / `inspection_workspace`；
- `sampling_lists.status` 只允许 `preparing` / `exported`；
- 历史 item index 对 `(list_id, product_id)` 唯一，并稳定外键归属于 `sampling_lists.list_id`；
- 历史 index 的 `product_id`、`source_snapshot_id`、`source_task_id` 是冻结标识 TEXT/索引值，不对当前 `products`、`product_snapshots`、`tasks` 建强制外键；
- 删除当前 membership 不级联删除 Product/Snapshot；
- 历史 metadata 不因 run 重导入被覆盖。

### 12.2 冻结文件

路径固定在 `output/sampling_lists/<list_id>/`，所有 list ID 和相对路径使用与 run files 同等级别的路径穿越校验。JSON 和 XLSX 先写临时文件再原子替换；最终记录 SHA-256。

XLSX 是用户交付格式，JSON 是历史业务事实源。SQLite 丢失时可从历史 JSON 幂等重建 `sampling_lists` 和 `sampling_list_item_index`；即使原 ProductSnapshot、Task 或整个 run 已不存在，仍必须仅依据冻结 JSON 中的文本标识完成重建。重建不会反向创建 Product/Snapshot/Task，也不会恢复已清空的当前 memberships。

## 13. Manual-action 状态机

### 13.1 状态

```text
inactive
  -> waiting (worker 检测到 blocker)
  -> rechecking (收到 Web acknowledgement 或周期超时)
  -> resolved (worker 确认 blocker 消失)
  -> inactive/继续 Pipeline

rechecking -> waiting (仍被阻塞，generation 不变或递增 attempt)
任意活动状态 -> interrupted (worker/服务退出)
```

### 13.2 并发规则

- gate 属于 TaskManager 当前活动任务；
- `Condition/Event` 只传递 acknowledge signal；
- `blocker_reason(page)` 只在 Collector worker 调用；
- acknowledgement 带 generation，防止旧按钮点击解除后来一次 blocker；
- worker 可 3-5 秒周期复检，复检频率不能形成高频页面操作；
- browser 被用户关闭时保持现有安全失败/中断语义；
- CLI 默认 adapter 仍可用 terminal `input()`，Web adapter 不允许 terminal input。

## 14. 前端目录与组件边界

```text
frontend/
  package.json
  index.html
  vite.config.ts
  tsconfig.json
  src/
    main.tsx
    app/
      App.tsx
      AppRouter.tsx
      AppState.tsx
    api/
      client.ts
      contracts.ts
      products.ts
      inspections.ts
      sampling.ts
    domain/
      product.ts
      inspection.ts
      recommendation.ts
      sampling.ts
      presentation.ts
    layout/
      AppShell.tsx
      Sidebar.tsx
      PageHeader.tsx
    components/
      StatusBadge.tsx
      EmptyState.tsx
      ToastProvider.tsx
      Drawer.tsx
      LoadingState.tsx
      EvidenceCard.tsx
      RecommendationPanel.tsx
      ProductContextForm.tsx
      ReviewActions.tsx
    pages/
      products/
        ProductOverviewPage.tsx
        ProductTable.tsx
        ProductDetailPanel.tsx
        SnapshotTimeline.tsx
      inspections/
        InspectionArchivePage.tsx
        NewInspectionDialog.tsx
        InspectionWorkspacePage.tsx
        InspectionFlow.tsx
        ReviewQueue.tsx
        ManualActionBanner.tsx
      sampling/
        SamplingListPage.tsx
        SamplingListTable.tsx
        SamplingListDrawer.tsx
        HistoricalListView.tsx
    styles/
      index.css
      tokens.css
```

约束：

- `api/contracts.ts` 只描述真实 API；不得导入 Figma mock types；
- `domain/presentation.ts` 只做 code -> label/tone 映射，不做业务推断；
- Page 负责编排，复用组件负责局部交互；
- 不复制一个巨型 `App.tsx`，也不建设过度抽象的 Design System；
- 共享 current sampling count 由 App Context 管理，mutation 成功后刷新；
- 不提交生产 mock 数据；测试 fixture 放测试目录。

## 15. 视觉、响应式与可访问性

### 15.1 视觉 tokens

- 页面背景：浅灰蓝；Card：白色；边框：细、低对比；
- primary：sky/blue；线索：amber/orange；当前已加入：green；
- Context 信息不足：yellow；Knowledge Gap：gray/blue；
- red 仅用于系统错误和严重操作错误；
- Card 适度圆角，避免消费类大圆角和夸张阴影。

字号：正文 13-14px，表格 13px，辅助 12px，低优先级 ID 11-12px。不得照搬 Figma 大量 10px/11px 正文。

字体使用本机优先栈，例如 `Noto Sans SC`, `Microsoft YaHei`, system-ui；不依赖 Google Fonts。

### 15.2 视口

- 核心验收：1440px 和 1080px 桌面；
- 1080px 保持信息可读，表格允许局部横向滚动；
- Master-Detail 两列各自滚动；
- 窄屏 Sidebar 收缩，详情改为覆盖层或单列；
- 不承诺手机端完整业务操作，但不能出现不可关闭遮罩或内容永久不可达。

### 15.3 可访问性

- 所有 icon-only 按钮有 `aria-label` 和 Tooltip；
- Drawer/Dialog 有焦点圈定、Esc 关闭、关闭后恢复焦点；
- 状态不能只靠颜色；
- 表格、表单、错误和 Toast 使用正确语义及 `aria-live`；
- 键盘可完成筛选、选择 Snapshot、保存 Context、复核和清单操作。

## 16. 加载、空状态和错误

| 场景 | 行为 |
| --- | --- |
| 商品/任务初载 | 骨架或紧凑 loading，不清空已有内容 |
| 局部 API 失败 | 局部错误 + 重试，其他面板保留 |
| 无商品 | 初始化空状态，不制造示例数据 |
| 无 Evidence | “当前快照暂无页面线索” |
| Knowledge Gap | 使用正式合法空状态，不补成分/方法 |
| Recommendation 生成失败 | Evidence/Review 仍可用，建议区单独错误 |
| 人工淘宝验证 | 顶部/工作区醒目 amber Banner，允许 acknowledge |
| 清单重复加入 | 返回并显示“已在当前抽检清单” |
| 移出 | Toast + 撤销，无 Confirm Modal |
| 导出失败 | 当前 membership 保持，不生成成功历史记录 |

## 17. 测试与验收总则

### 17.1 Python 定向测试

- schema 7 -> 8 升级且旧数据原位保留；
- Product 代表 Snapshot、`sampling_status=current|historical_only|never` 与独立 `historicalCount`；
- task display name 创建时同时写入 `task_request.json`；旧 run 按真实 keyword/MonitorTarget fallback；重新 import 不用缺失/空值覆盖已有显式名称；
- task 业务状态文案和汇总：`waiting_for_manual_action`/等待淘宝验证与 `awaiting_review`/待人工复核严格分离，`recommendFollowUpCount`、`noFurtherActionCount` 不受导出清空 membership 影响；
- manual gate generation、acknowledge、重复点击、非活动任务、worker-only recheck；
- membership Product 唯一、Snapshot/Task 严格外键与一致性、无重复 note 字段；Sampling/Review repository 互不隐式写入；
- “加入抽检清单”原子写入 `recommend_follow_up` Review + Review note + membership，“暂不纳入”原子写入 `no_further_action` 并移除 membership；任一子步骤失败时整体回滚；单独移出只删 membership；
- 导出或单独移出后，已完成 Review 不重新进入待复核队列；
- 导出成功/失败、原子文件、preparing 恢复、历史冻结、重复下载；删除原 ProductSnapshot/Task/run 后仍可仅由冻结 JSON 重建历史 index，来源 ID 不要求当前实体外键存在；
- 新文件 API 路径穿越与 Excel 公式注入；
- 旧 run 无 Recommendation 兼容。

### 17.2 前端自动检查

- `tsc --noEmit`；
- `vite build`；
- API contract、presentation 和 reducer 的单元测试；队列四状态投影与五个筛选范围必须覆盖，尤其是 `recommend_follow_up` + 无 membership 不得落入待复核；
- 关键组件交互：Sidebar 优先级、筛选、时间线、Context 按需显示、应用层单 mutation 人工决策、移出撤销；不得由 React 串行调用 Review 和 Membership 两个 mutation；
- 禁用词静态检查，不对合法免责声明和技术测试误报。

### 17.3 阶段视觉验收

每个 Phase 结束只做一次本地视觉验收，使用本地 API fixture 或已有历史 run；不访问外部网站。检查 1440px、1080px、键盘、长商品名、空数据、Knowledge Gap、UGC-only、错误和 loading。

涉及 Python 核心改动的 Phase 在定向测试通过后跑一次完整 unittest。真实淘宝/Collector 验收只在后续明确需要时执行，Phase 0 不执行。

## 18. 分阶段实施计划

### Phase 1：数据契约基础 + AppShell + 商品总览

目标：建立 schema/API/typed client 基线，让默认商品总览使用真实数据完成 Product 一行、时间线和右侧详情。

Phase 1 preflight（必须在创建 `frontend/` 之前完成）：

1. 运行并记录 `node --version`；
2. 运行并记录 `npm --version`；
3. 根据当前 Node 环境选择相互兼容的 React、TypeScript、Vite、Tailwind CSS 4 和 Lucide React 版本；技术方向保持不变，但不得为了匹配 Figma 原型版本号而静默要求升级到不兼容 Node；
4. 使用 npm 安装后生成并提交 `package-lock.json`；不得提交 `.figma/`、Figma 原型产生的根目录 `.gitattributes` 或 `Web Page Layout Design/`。

后端修改：

- `src/data_store.py`：schema 8、仅作索引的 `tasks.display_name`、可从 `task_request.json`/真实目标重建名称、Sampling 三表、Product 聚合字段/筛选和只读查询；
- `src/local_api.py`：product filter options、workspace Snapshot 组合 DTO、扩展 product query；
- `src/web_contract.py`：只抽取可复用的 Snapshot assets/inspection 读取 helper，保持旧 contract；
- 新增 `src/sampling_store.py`：membership 和历史 metadata repository，不放 Recommendation 规则；
- 定向修改 `tests/test_data_store.py`、`tests/test_local_api.py`、`tests/test_web_contract.py`；新增 `tests/test_sampling_store.py`。

前端新增：

- 经上述 Node/npm preflight 后创建 `frontend/` 工程基础、Vite `/api` proxy、Tailwind tokens，并提交 npm `package-lock.json`；
- AppShell、Sidebar、PageHeader、StatusBadge、EmptyState、Toast；
- typed API client、Product domain；
- ProductOverviewPage、ProductTable、ProductDetailPanel、SnapshotTimeline；
- Evidence、Recommendation、Context、Review 的只读/编辑组件基线。

API：扩展 `GET /api/products`，新增 `GET /api/product-filter-options`、`GET /api/snapshots/{id}/workspace`；Sampling API 此阶段可先完成 repository contract 和只读 count，mutation UI 留到 Phase 2。

DB：一次性升级到 version 8，仅 additive migration。

测试：上述 Python 定向测试、schema 升级测试、前端 typecheck/build、Product 页面组件测试；Python 全量 unittest 一次。

验收标准：

- 默认打开商品总览；
- 一件 Product 一行且筛选范围代表 Snapshot 正确；
- 详情时间线可切换真实 Snapshot；
- Evidence/Recommendation/Context/Review 使用真实数据；
- 没有 mock 商品、硬编码 URL/Query/Context；
- `web/` 仍可回退。

### Phase 2：排查档案 + 工作区 + Web 人工验证 + 当前清单操作

目标：完成主动排查和连续复核流程，并彻底移除 Web 正常流程对 terminal Enter 的依赖。

后端修改：

- `src/task_runtime.py`：display name、业务状态摘要、ManualActionGate 注入和任务状态；
- `src/taobao_live.py`：保留 CLI adapter，Web adapter 改为 gate 等待；
- `src/main.py` / `src/discovery.py`：仅做 gate 参数传递所需的最小接线，不改 Collector 算法；
- `src/local_api.py`：manual acknowledge、应用层 Review decision、Sampling membership GET/POST/DELETE；
- `src/data_store.py` / `src/sampling_store.py`：Review decision application/service transaction、独立 repository 操作和 Task/Review 汇总；
- `src/web_contract.py`：新 stage 兼容映射；
- 对应 `tests/test_task_runtime.py`、`tests/test_local_api.py`，新增 `tests/test_manual_action_gate.py`。

前端新增：

- InspectionArchivePage、NewInspectionDialog；
- InspectionWorkspacePage、InspectionFlow、ReviewQueue；
- ManualActionBanner；
- Sampling count Context、加入/移出/Toast 撤销；
- Product Overview 与 Workspace 共用的 ReviewActions。

API：`POST /api/tasks` 增加 name 并同步持久化到 `task_request.json`；task summary 扩展；新增 acknowledge、原子 Review decision 和独立 membership API。

DB：使用 Phase 1 已建 schema 8，不再新增业务表。

测试：manual gate 并发/生命周期、单活动任务、resume、repository 解耦与 application transaction 原子性、导出/移出后的队列状态、队列自动前进、typecheck/build；Python 全量 unittest 一次。阶段末用离线 stub 模拟“等待 -> acknowledge -> worker 复检 -> 继续”，不启动淘宝。

验收标准：

- 排查档案卡片和业务状态正确；
- Quick/Monitor 使用真实 API，参数在高级设置；
- 无暂停/假 Draft/前端 Query 拼接；
- 工作区一张卡一件 Snapshot，左右独立滚动；
- Web acknowledgement 不跨线程操作 page，不需 terminal Enter；
- 从商品总览或工作区加入同一当前清单，并在一次后端事务中形成 `recommend_follow_up` Review；
- “暂不纳入”在一次后端事务中形成 `no_further_action` Review 并确保不在当前清单；
- 移出不改 Review。

### Phase 3：当前/历史清单 + Excel 导出 + 静态切换

目标：完成最终交付闭环和生产静态入口切换。

后端修改/新增：

- 新增 `src/sampling_export.py`：冻结 JSON、复制必要 Evidence、openpyxl XLSX、哈希和两阶段导出；
- `src/sampling_store.py`：preparing/exported 恢复与历史索引；
- `src/local_api.py`：export、history list/detail/download；
- `requirements.txt` 新增 `openpyxl`，不提前在 Phase 1/2 引入；
- `src/local_api.py` 默认静态根切到 `frontend/dist`，保留 `--web-root web`；
- 新增 `tests/test_sampling_export.py`，扩展 API/安全测试。

前端新增：

- SamplingListPage、SamplingListTable、SamplingListDrawer、HistoricalListView；
- 导出轻确认、成功反馈、当前/历史标签、重新下载；
- 完成所有页面的响应式和可访问性收口。

API：新增 export 和历史 API；完成 current sampling DTO。

DB：无 schema 变化；验证从冻结 JSON 幂等重建历史索引，且原 ProductSnapshot/Task/run 不存在时来源文本标识仍可重建。

测试：导出原子性/恢复/冻结性/公式注入/路径安全、历史不随新 Snapshot 漂移、前端 typecheck/build、Python 全量 unittest 一次。

验收标准：

- 当前清单直接可编辑，一 Product 一条；
- Knowledge Gap/UGC-only 可在明确提示后加入；
- XLSX 字段、说明页和免责声明完整；
- 导出后历史只读、当前清空、Review 不变；
- 导出后 `recommend_follow_up` 商品显示“已复核 / 建议跟进，当前未在清单”，不重新进入待复核；排查档案的持久 Review 统计不下降；
- 历史详情永远读取冻结事实并可重复下载；
- 1440px/1080px 无严重遮挡或多重整页滚动；
- Python 默认服务新 dist，旧 `web/` 可显式回退。

## 19. Phase 0 停止点

本设计书完成后停止。当前轮次不得创建 `frontend/`、修改 schema/API、运行淘宝、启动 Collector、push 或开始 Phase 1；设计修正提交只能包含 `docs/UX_REDESIGN_GAP_ANALYSIS.md` 与 `docs/UX_REDESIGN_SPEC.md`，不得纳入任何 Figma 参考文件。待收到“开始Phase 1”后继续同一对话，并先执行 Node/npm preflight，再以本文为实现基线。
