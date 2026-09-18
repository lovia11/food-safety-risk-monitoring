# V2-B4 Sleep Direction Vertical Slice

> 状态：implementation gate pending local test acceptance
>
> 日期：2026-09-18
>
> 数据版本说明：本文记录 sleep slice 在 Risk Reference c4 时的实现快照；后续 B4 已继续扩充至 c6，本文中的 c4 总量不是当前全库库存。

## 1. 本切片解决的问题

本切片针对真实产品工作流中的明确断链：

```text
页面 Evidence
  → 已识别 sleep_related Claim
  → 抽检辅助建议仍显示未映射
```

B4 不通过扩大 Claim 类型来“填满 UI”，而是按既定治理链补齐：

```text
exact Claim expression
  → ClaimInspectionBridge
  → source-backed Risk mapping
  → concrete Substance
  → persisted Method
  → Product Context / regulatory context
  → human review
```

## 2. 睡眠表达的分档治理

本切片不再把“只有官方逐字表述才能进入 Risk”作为唯一门槛，而是按表达是否明确作出睡眠功效/结果声称分档。

### A. 官方/过渡功能名称

进入 production Bridge：

- `改善睡眠`
- `有助于改善睡眠`

项目的受治理 HealthFunction 数据已经记录：

```text
历史/过渡名称：改善睡眠
        ↓ official_transition_name
当前官方功能：有助于改善睡眠
```

### B. 明确睡眠功效表达

同样进入 production Bridge：

- `助眠`
- `安睡`
- `好眠`
- `深睡`
- `催眠`

依据不是“这些词和改善睡眠长得像”，而是历史中央专项抽检资料明确规定：非法添加项目根据“声称的功能（包括批准和虚假宣传）”确定。上述词在 seller-managed 页面中命中时，本身明确表达睡眠改善、促进或结果性功效，因此可进入同一个“改善睡眠”监管筛查场景。

这类关系使用：

```text
governance_basis = governed_functional_scope
```

仍然逐 expression 显式治理，不按整个 `sleep_related` 类型外推。

### C. 宽泛主题、症状或更宽传统表述

继续 Claim-only：

- `睡眠`
- `入睡`
- `失眠`
- `辗转反侧`
- `安神`

这些词单独出现时不足以确认商品在作出“改善睡眠”功效声称。例如“难入睡”描述问题本身，“安神”的传统表述范围也大于睡眠，因此不能仅凭单词自动触发具体检测物质。

## 3. 监管来源依据

核心历史来源：

- 全国食品保健食品欺诈和虚假宣传整治工作领导小组办公室
- 《食品保健食品欺诈和虚假宣传整治问答》
- SAMR 现存官方 PDF：
  `https://www.samr.gov.cn/cms_files/filemanager/1647978232/attach/20233/P020181214555096215303.pdf`

来源中的保健食品检验项目表明确把“改善睡眠类样品”作为类别、声称类别，并列出相应检验项目。食品风险监测表又列出“声称改善睡眠类样品”及同类项目。

同一资料备注明确：非法添加项目根据声称的功能（包括批准和虚假宣传）确定。

该来源属于 2018 年专项整治/历史抽检监测语境，因此项目治理为：

- `basis_type = historical_sampling_plan`
- `temporal_status = historical`
- `evidence_grade = B`

不得显示为 2026 当前统一法定抽检项目。

## 4. Risk Reference 扩充

`config/risk_substance_reference.json`：

- dataset version：`2026.09-c4`
- 新增 `sleep_aid` historical mappings：21 条
  - 1 条来源集合 mapping
  - 20 条具体 Substance mapping

来源表还点名“氯氮䓬、马来酸咪达唑仑”；当前 Inspection Reference 尚无对应已核验实体，本切片不自行补实体、不猜 CAS、不从 Method 反推，因此暂不展开为具体 Substance mapping。

20 个具体 Substance 均必须同时满足：

1. 历史来源直接点名；
2. 当前 `inspection_reference.json` 已存在同一 Substance 实体；
3. 存在可追溯 source basis；
4. 不由药理知识或方法标题推断。

## 5. B3 allowlist 补强

实施 B4 时发现，B3 原实现只能让 historical Bridge 授权一个 `reference_mapping_id`，不足以把“来源集合 + 多个具体 Substance mapping”选择性带入 KnowledgeTrace。

因此 B3 做最小补强：

```json
"authorized_historical_mapping_ids": [...]
```

约束：

- `current_only` 必须为空数组；
- `historical_reference_allowed` 必须包含主 `reference_mapping_id`；
- 所有授权 mapping 必须：
  - 同一 `risk_category`
  - `historical_sampling_plan`
  - `temporal_status=historical`
  - 与主 reference 同 `source_reference`
  - 同 `source_date`
  - 同 `product_scope`

Runtime 只将这个 allowlist 加入 KnowledgeTrace，不开放整个 `sleep_aid` 历史类别。

## 6. Method 与 Product Context

当前 Inspection Reference 已覆盖本次展开的 20 个睡眠相关 Substance，其中：

- BJS 201710 覆盖当前展开的 20 个 Substance；
- KJ201903 覆盖巴比妥、苯巴比妥、异戊巴比妥、司可巴比妥；
- GB/T 45443-2025 覆盖褪黑素。

Method 存在不等于 Method 对任意商品都适用。

最终状态仍由 Product Context / applicability 决定：

- applicable / conditional → 可形成相应辅助建议；
- insufficient context → `needs_context_review`；
- not applicable → 不进入 suggested methods。

## 7. 褪黑素边界

褪黑素保留历史筛查来源关系，但它同时存在受治理的合法保健食品原料语境。

因此：

```text
sleep Claim
  → historical sleep_aid reference
  → 褪黑素
  ≠ 疑似非法添加褪黑素
```

Runtime 必须进入：

```text
regulatory_context_review
```

要求人工核对：

- 商品身份
- 是否保健食品
- 注册/备案
- 配料/原料
- 具体产品上下文

在完成这些核对前，不直接输出普通 `suggest_testing`。

## 8. 用户可见验收标准

对于页面 seller-managed Evidence 明确包含：

```text
有助于改善睡眠
```

新的正确结果不能再是：

```text
尚未建立该宣传与检测关注方向之间的可靠关系
```

应进入：

```text
sleep_related Claim
  → sleep_aid
  → 含历史筛查参考
  → 具体 Substance follow-ups
  → 已核验 Method / 需补上下文
```

同时必须显示 historical disclosure：

> 该关注方向依据历史中央专项抽检/风险监测资料，用于抽检筛查参考；不表示当前统一法定抽检项目，也不表示该商品实际含有相关物质。

对于“安睡整个夜晚”“助眠”“深睡”等明确功效表达，应进入 sleep_aid 并形成后续 Substance/Method 研判。

对于仅命中“睡眠”“难入睡”“失眠”“辗转反侧”“安神”等宽泛或症状表达的页面，仍不自动生成 sleep_aid 抽检建议；这是明确的表达粒度边界，不是旧链路 fallback。

## 9. Gate

定向后端：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_claim_inspection_bridge tests.test_risk_substance_reference_data tests.test_v2b3_temporal_governance tests.test_inspection_knowledge tests.test_inspection_signal_trace tests.test_inspection_recommendation tests.test_inspection_runtime_claim_v2
```

全量后端：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

前端：

```powershell
Set-Location frontend
npm run test:workflow
npm run typecheck
npm run build
```

Gate 通过后，本 sleep vertical slice 才可标记为 accepted。
