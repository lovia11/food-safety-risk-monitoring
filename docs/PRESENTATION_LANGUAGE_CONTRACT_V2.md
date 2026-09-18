# Presentation Language Contract V2

> 状态：active
> 日期：2026-09-18

## 1. 目标

前端向监管用户解释业务状态，不直接暴露内部数据结构、阶段名或治理实现。

用户首先需要知道：

1. 发现了什么；
2. 当前能给出什么建议；
3. 如果不能给出，缺什么信息。

## 2. 禁止作为主流程用户文案的内部词

- `Evidence`
- `Phase3`
- `V2`
- `KnowledgeTrace`
- “映射”作为内部关系名
- “治理”作为内部数据流程名

这些术语可以保留在代码、配置、审计文档和知识库详情中，但不应成为商品详情页的主要状态解释。

## 3. 状态与用户语言

| 内部状态 | 用户主文案 |
|---|---|
| analysis not ready | 尚未完成分析 |
| Claim complete + zero signals | 未发现重点宣传线索 |
| Claim exists + no Risk finding | 已发现宣传线索，暂无对应抽检建议 |
| Risk exists + no usable Method | 已识别抽检关注方向，暂无适用检测方法 |
| Recommendation available | 已形成抽检辅助建议 |
| Recommendation error | 抽检建议生成失败 |
| needs context | 需补商品信息 |
| regulatory context review | 需核对商品信息 |

## 4. 边界说明原则

- 不在每个状态卡片重复“不是违法认定/不是检出结论”等说明。
- 页面级抽检建议保留一处统一免责声明。
- historical reference 仅额外说明：历史专项资料不代表当前统一抽检要求。
- 完整 provenance、后端 reason、mapping ID 等继续保留在结构化结果中，供审计和知识库查看。

## 5. 状态模型原则

V2 页面主流程以 Claim 状态判断是否发现宣传线索：

```text
claimAnalysisStatus + claimSignals
        ↓
页面宣传线索状态
```

`Evidence[]` 仍用于原文溯源和历史 Snapshot 兼容，不再作为 V2 Claim 是否存在的唯一判断条件。

## 6. 修改边界

本 Contract 只规范 Presentation 和交互入口，不改变：

- Evidence 数据模型
- Claim taxonomy
- Claim→Risk 关系
- Risk→Substance 关系
- Method applicability
- Review / Sampling 决策

业务规则变化必须在对应治理阶段单独评估，不得通过文案暗示或替代。
