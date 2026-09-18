# V2-B4 Cardiometabolic Risk Expansion

> 状态：implementation gate pending local test acceptance
> 日期：2026-09-18
>
> 数据版本说明：本文记录 cardiometabolic slice 在 Risk Reference c5 时的实现快照；后续 B4 已继续扩充至 c6，本文中的 8/46/54 等数字只描述该阶段，不是当前全库库存。

## 1. 范围

本切片继续 B4 Risk→Substance 扩充，覆盖：

- `blood_pressure` — 辅助降血压
- `blood_lipid` — 辅助降血脂
- `blood_glucose` — 辅助降血糖

不改变 B3 historical/current governance，不提前执行 B5 Method shortlist 深核。

## 2. 官方来源

核心历史来源仍为市场监管总局现存《食品保健食品欺诈和虚假宣传整治问答》。

来源中的保健食品监督抽检/风险监测表明确按类别、声称类别配置检验项目：

- 辅助降血糖类样品 → 甲苯磺丁脲、格列本脲、格列齐特、格列吡嗪、格列喹酮、格列美脲、马来酸罗格列酮、瑞格列奈、盐酸吡格列酮、盐酸二甲双胍、盐酸苯乙双胍、盐酸丁二胍、格列波脲；
- 辅助降血压类 → 阿替洛尔、盐酸可乐定、氢氯噻嗪、卡托普利、哌唑嗪、利血平、硝苯地平、氨氯地平、尼群地平、尼莫地平、尼索地平、非洛地平；
- 辅助降血脂类样品 → 监督抽检列洛伐他汀、辛伐他汀、烟酸，风险监测另列美伐他汀、去羟基洛伐他汀、洛伐他汀羟酸钠盐。

同一资料备注要求根据“声称的功能（包括批准和虚假宣传）”确定非法添加项目。

这些关系治理为：

```text
basis_type = historical_sampling_plan
temporal_status = historical
evidence_grade = B
```

不得展示成当前统一法定抽检目录。

## 3. Claim→Risk 表达治理

### 血压

进入 Bridge：

- `辅助降血压` — official transition name
- `调节血压` — official transition name
- `有助于维持血压健康水平` — current official function wording
- `降压` — governed functional scope

继续 Claim-only：

- `血压`
- `高血压`

### 血脂

进入 Bridge：

- `辅助降血脂`
- `调节血脂`
- `有助于维持血脂（胆固醇/甘油三酯）健康水平`
- `降脂`

继续 Claim-only：

- `血脂`
- `胆固醇`
- `有助于维持血脂健康水平`（项目中的 manual-curated 简写，不等同当前官方功能全称）

### 血糖

进入 Bridge：

- `辅助降血糖`
- `调节血糖`
- `有助于维持血糖健康水平`
- `降糖`

`blood_glucose_related` 当前没有把宽泛 `血糖` 或疾病词 `糖尿病` 录入 production taxonomy，因此不产生整类自动桥接问题。

## 4. c5 Risk Reference

`config/risk_substance_reference.json` 升级为 `2026.09-c5`。

新增 25 条 historical mappings：

- blood_pressure：12 = 1 group + 11 concrete substances
- blood_lipid：5 = 1 group + 4 concrete substances
- blood_glucose：8 = 1 group + 7 concrete substances

加上 c4：

```text
current mappings     = 8
historical mappings  = 46
total mappings       = 54
historical categories = 4
```

## 5. 为什么没有把来源表全部机械录入

### 5.1 当前 Inspection Reference 缺实体

本切片不猜 CAS、不凭药名自行补实体。

暂未展开：

- blood_pressure：盐酸可乐定
- blood_lipid：去羟基洛伐他汀
- blood_glucose：格列本脲、马来酸罗格列酮、盐酸吡格列酮、盐酸二甲双胍、盐酸苯乙双胍、盐酸丁二胍

这些条目保留为来源集合中的知识缺口，后续由 B5 方法/物质深核决定是否进入 Inspection Reference。

### 5.2 烟酸

烟酸虽然被历史辅助降血脂抽检表点名，但它同时存在正常营养素/食品强化语境。

当前 Inspection Reference 尚未建立烟酸的 `substance_regulatory_context`，因此本切片不把烟酸展开成商品级 concrete Risk mapping。

处理原则与褪黑素一致：先治理合法/条件性语境，再决定商品级 follow-up 状态，不能把历史抽检表机械解释成非法添加清单。

## 6. Runtime 预期

### 示例 1

```text
页面：“帮助降压”
→ blood_pressure_related
→ blood_pressure
→ historical screening reference
→ 11 个已治理 Substance
→ Method / Product Context
```

### 示例 2

```text
页面：“辅助降血脂”
→ blood_lipid
→ 4 个 concrete Substance
→ 不自动包含烟酸
```

### 示例 3

```text
页面：“降糖”
→ blood_glucose
→ 7 个 concrete Substance
→ 不凭来源名称伪造盐酸二甲双胍等缺失实体
```

## 7. Audit 边界

c5 historical mappings 进入知识库存和 V2 Claim runtime，但不进入 current-only 覆盖率分母。

因此 inspection knowledge audit 仍应保持：

- current Risk mappings = 8
- current explicit concrete mappings = 5
- current end-to-end reachability denominator = 5

新增 historical mappings 只能增加 historical inventory，不得抬高 current coverage 指标。

## 8. Gate

定向后端：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_claim_inspection_bridge tests.test_risk_substance_reference_data tests.test_v2b3_temporal_governance tests.test_inspection_knowledge tests.test_inspection_signal_trace tests.test_inspection_recommendation tests.test_inspection_runtime tests.test_inspection_runtime_claim_v2 tests.test_knowledge_read_api tests.test_inspection_knowledge_audit
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

本切片只有在本地 Gate 通过后才标记 accepted。
