# V2-0 Workspace Convergence Audit

审计日期：2026-09-12<br>
本地工作区：`D:\毕业设计-ux`<br>
审计分支：`ux-redesign-v1`<br>
审计 HEAD：`93778df128d02ace8b6dca0a683ceb398c8012a7`<br>
审计性质：只读工作区、引用关系、运行入口与规范权威性审计；除本报告外未修改现有文件。

## 1. Executive Summary

**结论：`NEEDS_CONVERGENCE`。**

当前代码、自动化测试、配置和历史真实样例已经足以作为 V2 后续开发的技术基础，但当前工作区**不适合在缺少上下文的情况下直接进入 V2-1**。主要原因不是核心运行链不可用，而是：

1. `README.md`、`PROJECT_STATUS.md`、`docs/AI_HANDOFF.md` 仍把 V1 原生 Web、schema 7、旧信息架构和旧测试规模描述为当前状态；
2. `web/` 已退出默认运行链，却仍被一个包含 15 项测试的旧测试模块直接约束，并在多份文档中保留为 fallback；
3. Phase 0/集成审计类文档没有统一标记为历史或已解决，容易被误当成现行实施规范；
4. `output/`、`archive/`、`data/app.db`、截图和历史样例同时存在，若不声明证据、索引、测试样例与设计规范的边界，Codex 容易从运行产物反向推断业务设计；
5. 当前尚无一组覆盖“当前状态、产品需求、系统架构、领域模型、UX、知识治理、路线图、验收”的唯一权威 V2 文档。

建议先完成第 17 节的 V2-0 收敛动作，再开始 V2-1。未来能力缺口（如 `ProductFact`、真实商品产地、保健食品身份、Claim Taxonomy）是 **CURRENT LIMITATIONS**，不是本轮发现的 bug。

## 2. Git / Workspace State

### 2.1 实际 Git 状态

| 项目 | 实际值 | 结论 |
| --- | --- | --- |
| Branch | `ux-redesign-v1` | 符合当前开发分支 |
| HEAD | `93778df128d02ace8b6dca0a683ceb398c8012a7` | `Build historical validation dataset tooling` |
| Upstream | `origin/ux-redesign-v1` | 本地领先 1 个提交、落后 0 个提交 |
| 相对 `main` | `main...HEAD = 1 / 16` | 当前分支包含 16 个 `main` 没有的提交，同时缺少 `main` 的 1 个提交；进入合并阶段前需人工处理分叉 |
| Staged | 无 | 无待提交暂存修改 |
| Modified | 无 | 无已跟踪文件修改 |
| Untracked | `.figma/`、`.gitattributes` | 两者均为本地视觉参考/Figma 产物，未纳入 Git |
| Workspace clean | 否 | 仅因上述 2 个 untracked 项；已跟踪工作树干净 |

配置的 `origin` URL 为 `https://github.com/lovia11/food-safety-risk-monitoring-.git`，而项目说明写作 `lovia11/food-safety-risk-monitoring`。两者尾部是否应有 `-` 需要在下一次远端治理前人工确认；本轮未访问或修改远端。

### 2.2 Historical Validation 状态

Historical Validation builder、候选报告和测试已包含在当前 HEAD 中，不是未提交修改：

- `tools/build_historical_validation_set.py`
- `tests/test_historical_validation_builder.py`
- `docs/HISTORICAL_VALIDATION_CANDIDATES.md`
- 当前生成集：`output/historical_validation_20260911/`

当前生成集受 `.gitignore` 排除，不会随普通 Git 提交进入仓库。不存在尚未 commit 的 builder/report 源文件；生成数据本身按设计保持本地。

### 2.3 `.gitignore` 审计

实际 ignore 检查确认以下路径类别均被排除：

- `output/`
- `archive/`
- `data/*.db` 及 SQLite sidecar
- `.browser-profile/`
- Python `__pycache__/`
- `.paddleocr/`、`.paddlex/`
- `models/`、`model_cache/`
- `frontend/node_modules/`
- `frontend/dist/`
- `output/historical_validation_20260911/` 下的临时/验证产物

未被忽略且当前未跟踪的是 `.figma/` 和 `.gitattributes`。这符合此前“不得提交视觉参考”的纪律，但会持续使 `git status` 非 clean；未来应在明确批准后删除或建立正式忽略策略，本轮不处理。

## 3. Current Runtime Architecture

### 3.1 Backend 真实入口与调用关系

正式本地 Web 启动入口是 `python -m src.local_api`。根目录 `main.py` 只是独立采集 CLI 的薄代理：

```text
Web/API:
src.local_api.main
  -> DataStore(output root + data/app.db)
  -> InspectionRuntime.from_store(...)
  -> DataStore.import_all_runs()
  -> TaskManager
       -> worker thread
       -> StandalonePipeline (src.main)
  -> ThreadingHTTPServer
  -> serve API + frontend/dist + run assets

Standalone CLI:
root main.py
  -> src.main.main
  -> StandalonePipeline

Pipeline:
DiscoveryCoordinator / LiveSearchCollector
  -> PhaseOneCollector (Detail)
  -> shared OCRRuntime + run_ocr
  -> run_analysis (Phase3)
  -> InspectionRuntime.generate (Recommendation)
  -> web_snapshot / DataStore import
```

核心职责：

- `src/local_api.py`：HTTP API、静态文件和 run asset 服务、应用级 wiring；
- `src/task_runtime.py`：Web Task worker、任务生命周期和 Manual Action 协调；
- `src/main.py`：StandalonePipeline 主链；
- `src/data_store.py`：schema 8 SQLite 可重建索引、查询投影、Review eligibility enforcement；
- `src/inspection_runtime.py`：Inspection/Reference runtime bootstrap 与 Recommendation 生成；
- `src/pipeline_contract.py`：Detail/OCR/Analysis/Review 的唯一 readiness 投影；
- `src/review_decision.py`：Review 与当前 Sampling Membership 的应用层事务动作；
- `src/sampling_store.py`：Membership/List 的低层持久化，不修改 Review。

### 3.2 Frontend 真实入口

当前正式 Web 源码是 `frontend/`：React 19.2.8、React DOM 19.2.8、TypeScript 7.0.2、Vite 8.2.2、Tailwind CSS 4.3.3、Lucide React 1.43.0。`frontend/package-lock.json` 固定依赖解析结果。

- `npm run dev` 启动 Vite；
- 开发代理 `/api -> http://127.0.0.1:8765`；
- `npm run typecheck` 执行 TypeScript 检查；
- `npm run build` 先 typecheck，再生成 `frontend/dist`；
- Local API 的默认 `--web-root` 是 `frontend/dist`；
- hash router 默认 `#/products`，当前一级信息架构为“商品总览 / 排查档案 / 抽检清单”。

`frontend/dist` 是当前可部署静态产物，但不是源代码权威；源代码权威是 `frontend/src`、构建配置和 package lock。

### 3.3 当前 Pipeline Contract

`src/pipeline_contract.py` 提供统一后端谓词，当前语义为：

| Readiness | 当前核心事实 |
| --- | --- |
| `detailCollected` | 商品达到 Detail 成功状态且存在真实 `meta.json` 路径 |
| `ocrInputReady` | Detail 成功且存在至少一张原图输入 |
| `ocrReady` | OCR 输入就绪且至少一张图片 OCR 成功 |
| `analysisReady` | Product 状态为 analysis success、OCR ready 且存在 `analysis.json` |
| `reviewEligible` | 等于 `analysisReady` |

Recommendation 成功不是 Review eligibility 的硬前提；Phase3 已成功但 Recommendation 失败时，Evidence 和人工 Review 仍可用，Recommendation 只显示为不可用。Review Decision API 在服务端拒绝非 eligible Snapshot，前端过滤不是唯一防线。

### 3.4 Review / Sampling 当前语义

- Review 是 Snapshot 级人工结论；
- Sampling Membership 是 Product 级当前清单关系，并记录其 source Snapshot；
- “加入抽检清单”由应用服务在一个 SQLite transaction 中完成 Review=`recommend_follow_up` 与 Membership 确认；
- “暂不纳入”在同一业务事务中设置 Review=`no_further_action` 并移除当前 Membership；
- 单独“移出当前清单”只删除 Membership，不改变 Review；
- 低层 restore 仅允许 source Snapshot 的 Review 仍为 `recommend_follow_up`；
- Sampling Export 冻结 JSON/XLSX/evidence 事实并清空 current membership，但不改历史 Review；
- 历史清单以冻结导出为事实源，不要求原 ProductSnapshot 永久存在。

## 4. Directory Classification

| Path | Classification | Used By | Evidence | Proposed Action |
| --- | --- | --- | --- | --- |
| `src/` | A. CURRENT_PRODUCTION | API、Pipeline、DataStore、Review、Sampling、知识 runtime | 当前 Python 运行入口和 28 个 tracked 源文件均位于此处 | KEEP_CURRENT |
| `main.py` | A. CURRENT_PRODUCTION | Standalone CLI | 仅代理 `src.main.main` | KEEP_CURRENT；README 中说明用途 |
| `frontend/src/` | A. CURRENT_PRODUCTION | 当前 React UI | 当前 router、页面、API contract、组件与样式均从此构建 | KEEP_CURRENT |
| `frontend/package.json`、lock、Vite/TS 配置 | A. CURRENT_PRODUCTION | 前端依赖、测试、构建 | build/typecheck/workflow scripts 与 API proxy | KEEP_CURRENT |
| `frontend/dist/` | E. GENERATED_RUNTIME | Local API 默认静态根 | `src/local_api.py --web-root` 默认值为该目录 | 保留本地生成；不作为源代码或设计依据 |
| `config/` | A. CURRENT_PRODUCTION | Monitor、Effect、Bridge、Risk、Inspection runtime | 六份 JSON 被导入/读取并有专门测试 | KEEP_CURRENT；按知识治理规则修改 |
| `tests/` | B. CURRENT_SUPPORT | Python contract/regression tests | 38 个 Python test 文件、412 个 test methods | KEEP_CURRENT；移除 V1 前先处理旧 Web 测试 |
| `frontend/tests/` | B. CURRENT_SUPPORT | 当前前端 workflow contract | 10 个 Node test blocks | KEEP_CURRENT；后续补当前 React 浏览器级验收 |
| `tools/` | B. CURRENT_SUPPORT | Historical Validation 数据构建 | 当前 HEAD 新增 builder 及对应测试 | KEEP_CURRENT；标明不属于生产入口 |
| `manual_input/` | B. CURRENT_SUPPORT | Collector 离线真实 HTML fixture | `tests/test_real_collector_fixtures.py` 使用 `taobao_search.html` | KEEP_CURRENT；不要误判为遗留网页 |
| `data/README.md` | B. CURRENT_SUPPORT / narrow canonical | 数据边界说明 | 明确 output 是事实、SQLite 是索引 | KEEP_CURRENT；未来并入系统架构文档 |
| `data/app.db` | E. GENERATED_RUNTIME | DataStore 查询索引 | schema 8；可从 output 幂等重建；被 Git ignore | 不提交、不当作原始事实或产品规范 |
| `output/` | E. GENERATED_RUNTIME | 原始 run 事实、API import 输入 | 当前 API 扫描直接子目录的 `web_snapshot.json`；被 ignore | 运行证据 SoT；禁止作为设计规范 |
| `output/historical_validation_20260911/` | B/E. CURRENT_SUPPORT + GENERATED_RUNTIME | 离线真实样例验收 | manifest 声明 5 商品、noLiveCollection=true | 保留本地；明确是验证集而非生产覆盖证明 |
| `archive/` | E. GENERATED_RUNTIME / historical backup | 历史 run 保存 | 不被 Local API 默认扫描；被 ignore | 只作备份/取证，永不作为当前设计规范 |
| `.browser-profile/` | F. THIRD_PARTY_OR_ENVIRONMENT | Playwright/Chrome 登录和会话环境 | 浏览器运行生成且被 ignore | 本地保留，按敏感数据处理 |
| `.venv/` | F. THIRD_PARTY_OR_ENVIRONMENT | Python/OCR runtime | 当前为 Python 3.10.0 + 固定 Paddle 依赖 | 不提交；由 requirements 重建 |
| `frontend/node_modules/` | F. THIRD_PARTY_OR_ENVIRONMENT | 前端 build/test | npm 安装产物、被 ignore | 不提交；由 lock 重建 |
| OCR/model cache | F. THIRD_PARTY_OR_ENVIRONMENT | PaddleOCR/PaddleX | `.paddleocr`、`.paddlex`、models/cache 被 ignore | 不提交，不作为模型版本权威 |
| `web/` | C. LEGACY_V1 | 旧原生 ES Modules UI、旧测试、显式 fallback | 默认生产链不使用；`test_web_frontend.py` 有 15 项直接测试 | 暂不删；先移除测试和 fallback 承诺 |
| `ui/` | D. HISTORICAL_DOCUMENTATION | 六张 V1 页面截图 | 旧 IA：总览、商品监测、风险研判、采集任务等；无运行/构建/测试引用 | 未来迁入 `docs/archive/v1/` |
| `docs/` | 混合，逐文档见第 6 节 | 设计、历史、审计、验证 | 权威状态不统一 | 完成 canonical docs 收敛 |
| `collection_experiment.md` | D. HISTORICAL_DOCUMENTATION | 早期采集实验 | 描述 Phase1/OCR 未安装等旧状态 | 未来归档并加 NON-NORMATIVE |
| `README.md` | G（活跃位置但需重写） | 新开发者入口 | 描述旧 Web 和旧 IA | REWRITE_REQUIRED |
| `PROJECT_STATUS.md` | G（活跃位置但需重写） | 项目状态入口 | schema、版本、测试数、Web 均过时 | REWRITE_REQUIRED |
| `requirements*.txt` | A. CURRENT_PRODUCTION | Python 与 OCR 环境 | OCR 锁定 3.2.0/3.7.0/3.7.2 | KEEP_CURRENT；补统一安装说明 |
| `.gitignore` | B. CURRENT_SUPPORT | 仓库卫生 | 正确隔离主要运行/环境产物 | KEEP_CURRENT |
| `.figma/` | G. UNKNOWN_NEEDS_REVIEW（已知为本地参考） | 无运行/构建/测试用途 | untracked；仅设计文档提及视觉参考 | 批准后删除或正式 ignore，绝不提交 |
| `.gitattributes` | G. UNKNOWN_NEEDS_REVIEW（Figma 生成） | 无运行/构建/测试用途 | untracked；无代码引用 | 批准后删除，绝不提交 |
| `.idea/` | F/G. THIRD_PARTY_OR_ENVIRONMENT | 本机 IDE | 无业务运行意义，是否保留取决于用户 | NEEDS_MANUAL_DECISION |
| `src/__pycache__/`、`tests/__pycache__/`、`tools/__pycache__/` | F. THIRD_PARTY_OR_ENVIRONMENT | Python cache | untracked/ignored、可自动重建 | 批准后可安全清理 |

## 5. Legacy V1 Dependency Audit

### 5.1 `web/` 结论

`web/` 是**确认的 LEGACY_V1**，但当前还不是 `SAFE_DELETE_AFTER_APPROVAL`。

| 引用类型 | 结果 | 证据 |
| --- | --- | --- |
| 当前默认 runtime refs | 0 | Local API 默认 `frontend/dist`；当前 React 不 import `web/` |
| 当前 build refs | 0 | Vite 只构建 `frontend/` |
| 当前生产 scripts refs | 0 | 当前启动路径没有复制或加载 `web/` |
| 直接 test refs | 1 个模块 / 15 项测试 | `tests/test_web_frontend.py` 直接读取 `web/index.html` 并 import `web/js/*` |
| documentation refs | 多处 | README、PROJECT_STATUS、AI_HANDOFF、UX 设计文档仍描述旧 Web 或 fallback |
| fallback path | 存在但非默认 | 可显式传 `--web-root web`；代码不对它做专门分支 |

删除 `web/` 不会破坏当前 V2 默认生产启动与 Vite 构建，但会立刻破坏 15 项旧测试，并取消文档承诺的显式 fallback。因此正确顺序是：

1. 确认不再需要 V1 rollback；
2. 删除或替换 `tests/test_web_frontend.py`，将仍有价值的纯 contract 覆盖迁移到当前 React workflow/API tests；
3. 从 README、PROJECT_STATUS、AI_HANDOFF、UX 文档中移除“当前 Web/fallback”表述；
4. 再把 `web/` 提交为删除或移动到明确的外部历史存档。

### 5.2 其它疑似 Legacy 的引用结论

- `ui/`：0 runtime refs / 0 build refs / 0 test refs；仅为 V1 截图，适合归档，不建议直接删除其历史价值。
- `manual_input/taobao_search.html`：不是旧产品 Web；仍是当前真实 Collector fixture，必须保留。
- schema 7→8 migration tests：不是旧 schema 依赖；它们证明 additive migration，必须保留。
- Web snapshot/API contract 中独立的 `schema_version=1`：不是 SQLite schema 1，也不是旧数据库依赖；不能因数字相同误删。
- Python API tests 中临时目录名 `web`：是测试自建静态根，不是对仓库 `web/` 的依赖。

## 6. Documentation Conflict Matrix

| Document | Current Accuracy | Main Conflicts | Proposed Action |
| --- | --- | --- | --- |
| `README.md` | OBSOLETE_OR_MISLEADING | 把 `web/` 当当前 MVP；旧 IA；缺 React/Sampling/当前 API 与启动边界 | REWRITE_REQUIRED，改为最短可执行入口与 canonical docs 索引 |
| `PROJECT_STATUS.md` | OBSOLETE_OR_MISLEADING | 描述 `main`、v0.8-D6、schema 7、345 tests、旧 Web；缺当前 React、schema 8、Sampling、Manual Action、stabilization、Historical Validation | REWRITE_REQUIRED，以当前 HEAD 重新生成事实快照 |
| `docs/AI_HANDOFF.md` | OBSOLETE_OR_MISLEADING | 仍把 D6/schema 7/旧 Web/旧输出和测试规模写成当前；部分安全边界仍重要 | 先提取不变量至新 canonical docs，再归档至 `docs/archive/v1/` |
| `docs/DEVELOPMENT_HISTORY.md` | HISTORICAL_ONLY | 时间线和决策有价值，但天然不代表当前状态 | 迁入 `docs/archive/v1/`，加 `ARCHIVED / NON-NORMATIVE` |
| `docs/PIPELINE_INTEGRATION_AUDIT.md` | PARTIALLY_VALID | Artifact matrix 与审计理由仍有价值；“当前 Paddle 3.5”及 P0 待办已被后续提交解决 | 把现行 contract 提炼进架构/验收文档，原文标记 resolved 后归档 |
| `docs/UX_REDESIGN_GAP_ANALYSIS.md` | HISTORICAL_ONLY | Phase 0 时尚无 React、Python 默认旧 Web；当前已完成 Phase1-3 | 归档为 Phase 0 历史输入 |
| `docs/UX_REDESIGN_SPEC.md` | PARTIALLY_VALID | Review/Sampling、证据、IA 等大量业务语义仍准确；但标题状态、Phase stop points、前端不存在等描述过时 | 将仍有效规范提炼为 `UX_SPEC_V2.md`，原文归档为 V1 重构基线 |
| `docs/HISTORICAL_VALIDATION_CANDIDATES.md` | CURRENT_SUPPORT | 与 baseline/候选/构建约束一致，但它是验证数据 provenance，不是产品需求 | 保留；顶部明确 `VALIDATION SUPPORT / NON-PRODUCT-SPEC` |
| `docs/output_inventory.md` | OBSOLETE_OR_MISLEADING | 9 月 2 日的 output 清单不再等于当前 output/archive 状态 | 归档并在标题标注 snapshot date |
| `docs/search_query_pilot_v0.6-c1.md` | HISTORICAL_ONLY | 9 条 query 验证和来源依据仍有历史价值，但不是完整 106 目标 operational coverage | 归档，知识治理文档只引用其证据结论 |
| `collection_experiment.md` | HISTORICAL_ONLY | 早期 Phase1 实验、OCR 未安装等状态已失效 | 归档 |
| `data/README.md` | CURRENT_CANONICAL（窄范围） | 对 output/SQLite 边界仍准确；范围不足以承担完整架构规范 | 保留并由 `SYSTEM_V2_ARCHITECTURE.md` 引用 |

当前没有一份能够单独作为“V2 当前系统全貌”的 canonical 文档。直到第 13 节建议的文档建立前，当前 code + tests + config 是最高优先级事实源。

## 7. Config / Knowledge Coverage Reality

### 7.1 Coverage 不能合并为一个“已覆盖”指标

| Coverage 层 | 当前事实 | 能说明什么 | 不能说明什么 |
| --- | --- | --- | --- |
| Reference Coverage | `monitor_targets.reference.json` 有 106 个正式目标 | 目标已被建模并带 reference provenance | 不代表可搜索、已启用或已跑过 |
| Operational Coverage | reference 中 5 个 enabled、6 个有 queries、5 个 enabled 且有 queries；共 9 条 queries；development 另有 1 个 enabled 目标、2 条 queries | 当前实际允许进入搜索调度的有限范围 | 不代表 106 个目标已具备运营搜索能力 |
| Claim/Effect Coverage | 5 类：助眠、降压、降脂、减脂、男性相关；共 26 个 exact keywords | 当前 Phase3 能识别的有限页面功效词表 | 不等于完整 Claim Taxonomy 或官方保健功能体系 |
| Evidence→Risk Bridge | 3 条 bridge；覆盖“减肥→weight_loss”“壮阳/补肾→male_function” | 只有明确映射的 Evidence 可进入当前 Risk 路径 | 其余 Effect 没有 bridge，不得近似推断 |
| Risk→Substance | 8 条 verified mappings；3 个 risk categories；3 条 substance_group、5 条 substance | 当前已核验风险类别到物质/物质组关系 | 不代表商品实际检出，也不展开 group 成员 |
| Substance→Method | 5 methods、117 substances、132 method-substance links、37 applicability、1 regulatory context | 当前 Inspection Recommendation 可使用的知识边界 | 不代表每个页面 Evidence 都能桥接到方法 |

补充事实：

- 106 个 Reference 目标中，只有 5 个当前同时 enabled 且有 SearchQuery；“已入 Reference”绝不能写成“已投入运行”。
- `当归` 当前有 query 但 disabled；它证明 query existence 与 operational enablement 是两个状态。
- development 配置的酸枣仁是开发/验证入口，不应被当作正式 Reference coverage 的替代。
- Risk reference 当前覆盖 `anti_fatigue`、`male_function`、`weight_loss`；Effect bridge 实际只触达其中后两类。
- Inspection reference 的 117 substances 全部至少有 method link，但这只表示知识表内部连通，不表示所有业务 Evidence 已覆盖。

### 7.2 明确的 Current Limitations

在 `src/`、`frontend/`、`config/`、`tests/`、`tools/` 中未发现以下当前领域模型：

- `ProductFact` / `declared_origin` / `search_region` 的正式事实实体；
- `HealthFoodIdentity` / 保健食品注册备案号 / 小蓝帽核验模型；
- `ClaimTaxonomy` / `official_function`；
- `seller_location` / `manufacturer_location`。

这些是 V2 路线图中的能力缺口，不是应在审计阶段自由修复的 bug。当前 `region` 只能表达搜索页地区，不得称为、推断为或回填为商品产地。

## 8. Runtime / Generated Data Boundaries

### 8.1 权威边界

| 数据类别 | 权威性质 | 使用规则 |
| --- | --- | --- |
| `output/<run_id>/` 原始页面、图片、OCR、analysis、run metadata | **source of truth for collected evidence** | 只能说明该 run 的真实采集/处理事实；不能自动升级为产品规则、监管结论或知识映射 |
| `inspection_recommendation.json` | 当前知识版本基于 evidence/context 的派生结果 | 可展示和冻结；不是实验室检出结果，知识变化可重新生成 |
| `data/app.db` | **generated index** | 用于跨 run 查询、Review、Sampling；原始采集事实可由 output 重建，不能取代冻结证据 |
| Sampling frozen JSON/XLSX/evidence | 历史清单事实源 | 导出后不依赖 current membership；历史 index 只是检索辅助 |
| `archive/` | 历史备份/取证 | 默认 API 不扫描；不能当当前运行数据或当前设计规范 |
| Historical Validation Set | **test/demo validation data** | 用于稳定离线真实样例验收；不能证明所有商品、目标或页面模板均覆盖 |
| screenshots / logs / OCR output | 单次运行诊断与证据 | 可用于复现事实，不可反向定义 UI、pipeline 或业务状态机 |
| `frontend/dist` | generated deployable asset | 当前 Local API 默认读取，但修改源必须在 `frontend/src` 完成 |

### 8.2 Historical Validation Set

当前存在：

- run id：`historical_validation_20260911`
- 商品数：5
- manifest：`output/historical_validation_20260911/historical_validation_manifest.json`
- purpose：`historical_validation`
- code baseline：`38904fb5c648ea4a6f66b86d6107f387041cbda4`
- `noLiveCollection=true`
- source root：`D:/毕业设计/output`
- Git ignored：是

由于 `DataStore.import_all_runs()` 默认扫描 `output/` 的直接子目录并读取 `web_snapshot.json`，该验证 run **会被当前默认 API 自动导入**。因此 UI 中出现这 5 个商品只能证明验证集已被索引，不应被误认为最新生产采集、当前 operational coverage 或业务默认示例。

当前 `output/` 只看到该验证 run；更多历史 run 位于 `archive/` 或外部稳定目录时，不会被默认 API 自动导入。历史原始目录和验证副本的角色必须在未来架构文档中分别说明。

## 9. Test Suite Audit

### 9.1 当前测试分层

| 层 | 主要覆盖 | 当前性 |
| --- | --- | --- |
| Pipeline | Discovery、StandalonePipeline、Task runtime、Manual Action、mixed-result integration | CURRENT_V2 |
| Detail Collector | PhaseOneCollector、real HTML fixture、adapter contract | CURRENT_V2；fixture 路径需收敛 |
| OCR | 依赖兼容、artifact contract、全失败门槛、共享 runtime 失败诊断 | CURRENT_V2 |
| Phase3/D2-D6 | analysis、risk、bridge、inspection recommendation/runtime | CURRENT_V2；冻结语义不可擅改 |
| DataStore | schema 7→8 migration、Product/Snapshot、readiness、task projection、路径安全 | CURRENT_V2 |
| Review | eligibility、跨 Snapshot、atomic Review+Membership、restore conflict | CURRENT_V2 |
| Sampling | current membership、export、historical frozen list、API | CURRENT_V2 |
| Local API | products、workspace、tasks、assets、review/sampling endpoints | CURRENT_V2 |
| Frontend workflow | typed/presentation/query/router/workflow contract，共 10 个 Node tests | CURRENT_V2，但不是完整组件/浏览器 E2E |
| Typecheck/build | TypeScript 与 production build | CURRENT_V2 |
| Historical Validation builder | 候选校验、hash/provenance、生成集约束，共 6 项 builder tests | CURRENT_SUPPORT |
| `test_web_frontend.py` | V1 原生 Web HTML/CSS/JS，共 15 项 | LEGACY_V1 |

当前共有 38 个 Python test 文件、412 个 Python test methods，另有 10 个前端 workflow test blocks。

### 9.2 关键结论

1. 当前 V2 后端、React contract、Review/Sampling 和 pipeline readiness 已有较完整的确定性测试覆盖。
2. `tests/test_web_frontend.py` 是唯一明确只服务仓库根 `web/` 的测试模块，删除 V1 前必须先移除或迁移其仍有价值的 contract assertions。
3. schema 7→8 测试是当前 migration contract，不是“仍依赖旧 schema”；应保留。
4. 独立 JSON contract 的 `schema_version=1/2/3` 与 SQLite `SCHEMA_VERSION=8` 属于不同命名空间，不能按数字做机械清理。
5. `tests/test_real_collector_fixtures.py` 对历史 run 目录存在硬编码/位置耦合：真实源被移动到 archive 或外部根后，标准工作区可能缺 fixture；Historical Validation builder 可以使用显式 source override，但当前测试入口还需要在 V2-0 cleanup 中收敛成稳定 fixture 解析策略。
6. 当前 React 缺少组件级和本地浏览器级自动化；现有 workflow test 更接近纯 domain/contract 测试。V2-1 的视觉与交互收口不能只靠旧 `web/` 测试替代。
7. 本轮没有运行测试：审计任务要求只读，部分 DataStore/API 测试会创建临时数据，且不需要以测试执行重新证明引用关系。最近在当前代码基线上完成的全量结果应由未来 `CURRENT_SYSTEM_STATUS.md` 记录，不应从旧 `PROJECT_STATUS.md` 的 345 项推断。

## 10. Safe Delete Candidates

本轮不删除。按“0 runtime refs / 0 build refs / 0 test refs，可重建或 Git history 已保留”计，共 **5 组**：

| Candidate | Runtime refs | Build refs | Test refs | 依据/前置条件 |
| --- | ---: | ---: | ---: | --- |
| `.figma/` | 0 | 0 | 0 | untracked 本地视觉参考；确认不再需要人工对照后删除 |
| `.gitattributes` | 0 | 0 | 0 | untracked Figma 生成文件；不属于当前仓库 contract |
| `src/__pycache__/` | 0 | 0 | 0 | Python 自动重建 cache |
| `tests/__pycache__/` | 0 | 0 | 0 | Python 自动重建 cache |
| `tools/__pycache__/` | 0 | 0 | 0 | Python 自动重建 cache |

`web/` **不在本表**，因为有 15 个直接 test refs 和多个文档/fallback 引用。`frontend/dist` 也不在本表，因为当前 Local API 默认依赖其存在；它虽可重建，却是运行静态入口。`.idea/` 属于用户 IDE 状态，需人工决定。

## 11. Archive Candidates

本轮不移动。建议未来统一迁入 `docs/archive/v1/` 并在顶部写明 `ARCHIVED / NON-NORMATIVE`，共 **9 组**：

1. `collection_experiment.md`
2. `docs/AI_HANDOFF.md`（先提取永久不变量）
3. `docs/DEVELOPMENT_HISTORY.md`
4. `docs/PIPELINE_INTEGRATION_AUDIT.md`（先提取当前 artifact/readiness contract，并标记问题已解决）
5. `docs/UX_REDESIGN_GAP_ANALYSIS.md`
6. `docs/UX_REDESIGN_SPEC.md`（先提取仍有效业务/UX 语义）
7. `docs/output_inventory.md`
8. `docs/search_query_pilot_v0.6-c1.md`
9. `ui/` 六张 V1 截图

`docs/HISTORICAL_VALIDATION_CANDIDATES.md` 暂不归档：builder 仍在当前 support 链使用它记录候选和 provenance。`web/` 属于待解除依赖的 Legacy 代码，不计入本轮 archive candidate 数量。

## 12. Rewrite Candidates

### 12.1 `README.md`

必须重写为可执行的项目入口，至少包含：

- 当前 backend/frontend 启动方式与前置依赖；
- Python 3.10 与锁定 OCR 环境；
- `frontend/` 是当前 UI、`frontend/dist` 是生成物；
- 当前三大页面与不做违法/检出结论的产品边界；
- output/SQLite/frozen export 的权威关系；
- canonical docs 索引；
- 测试命令及哪些测试会写临时目录。

不应继续详细复制阶段状态、表数量、测试数量或完整架构；这些应链接到专门文档。

### 12.2 `PROJECT_STATUS.md`

必须以当前 HEAD 重新生成，至少记录：

- 当前 branch/基线、schema 8、React 版本和三大页面；
- Detail→OCR→Phase3→Recommendation→Review readiness；
- Review/Sampling transaction 和 frozen export；
- 固定 OCR 环境与 Historical Validation Set；
- 当前测试分层与最近一次真实验收；
- 已知限制、下一阶段以及明确 non-goals。

它只能描述“现在已经是什么”，不得混入未来路线图或把历史 phase 当当前状态。

### 12.3 其它需要局部重写/加状态头的文件

- `docs/HISTORICAL_VALIDATION_CANDIDATES.md`：加非产品规范声明；
- `data/README.md`：保留内容，未来补 frozen sampling 与 import 范围链接；
- 归档文档：统一加 archive 状态、原始日期、适用 baseline 和替代文档链接。

## 13. Proposed Canonical Documentation Architecture

本轮不创建以下文件。建议未来结构和职责如下：

```text
AGENTS.md

docs/
├─ CURRENT_SYSTEM_STATUS.md
├─ PRODUCT_REQUIREMENTS_V2.md
├─ SYSTEM_V2_ARCHITECTURE.md
├─ DOMAIN_MODEL_V2.md
├─ UX_SPEC_V2.md
├─ KNOWLEDGE_GOVERNANCE.md
├─ IMPLEMENTATION_ROADMAP_V2.md
├─ TEST_ACCEPTANCE_V2.md
├─ decisions/
└─ archive/
   └─ v1/
```

| Document | 目的 / Source of Truth | 应包含 | 不应包含 / 与其它文档关系 |
| --- | --- | --- | --- |
| `AGENTS.md` | 约束所有自动化开发行为；仓库级操作规则 SoT | 技术基线、source priority、永久边界、禁止改动、验证矩阵 | 不复制产品需求或实现状态；链接下列 canonical docs |
| `CURRENT_SYSTEM_STATUS.md` | 当前已实现事实的人工可读快照 | 基线、入口、版本、schema、功能、测试、已知限制、最新真实验收 | 不写愿景；每个 release/gate 更新，以 code/tests 为最终校验 |
| `PRODUCT_REQUIREMENTS_V2.md` | 产品目标与业务语义 SoT | 用户、场景、核心术语、in/out of scope、验收语义、非结论边界 | 不规定表结构、组件或算法；架构/UX 必须满足它 |
| `SYSTEM_V2_ARCHITECTURE.md` | 当前/目标技术结构 SoT | 运行入口、模块所有权、pipeline artifact contract、transaction、文件/DB 边界、部署 | 不定义视觉细节或知识事实；引用 Domain 与 ADR |
| `DOMAIN_MODEL_V2.md` | 实体与状态语义 SoT | Task/Product/Snapshot/Evidence/Review/Membership/List/Future Fact/Identity/Claim 的 identity、scope、provenance、关系 | 不写页面布局；schema 变更必须先对齐该文档和 ADR |
| `UX_SPEC_V2.md` | 当前 V2 IA 与交互 SoT | 页面层级、presentation mapping、空/错/加载状态、可访问性、响应式、review/sampling 用户流程 | 不复刻后端规则；引用 API/domain contracts，不自行推导 eligibility |
| `KNOWLEDGE_GOVERNANCE.md` | Reference/Risk/Bridge/Method 数据治理 SoT | 来源等级、核验、版本、coverage 指标、变更审批、禁止推断、gap 表达 | 不存具体运行结果；配置数据仍是具体记录 SoT |
| `IMPLEMENTATION_ROADMAP_V2.md` | 未完成工作的排序与 gate SoT | phase、依赖、风险、决策点、退出条件 | 不宣称 feature 已实现；完成项回写 Current Status |
| `TEST_ACCEPTANCE_V2.md` | 变更类型到验证要求的 SoT | 单测/集成/typecheck/build/视觉/E2E/数据验收矩阵和 fixture 规则 | 不嵌入易变测试数量；由 CI/命令结果给执行事实 |
| `docs/decisions/` | 不可逆/重大取舍的 ADR | 背景、决策、替代方案、后果、日期、关联代码 | 不替代当前状态；若 superseded 必须显式链接 |
| `docs/archive/` | 历史上下文 | 原文、baseline、归档日期、替代规范链接 | 永不作为当前实现指令或优先依据 |

建议权威关系：

```text
Current code/tests/config
  -> 校验 CURRENT_SYSTEM_STATUS
PRODUCT_REQUIREMENTS_V2
  -> 约束 DOMAIN_MODEL + SYSTEM_ARCHITECTURE + UX_SPEC
KNOWLEDGE_GOVERNANCE
  -> 约束 config/Reference/Risk/Bridge/Method 数据变更
IMPLEMENTATION_ROADMAP
  -> 安排尚未实现的 change set
TEST_ACCEPTANCE
  -> 定义每类 change set 的 gate
decisions/
  -> 记录重大取舍及 supersession
archive/
  -> 仅解释历史，不参与当前规范冲突裁决
```

## 14. Proposed AGENTS.md Rules

本轮不创建 `AGENTS.md`。建议内容框架如下。

### 14.1 Technical Baseline

- CPython 3.10.x；当前验证环境 3.10.0；
- 本地标准库 HTTP server + SQLite DataStore；
- Playwright/Chrome 采集与统一 ManualActionGate；
- OCR 固定 `paddlepaddle==3.2.0`、`paddleocr==3.7.0`、`paddlex==3.7.2`、PP-OCRv6、bos、CPU；
- Phase3/D2-D6 和当前 InspectionRuntime 是冻结核心；
- React 19 + TypeScript 7 + Vite 8 + Tailwind 4 + Lucide React；
- openpyxl 只用于 Sampling XLSX export；
- output 是采集事实，SQLite 是可重建索引，历史 Sampling 冻结文件是清单事实。

### 14.2 Source Priority

冲突时按以下顺序裁决：

1. Current code + tests + current governed config
2. `CURRENT_SYSTEM_STATUS.md`
3. `PRODUCT_REQUIREMENTS_V2.md`
4. `SYSTEM_V2_ARCHITECTURE.md`
5. `DOMAIN_MODEL_V2.md`
6. `UX_SPEC_V2.md`
7. `KNOWLEDGE_GOVERNANCE.md`（知识变更场景优先于实现便利）
8. `IMPLEMENTATION_ROADMAP_V2.md`
9. ADR（仅在未 superseded 且适用当前 baseline 时）
10. `archive/` 永不作为当前规范

发现上层文档与代码冲突时，不得静默选择；先报告事实和建议修订对象。

### 14.3 Permanent Safety / Business Boundaries

- 系统只提供风险线索、证据组织和抽检辅助建议，不认定违法；
- 页面文字、OCR、Risk Mapping 和 Recommendation 均不等于实验室实际检出；
- seller-managed 与 UGC Evidence 必须分离，不能互相替代；
- Review 是 Snapshot 级人工结论，Sampling Membership 是 Product 级当前清单关系，两者实体分离；
- 原始 output 保留事实和失败诊断，SQLite 不成为唯一副本；
- Recommendation 不是 Review eligibility 的硬前提，Phase3 analysis 才是核心前提；
- 搜索发现不等于完成分析，不得进入正常 Review Queue；
- 搜索页地区不等于商品产地、卖家位置或生产地；
- Knowledge Gap 必须显式展示，不得用虚假 mapping 填空。

### 14.4 Forbidden Autonomous Changes

未经明确批准不得：

- 改 SQLite schema、migration 或实体 identity；
- 扩大/猜测 Effect→Risk、Risk→Substance、Substance→Method 映射；
- 改变 Phase3、D2-D6、Reference 或 Risk 语义；
- 改 Taobao DOM 策略或真实采集算法来掩盖上游 contract 错误；
- 把 `region` 重命名/推断为 `declared_origin`；
- 把蓝帽图片线索单独认定为官方保健食品身份；
- 按近义词、LLM 猜测或 UI 需求自动建立官方功能/Claim 映射；
- 让 React 跨 mutation 自行承担 Review+Membership 原子性；
- 把 output、截图、旧文档或 validation fixture 当产品规范；
- 删除/重写历史证据、Reference provenance 或 frozen export；
- 使用 `git add .`，提交 `.figma/`、环境、运行数据或 build cache。

### 14.5 Required Validation Matrix

| Change type | 最低验证 |
| --- | --- |
| Python utility/contract | 定向 unittest + 相关 integration |
| Pipeline stage/artifact | 阶段单测 + mixed-result integration + failure artifact assertions |
| OCR dependency/runtime | clean Python 3.10 env resolution + OCR tests + historical fixture；批准后才做极小真实 E2E |
| DataStore/API | migration/old-data preservation + path safety + DTO/filter tests + full unittest |
| Review/Sampling | transaction、跨 Snapshot、restore conflict、frozen history tests |
| React/domain | frontend workflow + typecheck + production build |
| UX presentation | 上述前端验证 + 1440/1080 本地视觉验收 + loading/error/empty/long content |
| Knowledge config | schema validation + provenance + referential integrity + no inference + domain tests +人工审阅 |
| Collector/DOM | fixture regression；明确批准后单商品真实 E2E，不批量试错 |
| Documentation only | 链接、版本、术语和 code fact 一致性检查；显式限定 normative status |

## 15. Proposed V2 Roadmap

本节只给依赖和 gate，不实施任何 Phase。

| Phase | Scope | Dependency | Major risks | Schema impact | Data requirements | Real-world validation requirements |
| --- | --- | --- | --- | --- | --- | --- |
| V2-0 | Workspace convergence + canonical docs | 当前 audit | 删除仍有测试依赖的 V1；新旧规范并存 | 无 | 当前 code/config/test/runtime inventory | 新开发者仅按 canonical docs 能启动、定位权威并解释边界 |
| V2-1 | 核心 UX 收口：缩略图、整行/卡片点击、Snapshot 摘要、Evidence source grouping、inline preview/lightbox、未分析/0 Evidence/未桥接/Recommendation unavailable 分态 | V2-0 | 前端自行推导 readiness；大图性能；把 0 evidence 当失败 | 原则上无；只做 presentation/API additive 字段时也需 contract 审核 | 当前 5 商品 validation set + empty/error/UGC-only/0-evidence fixtures | 1440/1080 本地验收；长标题、缺图、历史 Snapshot、失败态；不访问外站即可完成首轮 |
| V2-2 | ProductFact 基础，首批 `declared_origin`；预留 category/form/ingredients/registration no | V2-0，最好 V2-1 稳定后 | 把搜索地区/卖家地址推断为产地；事实覆盖 Snapshot | 预计 additive：Snapshot-scoped fact/evidence/provenance；需 ADR | 多页面模板的明确产地声明、原文与位置证据、unknown 样例 | 经批准的小样本真实商品跨模板验证；证明“不存在时为空”而非补占位 |
| V2-3 | Health Food Identity：蓝帽线索、注册/备案号、官方身份核验、官方登记功能 | V2-2 | logo 假阳性、盗图、号与商品不匹配、官方源变化 | 预计 additive identity/verification/provenance 表或冻结 artifact；先定 Domain Model | 页面图文线索 + 官方注册/备案数据 + 正反例 | 对官方数据库逐项核验；仅 logo 不得判定 identity |
| V2-4 | Monitor Coverage：106 正式目标的 Operational SearchQuery 扩展 | V2-0 + Knowledge Governance | 搜索词误召回、频率/登录风险、把 reference 误当 enabled | 可能无需 schema；配置版本/状态足够时保持 | 每目标 query 证据、召回样例、enable 审批、频率策略 | 分批 query pilot，不一次启用 106；记录成功/阻断/误召回 |
| V2-5 | Claim Taxonomy：页面 Claim、官方保健功能、疾病/治疗宣传、监管风险线索分层 | V2-2 + V2-3 | 概念混同、近似词自动映射、法规时效 | 预计新增 governed taxonomy/config；若持久化识别结果则 additive entities/index | 标注语料、官方术语、negative/ambiguous samples、版本 provenance | 双人/人工抽样复核，报告 precision/coverage/unknown；不追求自动填满 |
| V2-6 | Health Food Claim Consistency：页面声称 vs 官方登记功能 | V2-3 + V2-5 | 把“不一致线索”写成违法结论；身份错配传染 | 可能新增 comparison artifact/index；先 ADR 决定文件事实与 DB 索引 | 已核验 identity、官方功能、页面 claims、不可比较样例 | 对官方记录逐商品重建；展示证据与“不足以判定”边界 |
| V2-7 | Inspection Knowledge Coverage：Evidence→Risk→Substance→Method 扩展 | V2-5 + Governance | 为覆盖率造 mapping、来源等级下降、组成员猜测 | 优先复用现有 config/schema；确需新关系时 additive + migration gate | 官方/权威来源、逐条 provenance、gap inventory | 每条 mapping 人工核验；当前 5/117/132 数量不作为扩张目标本身 |
| V2-8 | Knowledge Base UI | V2-5 + V2-7 | UI 把 reference 可用性表现成商品结论；编辑权限不清 | 只读 API/UI可无 schema；治理工作流另立设计 | 版本化 Reference/Risk/Bridge/Method、来源与 gap | 权限、provenance、历史版本、空状态和交叉链接验收 |
| V2-9 | Analytics | V2-2/5/6/7 数据语义稳定 | 小样本误导、候选与已分析混算、历史 membership 清空后口径错 | 可能需要 additive read model/index；不可牺牲事实模型 | 指标字典、denominator、时间窗、失败/unknown 处理、足量真实 run | 每个数字可回溯到 Product/Snapshot/Review/frozen list；与手工样本对账 |
| V2-10 | 论文实验与评价 | V2-0 至 V2-9 的选定范围冻结 | 数据泄漏、选择偏差、把辅助线索当检测准确率 | 不应改生产 schema；独立实验数据/结果 | 冻结数据集、标注规范、baseline、指标、复现实验环境 | 可重复脚本、人工标注一致性、误差分析、限制声明、真实案例审阅 |

## 16. Risks Before V2 Development

按优先级列出：

### P0

1. **规范权威冲突**：README/PROJECT_STATUS/AI_HANDOFF 的活跃文件名会让新 Agent 优先读取旧 Web、schema 7、旧 IA 和已解决问题。
2. **V1 删除时机错误**：`web/` 已是 Legacy，但 15 项测试和显式 fallback 尚未解除；直接删除会造成测试回归并丢失已承诺的回退路径。
3. **运行产物误作需求**：当前 API 自动导入 Historical Validation Set；若不标记，5 个样例可能被误当生产数据、默认品类或完整 coverage。
4. **数据权威混淆**：output、SQLite、Recommendation、frozen sampling 各自权威范围不同；未来 ProductFact/Identity 若不先定义事实层，容易把派生值写成原始事实。
5. **远端命名疑点**：配置的 origin 仓库名尾部带 `-`，与项目说明不一致；未来 push/PR/文档链接前需确认真实远端身份。

### P1

6. **测试 fixture 路径漂移**：real collector fixture 测试依赖旧 run 位置；archive/output 收敛前要先建立稳定 fixture root。
7. **前端验收缺口**：当前 React 有 workflow/typecheck/build，但旧 Web 视觉测试不能证明当前组件行为；V2-1 需建立最小当前 UI 验收。
8. **Coverage 误读**：106 targets、117 substances、132 links 容易被展示为“已运营/已识别/已检出”；所有指标必须带层级与 denominator。
9. **未来实体尚未建模**：ProductFact、HealthFoodIdentity、ClaimTaxonomy 不存在；不得用现有 `region`、OCR 文本或 Effect 字段临时代替。
10. **历史文档缺少 non-normative 标签**：同一术语在 Phase 0 设计、集成 audit 和当前代码中含义可能不同，全文检索会命中错误时代的规则。

### 当前最容易误导 Codex 的五类来源

1. `PROJECT_STATUS.md`：文件名暗示当前状态，但内容停留在 v0.8-D6/schema 7/旧 Web/345 tests。
2. `README.md`：通常是第一入口，却把根 `web/` 与旧 IA 写成现行产品。
3. `docs/AI_HANDOFF.md`：以 handoff 口吻给出过期的运行和实现指令，权威感强于实际时效。
4. `web/`、`ui/` 和未跟踪 `.figma/` 并存：三套视觉/IA 痕迹可能被误认为当前实现、目标实现或可复制组件。
5. 未加状态头的 Phase/audit/runtime 资料：`UX_REDESIGN_*`、`PIPELINE_INTEGRATION_AUDIT.md`、`output/`、`archive/`、`data/app.db` 各含真实内容，但分别是历史设计、已解决审计、运行证据、备份和索引，均不能单独定义当前产品。

## 17. Recommended V2-0 Cleanup Actions

以下动作都需要单独批准，本轮未执行：

1. 先确认 `origin` 真实仓库名和 `main...ux-redesign-v1` 的 1/16 分叉处理策略，避免在文档收敛后推错远端或误合并。
2. 创建 `AGENTS.md`，只写第 14 节的长期规则、source priority、禁止项和验证矩阵。
3. 创建 `docs/CURRENT_SYSTEM_STATUS.md`，以当前 code/tests/config 和稳定验证结果重建“现在是什么”。
4. 创建 `PRODUCT_REQUIREMENTS_V2.md`、`SYSTEM_V2_ARCHITECTURE.md`、`DOMAIN_MODEL_V2.md`，先冻结事实/索引/派生结果和 Review/Sampling/未来 ProductFact 的边界。
5. 从 `docs/UX_REDESIGN_SPEC.md` 提炼仍有效的 IA、Review/Sampling、Evidence 与 presentation 规则，形成 `UX_SPEC_V2.md`；不要直接复制过时 phase 状态。
6. 创建 `KNOWLEDGE_GOVERNANCE.md`，明确 Reference/Operational/Claim/Risk/Method 五层 coverage、来源等级和禁止推断规则。
7. 创建 `IMPLEMENTATION_ROADMAP_V2.md` 与 `TEST_ACCEPTANCE_V2.md`，分别只管未来顺序和验收，不混入当前状态。
8. 重写 `README.md` 和 `PROJECT_STATUS.md`，使新开发者的第一入口只指向当前 React、schema 8、锁定 OCR 和 canonical docs。
9. 给 `docs/HISTORICAL_VALIDATION_CANDIDATES.md` 增加 non-product-spec 标记，并在 Current Status 中说明 validation run 会被默认 API 导入。
10. 解决 `tests/test_real_collector_fixtures.py` 的历史路径耦合；固定为受控 fixture 或显式环境变量，并验证默认离线测试可重复。
11. 盘点 `tests/test_web_frontend.py` 的 15 项：删除纯 V1 presentation assertions，仅将仍有效的业务 contract 迁移到当前 frontend/backend tests。
12. 明确取消 V1 fallback 后，删除 `web/`；在该提交中同步清除 runtime/doc/test references，并证明 `0 runtime refs / 0 build refs / 0 test refs`。
13. 把第 11 节的 9 组历史材料迁入 `docs/archive/v1/`，统一添加 `ARCHIVED / NON-NORMATIVE`、原 baseline 和替代规范链接。
14. 经用户批准后清理第 10 节的 5 组 Safe Delete 项；对 `.idea/` 单独询问，不混入业务清理。
15. 在干净 checkout 中运行 Python 全量 unittest、frontend workflow、typecheck、build 和 Historical Validation builder 定向测试，记录到 `CURRENT_SYSTEM_STATUS.md`。
16. 完成一次仅使用 canonical docs 的“新 Agent 冷启动演练”：要求其准确说出入口、三大页面、schema 8、readiness、Review/Sampling、数据权威与 V2-1 scope；全部正确后才将 V2-0 标记完成。
17. V2-0 Gate 通过后再开始 V2-1；不得借 workspace cleanup 提前实现 ProductFact、产地、蓝帽、Claim Taxonomy、Knowledge Coverage 或 Analytics。

---

审计边界声明：**本轮未删除、移动或修改任何现有业务文件。**唯一新增文件为本审计报告。
