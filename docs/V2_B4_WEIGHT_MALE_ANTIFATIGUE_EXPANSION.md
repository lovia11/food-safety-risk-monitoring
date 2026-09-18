# V2-B4 Weight / Male / Anti-Fatigue Expansion

> 状态：Accepted — full backend/frontend gate passed on 2026-09-18
> 日期：2026-09-18

## 1. 范围

本切片完成 B4 剩余三个方向：

- `weight_loss` — 减肥 / 体重管理
- `male_function` — 补肾壮阳 / 男性功能
- `anti_fatigue` — 抗疲劳 / 缓解体力疲劳

完成后 Risk Reference 升级到 `2026.09-c6`，Claim Inspection Bridge 升级到 `claim-inspection-bridge-v2.5`。

## 2. B3 temporal policy 补强

B4 实施过程中确认：同一 exact Claim 可能同时拥有 current 主证据与 historical screening 补充。由于一个 expression 不能重复配置两条 Bridge，仅有 `current_only` / `historical_reference_allowed` 两种 policy 不足以表达该情况。

因此新增：

```text
current_plus_historical_reference_allowed
```

语义：

```text
exact Claim
  → current primary Risk reference
  + explicit historical mapping allowlist
  → resolver 保留全部 current mappings
  + 仅加入 allowlist 中的 historical mappings
```

禁止全局打开 historical；historical allowlist 仍必须属于同一 risk category、historical_sampling_plan，并保持单一历史来源批次。

## 3. weight_loss

### 3.1 Current 扩充

在既有西布曲明 current 主链基础上，新增：

- 比沙可啶及其系列衍生物 group；
- 比沙可啶 concrete Substance；
- 酚汀（酚丁）、酚酞及其酯类衍生物或类似物 group；
- 酚酞 concrete Substance。

这些关系来自 2025 市场监管总局针对宣称“减肥”功能食品非法添加案件的 current 官方来源。

没有把当前 Inspection Reference 尚不存在的酚丁衍生物等名称现场补造成 Substance。

### 3.2 Historical 扩充

历史中央专项抽检/风险监测关系新增：

- 1 个减肥类筛查 group；
- 7 个 concrete Substance：西布曲明、N-单去甲基西布曲明、N,N-双去甲基西布曲明、芬氟拉明、麻黄碱、酚酞、呋塞米。

### 3.3 Claim scope

进入 production：

- `减肥` — 保留 legacy/current primary provenance，并选择性加入 historical；
- `有助于控制体内脂肪` — current official function wording，承接同一 current + historical 功能场景。

继续 Claim-only：

- `减脂`
- `瘦身`
- `燃脂`

不因为同属 `weight_management` 就整体放开。

## 4. male_function

既有 current 那非类/拉非类 group + 西地那非/他达拉非 concrete 主链保留。

新增 current group：

- `育亨宾及其系列衍生物`

官方 current 来源的案件场景明确为宣称“壮阳”功能食品。

当前 Inspection Reference 没有已核验育亨宾 Substance 实体，因此：

```text
壮阳
→ male_function
→ 可看到育亨宾系列 group
→ 不生成 concrete “育亨宾” Substance
```

Claim scope 仍保持：

- admitted：`壮阳`、`补肾`
- Claim-only：`阳痿`、`早泄`、`遗精`、`男性功能`

本切片没有因为新增 current group 而扩大男性功能表达词。

## 5. anti_fatigue

### 5.1 Current

保留 2025 那非类/拉非类 current 主链：

- group：那非类、拉非类物质
- concrete：西地那非、他达拉非

官方解读直接出现“抗疲劳”宣传语境。

### 5.2 Historical

历史中央“缓解体力疲劳类/提高免疫力类样品”筛查关系新增：

- 1 group；
- 13 个当前 Inspection Reference 已存在的 concrete Substance，包括西地那非、他达拉非、伐地那非、豪莫西地那非、羟基豪莫西地那非、那红地那非、红地那非、氨基他达拉非、硫代艾地那非、伪伐地那非、那莫西地那非、去甲基他达拉非、硫代西地那非。

来源中无法与当前 Inspection Reference 安全对齐的名称不展开。

### 5.3 Claim scope

进入 production：

- `抗疲劳` — official transition name
- `缓解体力疲劳` — current official function wording

两者均使用 current primary + selective historical。

## 6. c6 inventory

```text
Risk Reference version = 2026.09-c6
total mappings         = 81
current mappings       = 13
historical mappings    = 68
current groups         = 6
historical groups      = 6

Claim Bridge version   = claim-inspection-bridge-v2.5
Bridge mappings        = 25
```

## 7. Knowledge Audit 口径

Current coverage 必须由 V2 `claim_inspection_bridge_v2.json` 计算，而不是旧 `effect_risk_bridge.json`。

旧 Effect Bridge 只保留给既有 deterministic context corpus 兼容回归。

c6 current Risk 与 V2 Claim Bridge 的交集为：

- current Risk rows：13
- current explicit mappings：7
- unique current concrete substances：5
- current runtime categories：`weight_loss / male_function / anti_fatigue`
- 当前 7 条 concrete path 均存在 recommendation-ready Method + applicability path。

historical-only 的 sleep / blood_pressure / blood_lipid / blood_glucose 不进入 current coverage 分母。

## 8. B4 完成边界

B4 只建立：

```text
Claim / regulatory scenario
→ Risk
→ source-backed Substance
```

仍未治理的 Substance 实体、当前新方法、完整 analyte/applicability 深核属于 B5。

因此不得为了 B4“看起来完整”而：

- 猜 CAS；
- 由 Method 反推 Claim→Substance；
- 把 group 自动展开成所有药理学成员；
- 把历史筛查列表包装成当前统一法定项目。

## 9. Gate

先运行 Python syntax gate：

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests scripts
```

再运行 B3/B4 targeted suite、全量后端和前端 workflow/typecheck/build。

完整 backend/frontend Gate 已通过；B4 七方向正式标记 Accepted，进入 B5。
