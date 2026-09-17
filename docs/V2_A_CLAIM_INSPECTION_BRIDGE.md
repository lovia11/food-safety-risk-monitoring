# V2-A — Claim → 抽检知识链统一

> Status: IMPLEMENTED / PENDING REGRESSION VALIDATION  
> Applies to: V2  
> Date: 2026-09-18

## 1. 目标

V2 当前商品的抽检辅助建议以 `ClaimMention / ClaimSignal` 页面宣传线索作为正式入口，不再以 legacy Phase 3 Effect 作为当前商品的正式推荐入口。

目标链路：

```text
页面 Evidence
→ V2 ClaimMention
→ 受治理 Claim Inspection Bridge
→ Risk / 监管关注方向
→ Substance
→ Inspection Method
→ Product Context 适用性
→ 人工复核
→ 抽检清单
```

本阶段不新增任何监管知识关系，不扩展 Risk→Substance，不新增检验方法，不引入大模型、RAG 或模糊语义推断。

## 2. 当前正式桥接

机器可读权威：`config/claim_inspection_bridge_v2.json`。

V2-A 只迁移此前已经存在并经过治理的 3 条精确关系：

| Claim 类型 | 精确表达 | 监管关注方向 | Risk Reference |
|---|---|---|---|
| `weight_management` | `减肥` | `weight_loss` | `weight-loss-sibutramine-group-cn-2025` |
| `male_function_related` | `壮阳` | `male_function` | `male-function-nafei-lafei-group-cn-2025` |
| `male_function_related` | `补肾` | `male_function` | `male-function-nafei-lafei-group-cn-2025` |

不得按 Claim 类型整体扩展。因此：

- `减脂`、`瘦身`、`燃脂` 当前不会因为同属 `weight_management` 而自动进入 `weight_loss`；
- `阳痿`、`早泄`、`遗精`、`男性功能` 当前不会因为同属 `male_function_related` 而自动进入 `male_function`；
- `sleep_related`、`blood_pressure_related`、`blood_lipid_related` 当前仍是明确知识缺口，不自动推荐物质或检验方法。

## 3. 当前与历史数据的处理

### 当前 V2 商品

若存在 `claim_analysis.json`，抽检辅助建议必须使用该 Claim artifact。

若存在 `claim_analysis_error.json` 而没有有效 Claim artifact，建议生成应明确失败并保持可人工复核，不得静默回退到 legacy Effect。

### 历史兼容

仅当历史商品既没有 `claim_analysis.json`，也没有 `claim_analysis_error.json` 时，允许使用既有 `analysis.json → Effect-Risk Bridge` 兼容链，以保持旧快照可读。

## 4. 知识治理边界

`claim_inspection_bridge_v2.json` 支持两种治理来源：

- `legacy_verified_migration`：从已经治理的旧桥接精确迁移；
- `direct_verified_reference`：未来可以直接引用经过核验的 Risk Reference。

未来新增睡眠、血压、血脂等关系时，必须先在 `risk_substance_reference.json` 中建立有来源、可核验的监管关系，再新增 Claim expression → Risk Reference 关系。

禁止：

```text
检验方法能检测某物质
→ 反推出某种页面宣传应该关注该物质
```

也禁止：

```text
一个 Claim 类型下某个表达有依据
→ 自动把该类型所有表达都接到同一监管关注方向
```

## 5. UI 语义

面向用户不再只显示“无映射”。

无后续监管知识时应表达为：

> 已发现页面宣传线索，但当前知识库尚未建立该宣传与检测关注方向之间的可靠关系，建议结合原始页面证据人工复核。

当 `unmappedEvidence` 来自 V2 Claim 时保留：

- `claimMentionId`
- `claimType`
- `claimDisplayLabel`
- `expressionId`
- `matchedExpression`
- `evidenceId`
- 原始来源路径和行号

用于解释知识链断在何处。

## 6. 本阶段仍保留的技术债

V2-A 已把**推荐入口**切换到 Claim，但 Claim artifact 当前仍由 `analysis.json.evidence_details` 构建，而这批 Evidence 来自既有 Phase 3 精确词识别。

由于当前 Claim taxonomy 的 26 个表达全部来自同一套 legacy 词表，现阶段不会造成已治理表达的行为差异；但未来如果扩充全新的 Claim 表达，必须先完成 Claim 对页面 DOM/OCR Evidence 的独立读取或同步扩充底层 Evidence 生成机制，不能重新形成“新 Claim 依赖旧 Effect 词表”的隐性耦合。

该问题不授权在 V2-A 中自行扩词或改 Schema，应在后续真实样本/知识扩充前单独处理。

## 7. 验收

新增定向测试应至少证明：

- `减肥` 通过 V2 Claim 到达 `weight_loss`；
- `减脂` 不会被类型级外推；
- `壮阳`、`补肾` 到达 `male_function`；
- `难入睡` 产生 `sleep_related` Claim，但保持明确知识缺口；
- 当前商品存在 Claim artifact 时不再使用 legacy Effect 结果；
- Claim 分析失败时不静默回退；
- 没有 Claim artifact/error 的历史商品仍可走 legacy 兼容链。
