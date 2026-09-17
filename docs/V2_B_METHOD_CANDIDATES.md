# V2-B 检验方法候选清单

> Status: CANDIDATE AUDIT — 未进入 runtime  
> Date: 2026-09-18  
> Rule: 方法存在 ≠ 可自动推荐；必须完成目标物、适用范围、生命周期和上游 Risk 关系核验。

## 1. 为什么需要这份清单

当前项目 `inspection_reference.json` 只有一个深度整理的 7-method 子集，而市场监管总局截至 2026 年公开说明已累计发布 112 项食品补充检验方法。

V2-B 重新从“宣传方向”出发检索后发现，项目现有方法集既有“上游暂时触达不到”的方法，也漏了多项与减肥、降压、降糖、男性功能/抗疲劳高度相关的方法。

因此不再继续无方向扩充 Method，而建立与 7 个监管关注方向绑定的候选池。

## 2. P0 候选：优先深核

| Method | 方向 | 官方来源 | 当前状态 |
|---|---|---|---|
| BJS 201901 食品中二甲双胍等非食品用化学物质的测定 | blood_glucose | SAMR 2019年第4号公告 | candidate_pending_deep_verification |
| KJ201901 保健食品中西地那非和他达拉非的快速检测 胶体金免疫层析法 | male_function / anti_fatigue | SAMR 2019年第41号公告 | candidate_pending_deep_verification |
| KJ201902 保健食品中罗格列酮和格列苯脲的快速检测 胶体金免疫层析法 | blood_glucose | SAMR 2019年第41号公告 | candidate_pending_deep_verification |
| BJS 201805 食品中那非类物质的测定 | male_function / anti_fatigue | SAMR 2018年第14号公告 | candidate_pending_deep_verification |
| 食品中硝苯地平及其降解产物的测定（2022年第29号公告） | blood_pressure | SAMR 2022 | candidate_pending_deep_verification |
| BJS 202501 食品中坎地沙坦酯、拉西地平、阿齐沙坦的测定 | blood_pressure | SAMR 2025年第39号公告 | candidate_pending_deep_verification |
| BJS 202502 食品中普萘洛尔等25种β-受体阻滞剂类化合物的测定 | blood_pressure | SAMR 2025年第39号公告 | candidate_pending_deep_verification |
| BJS 202504 食品中酚丁、双丙酚丁、双酚沙丁、双酚沙丁醋酸酯和酚丁双环丙甲酸酯的测定 | weight_loss | SAMR 2025年第39号公告 | candidate_pending_deep_verification |
| BJS 202601 食品中布噻嗪和美布噻嗪的测定 | blood_pressure / weight_loss 场景候选 | SAMR 2026年第24号公告 | candidate_pending_deep_verification |
| BJS 202602 食品中伐地那非杂质30的测定 | male_function | SAMR 2026年第24号公告 | candidate_pending_deep_verification |

## 3. P1 候选：相关但需先核适用范围

| Method | 方向 | 原因 |
|---|---|---|
| 食品中5种α-受体阻断类药物的测定（2018） | blood_pressure | 历史降压抽检项目含哌唑嗪等，需核正文目标物和适用基质 |
| BJS 202409 食品中托拉塞米等19种利尿剂的测定 | blood_pressure / weight_loss | 利尿剂同时出现在部分历史减肥/降压筛查项目中，必须避免按药理反推 |
| 2025 西布曲明系列衍生物执法检验方法 | weight_loss | current 强场景证据，但属于执法检验方法，不应和 BJS 生命周期字段混淆 |
| 2025 比沙可啶系列衍生物执法检验方法 | weight_loss | current 强场景证据；需要独立 method_type/适用性治理 |
| 2025 酚汀（酚丁）/酚酞系列执法检验方法 | weight_loss | current 强场景证据；需和 BJS 202504 的关系去重 |
| 2025 4-氯双异丁酚丁执法检验方法 | weight_loss | current 强场景证据；需决定是否纳入 Deep Verified Subset |

## 4. 已有方法的角色重新定位

### BJS 201701

继续作为 weight_loss 当前核心方法之一，但不能再被理解成“整个减肥方向只有西布曲明”。

### BJS 202405

继续作为 male_function/anti_fatigue 重要方法；现有 95 analyte 深度知识具有价值。随着 2025 那非/拉非 current Risk 和 2026 BJS202602 出现，这部分可达性应增强。

### BJS 201710

不是摆设。它覆盖大量睡眠、降压、调脂、降糖、男性功能相关化合物，并具有保健食品/声称具有保健功效食品的剂型范围。但它只是 Method→Substance Authority，不能单独制造 Claim→Substance。

### KJ201903

保留为巴比妥类快速筛查，适用于其正式范围；阳性结果仍需进一步确证。V2-B sleep_aid 可能让它获得真实上游触达路径。

### GB/T 45443-2025

保留为保健食品褪黑素测定方法，不纳入一般“睡眠宣传→非法添加物”推荐。它更适合已核验褪黑素保健食品的产品身份/配方/含量语境。

## 5. 深核 Gate

每个 candidate 升级到 `recommendation_ready` 前必须获取正式方法正文并记录：

- method_no / title / publisher / source URL
- lifecycle/current status
- analyte 全量或明确受控 subset
- CAS/别名规范化
- determination role（定性/定量/快速筛查）
- product category
- product form
- matrix / ingredient exceptions
- 替代/废止关系
- 与已有 MethodSubstance 是否重复
- 是否需要独立 `method_type = enforcement_method` 或 `rapid_kj`

未完成以上字段的，只能留在 candidate 文档，不能写进 `inspection_reference.json` 的 recommendation-ready runtime。

## 6. 官方入口

- 食品补充检验方法数据库：`https://www.samr.gov.cn/spcjs/bcjyff/`
- BJS 201901：`https://www.samr.gov.cn/spcjs/bz/cs/art/2019/art_32afdd76c9f542f2bdd734801920ad0b.html`
- KJ 2019年第41号公告：`https://www.samr.gov.cn/spcjs/xxfb/art/2019/art_2a1de171556f40f2b8f5829fe9810086.html`
- BJS 201805公告：`https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2023/art_17e84b8961684057bbf27d6b7edd4813.html`
- 2022年第29号公告：`https://www.samr.gov.cn/spcjs/xxfb/art/2022/art_547b6bf10c8e4fa7ab052e250a1aa4b4.html`
- 2024年第51号公告：`https://www.samr.gov.cn/spcjs/xxfb/art/2024/art_4e2c7543a9d6488fa91081db6f003a36.html`
- 2025年第39号公告：`https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2025/art_0fa91ac2c946482894bb854d4f506c24.html`
- 2026年第24号公告：`https://www.samr.gov.cn/spcjs/xxfb/art/2026/art_9bd68f8517924598baf560008a034baf.html`
