# V2-B3 Historical / Current Risk Governance

> 状态：implementation gate pending local test acceptance
>
> 日期：2026-09-18

## 1. 目标

V2-B3 只解决历史监管资料如何进入 V2 Claim-first 抽检辅助链路的治理问题，不在本阶段批量扩充 Risk→Substance 或 Method 数据。

核心原则：

- current 受治理关系仍是默认生产知识；
- historical 官方专项抽检/风险监测资料可以作为抽检筛查参考，但不得被展示为当前统一法定抽检项目；
- historical 关系不得通过全局 `include_historical=True` 进入 V2 Claim production；
- historical 关系必须由某一条具体 ClaimInspectionBridge 显式授权；
- Method 只能回答“如何检测”，不能反向证明 Claim→Risk→Substance；
- 页面宣传线索不表示商品实际含有某物质，也不构成违法认定或实验室检出结论。

## 2. ClaimInspectionBridge temporal policy

`config/claim_inspection_bridge_v2.json` 的每条 mapping 现在必须声明：

- `current_only`
- `historical_reference_allowed`

规则：

### `current_only`

只能引用 `temporal_status=current` 的 Risk Reference。

现有生产桥：

- `减肥` → `weight_loss`
- `壮阳` → `male_function`
- `补肾` → `male_function`

均保持 `current_only`，本阶段没有扩大现有生产 coverage。

### `historical_reference_allowed`

只允许：

1. exact Claim expression 的单条 Bridge；
2. Risk Reference 的 `temporal_status=historical`；
3. `basis_type=historical_sampling_plan`；
4. `governance_basis=direct_verified_reference`；
5. 保留完整 source/date/product_scope/source_basis_text；
6. UI 输出历史资料边界说明。

legacy migration 不允许使用该 policy。

## 3. 禁止全局打开 historical

V2 Claim production 的 `resolve_claim_analysis()` 明确拒绝：

```python
include_historical=True
```

V2 的正确路径是：

```text
ClaimMention
  → exact ClaimInspectionBridge
  → Bridge temporal_policy
  → current mappings + Bridge-authorized historical mapping IDs only
```

`include_historical=True` 仅保留在 legacy Effect compatibility / debug 路径，不能成为新 V2 任务的生产开关。

## 4. KnowledgeTrace 选择规则

`InspectionKnowledgeResolver.resolve()` 支持：

```python
allowed_historical_mapping_ids={...}
```

选择结果为：

- 所有 current mapping；
- 加上 allowlist 中明确列出的 historical mapping；
- 同一 RiskCategory 下其他 historical mapping 不进入结果。

展示顺序固定 current 在前、historical 在后。

这避免了“为了启用一条历史关系而把整个 RiskCategory 的历史知识全部打开”。

## 5. Recommendation temporal disclosure

RiskFinding 新增：

- `temporal_basis`
  - `current_only`
  - `current_and_historical`
  - `historical_reference_only`
- `historical_reference_mapping_ids`
- `historical_reference_note`

历史资料统一展示边界：

> 该关注方向依据历史中央专项抽检/风险监测资料，用于抽检筛查参考；不表示当前统一法定抽检项目，也不表示该商品实际含有相关物质。

该文本描述知识来源边界，不是风险等级、概率或违法判断。

## 6. 特殊监管语境阻断

对存在受治理合法/条件性监管语境的 Substance，例如后续睡眠方向可能涉及的褪黑素，系统不得因为页面 Claim + 检验方法存在就直接输出普通 `suggest_testing`。

新增状态：

```text
regulatory_context_review
```

触发后：

- `suggested_methods=[]`；
- 已知方法仍保留在 `other_known_methods` 供人工研判；
- 要求先核对商品身份、食品类别、注册/备案、配料/原料等上下文；
- UI 显示“需核对监管语境”。

这条规则是为了防止把“可以在某类合法产品中出现的物质”粗暴显示为“疑似非法添加物”。

## 7. 前端边界

RecommendationPanel 只做最小展示增量，不改变既有交互结构：

- historical RiskFinding 增加“含历史筛查参考”标签；
- 显示 historical reference disclosure；
- `regulatory_context_review` 显示“需核对监管语境”。

不增加风险评分、红黄绿等级或自动裁决标签。

## 8. 本阶段明确没有做的事

V2-B3 **没有**：

- 向 production `risk_substance_reference.json` 批量加入历史关系；
- 因 Method 可检测某物质而新增 Claim→Risk/风险关系；
- 按 Claim type 整体扩展 Bridge；
- 把历史抽检表称为当前统一法定抽检要求；
- 针对褪黑素、烟酸等特殊物质直接输出非法添加结论。

这些知识扩充属于后续 V2-B4，并必须逐条通过 source-level audit。

## 9. Acceptance Gate

定向后端：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_claim_inspection_bridge tests.test_v2b3_temporal_governance tests.test_inspection_knowledge tests.test_inspection_signal_trace tests.test_inspection_recommendation tests.test_inspection_runtime_claim_v2
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

只有上述 Gate 通过后，V2-B3 才标记为 closed，然后进入 V2-B4 Risk→Substance source-backed expansion。
