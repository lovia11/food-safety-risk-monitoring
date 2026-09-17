# V2-B2 Claim Taxonomy 补洞实施记录

> Status: IMPLEMENTED — Claim observation only  
> Date: 2026-09-18  
> Branch: `ux-redesign-v1`  
> Boundary: 本阶段只扩展页面宣传 Claim 观察能力，不新增 Claim→Risk、Risk→Substance、Method Recommendation 或法律判断。

## 1. 本阶段为什么现在做

V2-B1 七方向监管审计已经确认：当前生产 Claim taxonomy 缺少 `blood_glucose` 与 `anti_fatigue` 两个监管方向入口，同时既有 sleep / blood pressure / blood lipid / weight management 词表没有覆盖多项已经治理过的当前或历史官方功能表述。

按照 V2-B 的既定顺序，本阶段先补 Claim observation，再进入 historical/current Risk governance。这样能够保持：

```text
页面观察 Claim
≠ 官方 HealthFunction
≠ Risk
≠ Substance
≠ Method
≠ Recommendation
```

## 2. 新增 Claim 类型

新增两个 active Claim type：

- `blood_glucose_related` — 血糖相关宣传
- `anti_fatigue_related` — 体力疲劳相关宣传

原有五类保持不变：

- `sleep_related`
- `blood_pressure_related`
- `blood_lipid_related`
- `weight_management`
- `male_function_related`

因此当前生产 Claim taxonomy 共 7 类。

## 3. 新增表达

在原 26 个 legacy exact expression 完整保留的前提下，新增 16 个 V2-B2 expression：

### Sleep

- `改善睡眠`
- `有助于改善睡眠`

### Blood pressure

- `辅助降血压`
- `调节血压`
- `有助于维持血压健康水平`

### Blood lipid

- `辅助降血脂`
- `调节血脂`
- `有助于维持血脂健康水平`
- `有助于维持血脂（胆固醇/甘油三酯）健康水平`

其中不带括号的 `有助于维持血脂健康水平` 明确标为 `manual_curated`，因为 2023 当前官方完整功能名称含“（胆固醇/甘油三酯）”；它不得伪装成官方名称原文。

### Weight management

- `有助于控制体内脂肪`

### Blood glucose

- `降糖`
- `辅助降血糖`
- `调节血糖`
- `有助于维持血糖健康水平`

宽泛词 `血糖` 与疾病词 `糖尿病` 本阶段不新增为自动 Claim expression。

### Anti-fatigue

- `抗疲劳`
- `缓解体力疲劳`

## 4. Provenance 处理

新增 expression 不伪装成 legacy migration：

- 原 26 项继续使用 `source=legacy_system`，并保留 `legacy_reference`；
- 当前/历史官方功能原生表述使用 `source=official_source`；
- 由 V2-B 监管审计明确选择、但不是当前官方名称原文的表达使用 `source=manual_curated`；
- 所有非 legacy expression 的 `legacy_reference=null`。

运行时仍保持 deterministic literal exact matching，没有加入 fuzzy、embedding、LLM 或同义词自动扩展。

## 5. 明确没有修改的生产语义

本阶段没有修改：

- `config/claim_inspection_bridge_v2.json`
- `config/risk_substance_reference.json`
- `config/inspection_reference.json`
- legacy `config/effect_risk_bridge.json`
- Recommendation resolver
- Product Context / Applicability

因此：

- 新识别到 `blood_glucose_related` 不会自动生成降糖药物 Recommendation；
- 新识别到 `anti_fatigue_related` 不会因为当前 Risk Reference 已存在 anti-fatigue 关系就自动接通；
- 新增官方功能名称作为页面 Claim expression，不表示该商品已获该保健功能批准；
- Claim 命中不表示实际含有任何物质，也不表示违法。

`claim_health_function_mapping_v2.json` 本阶段保持 V2-6A 已冻结的 4 条 topic mapping 不变。血糖与体力疲劳是否进入 ClaimConsistency 正式 topic mapping，应作为独立 V2-6/B2 follow-up gate 处理，而不是由 Claim taxonomy 扩展隐式产生。

## 6. 测试契约调整

`tests/test_claim_taxonomy_v2.py` 已调整为同时验证：

- 7 个 Claim type 唯一且 active；
- 原 5 Effect / 26 legacy keyword 仍 100% 一对一保留；
- 16 个 V2-B2 expression 精确存在；
- legacy 与新表达 provenance 分开；
- taxonomy 内仍禁止 Risk / HealthFunction / Inspection mapping 字段；
- seller-managed 仍是唯一 formal Claim source；UGC 仍只作辅助。

## 7. 下一步

下一阶段按既定 V2-B 顺序进入 **B3 — historical/current Risk governance**。

B3 先设计生产边界，不直接批量写 Risk Reference。至少要冻结：

1. historical 官方抽检关系是否允许被单条 ClaimInspectionBridge 显式引用；
2. 是否需要 mapping-level `temporal_policy`，而不是全局开启 `include_historical`；
3. current + historical 同时存在时的 provenance 与 UI 呈现；
4. 褪黑素、烟酸等合法语境复杂物质的 context guard；
5. historical 关系进入 Recommendation 时必须显示的非当前强制项目 disclaimer。

B3 冻结后，才进入 B4 Risk→Substance 扩充与 B5 Method shortlist 深核。
