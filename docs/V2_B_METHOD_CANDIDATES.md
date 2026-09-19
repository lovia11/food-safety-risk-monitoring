# V2-B5 检验方法候选与深核队列

> Status: B5-1 ACCEPTED；B5-2 KJ201901/KJ201902 IMPLEMENTED，等待当前 b9/c7 full backend Gate 最终收口  
> Date: 2026-09-18  
> Runtime boundary: candidate manifest 不被 DataStore / Recommendation 消费；只有进入 `inspection_reference.json` 且达到相应 `knowledge_depth` 的 Method 才能参与运行时。

## 1. 本阶段解决什么

B4 已经完成七个宣传方向的 Claim → Risk → source-backed Substance 治理。B5 不再扩 Claim 或 Risk，而只处理：

```text
已有监管关注方向 / Substance
→ 官方检验方法候选
→ 正式全文深核
→ MethodSubstance
→ MethodApplicability
→ lifecycle / provenance
→ promotion
```

核心原则保持不变：

- Method 能检测某物质，不能反推 Claim → Risk；
- 官方公告出现一个方法，只能先证明“方法身份存在”；
- 未读取正式方法全文之前，不能声称完整 analyte、CAS、适用基质、剂型、定性/定量角色或 Recommendation-ready；
- candidate manifest 始终 non-runtime；
- 当前 runtime 仍是 `inspection-reference@2026.09-b8` 的 7-method index。

## 2. Candidate lifecycle

`config/inspection_method_candidates_v2.json` 当前版本：`2026.09-b6`。

状态含义：

### `candidate`

只完成发现。还没有足够一手来源核验，不得记录 verification/promotion 字段。

### `verification`

已经由一手官方来源核验至少：

- method_no；
- 正式标题；
- 发布机构 / 发布公告；
- 发布身份。

但仍未完成正式全文的 analyte / applicability / lifecycle 深核，因此：

```text
expected_depth = reference_only
promoted_method_id = null
promoted_dataset_version = null
runtime_consumed = false
```

### `promoted`

已经形成正式 Inspection Method 身份并进入 `inspection_reference.json`。manifest 只保留 promotion trace，不重复导入 runtime。

## 3. B5-1 当前 verification queue

当前 manifest 共12条记录：4条 promoted trace，8条仍处于 verification。下表同时列出已在 B5-2 promotion 的 KJ201901/KJ201902，便于保持候选到runtime的完整追溯：

| Method | 当前关联方向 | 身份核验来源 | 当前状态 |
|---|---|---|---|
| BJS 201901 食品中二甲双胍等非食品用化学物质的测定 | blood_glucose | SAMR 2019年第4号公告 | `verification / reference_only` |
| KJ201901 保健食品中西地那非和他达拉非的快速检测 胶体金免疫层析法 | anti_fatigue（正式范围另含调节免疫等，但runtime不扩Risk） | SAMR 2019年第41号公告 + 正式附件1 | `promoted / recommendation_ready @ b9` |
| KJ201902 保健食品中罗格列酮和格列苯脲的快速检测 胶体金免疫层析法 | blood_glucose | SAMR 2019年第41号公告 + 正式附件2 | `promoted / recommendation_ready @ b9` |
| BJS 202409 食品中托拉塞米等19种利尿剂的测定 | blood_pressure / weight_loss 场景候选 | SAMR 2024年第51号公告 | `verification / reference_only` |
| BJS 202501 食品中坎地沙坦酯、拉西地平、阿齐沙坦的测定 | blood_pressure | SAMR 2025年第39号公告 | `verification / reference_only` |
| BJS 202502 食品中普萘洛尔等25种β-受体阻滞剂类化合物的测定 | blood_pressure | SAMR 2025年第39号公告 | `verification / reference_only` |
| BJS 202504 食品中酚丁、双丙酚丁、双酚沙丁、双酚沙丁醋酸酯和酚丁双环丙甲酸酯的测定 | weight_loss | SAMR 2025年第39号公告 | `verification / reference_only` |
| BJS 202601 食品中布噻嗪和美布噻嗪的测定 | blood_pressure / weight_loss 场景候选 | SAMR 2026年第24号公告 | `verification / reference_only` |
| BJS 202602 食品中伐地那非杂质30的测定 | male_function | SAMR 2026年第24号公告 | `verification / reference_only` |
| BJS 201808 食品中5种α-受体阻断类药物的测定 | male_function / yohimbine 方法候选 | SAMR 2018年第28号公告 + 官方方法数据库 | `verification / reference_only` |

这些“方向”只是深核优先级上下文，不是由 Method 自动建立的新 Risk relation。

## 4. 对旧 shortlist 的关键修正

### 4.1 BJS 201805 不再是 current runtime 缺口

旧清单把：

```text
BJS 201805 食品中那非类物质的测定
```

列为 male_function / anti_fatigue P0 候选。

但当前项目已经完成 BJS 202405 正式全文深核；该方法明确代替：

- BJS 201601；
- BJS 201704；
- BJS 201805。

因此 BJS 201805 的正确角色是：

```text
historical / superseded lifecycle reference
≠ current runtime expansion target
```

B5 不再把它作为现行 Recommendation Method promotion。

### 4.2 2022 硝苯地平方法暂不写入 manifest

SAMR 2022年第29号公告和方法数据库已确认正式方法：

```text
食品中硝苯地平及其降解产物的测定
```

但当前可访问的一手页面没有在正文中可靠给出方法编号。candidate schema 要求 `method_no`，因此本阶段不猜编号、不用列表顺序推编号。

保留为“已确认方法标题，待编号/全文核验”的文档候选。

### 4.3 BJS 201808 已从“编号待确认”升级为 verification

后续检索找到 SAMR 官方公告：

```text
市场监管总局关于发布《食品中5种α-受体阻断类药物的测定》
食品补充检验方法的公告（2018年第28号）
```

公告附件标签直接写明：

```text
食品中5种α-受体阻断类药物的测定（BJS 201808）
```

因此编号已经由一手来源确认，现已进入 manifest `verification`。

但当前工具仍未直接解析 SAMR 官方 DOCX 正文，所以还不能把第三方镜像中的5种目标物、CAS和适用基质直接当作 production MethodSubstance / Applicability。Method身份已核验，全文深核仍未完成。

### 4.4 2025 执法检验方法暂不混入 BJS runtime schema

西布曲明、比沙可啶、酚汀/酚酞、4-氯双异丁酚丁等 2025 current 执法检验方法具有很高业务价值，但它们的规范身份与 `supplementary_bjs / rapid_kj / national_standard_gbt` 不完全相同。

在确定是否需要新增 `method_type = enforcement_method` 及其 lifecycle/applicability 规则前，不把它们硬塞进现有 Method schema。

## 5. 首批深核优先级

优先级是知识工程顺序，不是产品风险排序。

### 第一批：小规模、当前、能直接补现有链路

1. **BJS 202504**
   - current；
   - 标题仅 5 个化合物；
   - 与 B4 current weight_loss 酚丁/酚酞监管场景最直接；
   - 适合先验证“候选 → 全文 → analyte/applicability → promotion”的 B5 流程。

2. **BJS 202501**
   - current；
   - 标题明确 3 个降压相关化合物；
   - 规模小，适合与 blood_pressure historical/current knowledge 做独立对照。

3. **BJS 201808 / KJ201901 / KJ201902**
   - BJS 201808 与快速方法都属于小规模 analyte 集；
   - 可补 male_function / yohimbine 与快速筛查角色；
   - BJS 201808 必须先取得/解析官方全文；KJ 方法还必须核清判定规则以及阳性后确证边界。

4. **BJS 202601 / BJS 202602**
   - 2026 current；
   - 标题目标物少；
   - 但必须特别防止用“方法存在”反推新的 Risk→Substance。

### 第二批：较大 analyte 集

- BJS 201901；
- BJS 202409；
- BJS 202502。

它们需要更多 Substance identity / CAS / applicability 解析工作，等第一批 promotion 流程跑通后再处理。

## 5.1 B5-2 已完成的官方全文抓取与 KJ promotion

通过独立 GitHub Actions research workflow 从 SAMR 官方附件获取并留存 SHA-256：

- KJ201901 DOCX：`CA99D709F8B38D6E53AC4DCED58BF99B3D0FF2B99EC8CCC9712B328F1B38D923`
- KJ201902 DOCX：`203DB061A5D171D9AFAC91402B3EAA1B7708C763E37F62DAD1663E231300B69C`
- BJS 201808 DOCX：`45D85B389553925AF01FCB5EEAB6DE7113E898ED998FCDEE44EBD3476DB696B9`
- BJS 201901 DOC：`C4A697A35F4171516C06947C937F0C10D01FDC3AFC671D7780154A5AD9936EE9`（已下载，尚未完成文本解析）

KJ201901 / KJ201902 已按正式全文进入 `inspection-reference@2026.09-b9`：

- `KJ201901`：西地那非、他达拉非；`rapid_screen`；正式范围为声称抗疲劳、调节免疫等功能的保健食品。runtime只保留已有 `anti_fatigue` Risk，不因Method扩出“调节免疫”等新Risk；阳性需确证。
- `KJ201902`：罗格列酮、格列苯脲；`rapid_screen`；精确限定 `blood_glucose`；阳性需确证。
- 两份方法正文列出的交叉反应物均不自动扩写成 MethodSubstance。

KJ201902 promotion 暴露出 B4 时留下的两个身份缺口。随后 `risk-substance-reference@2026.09-c7` 使用原有2018中央辅助降血糖抽检资料补齐：

- 来源“格列本脲” → 当前 `格列苯脲` Substance（CAS 10238-21-8）；
- 来源“马来酸罗格列酮” → 当前 `罗格列酮` 母体 Substance（CAS 122320-73-4）。

这两条 Risk 的监管依据仍是2018中央抽检资料；KJ201902全文只用于名称/盐型身份归一化，不构成 Method→Risk 反推。

BJS 201808 已取得并解析 SAMR 正式全文，但当前5个目标物中仅部分已有 canonical Substance 身份。其 promotion 留到下一子阶段，先完成5个目标物的base/salt identity治理。

## 6. Deep verification Gate

任何 candidate 进入 `inspection_reference.json` 前，至少必须从正式方法全文确认：

- method_no / official title；
- publisher / source URL / source date；
- method lifecycle / 是否被替代；
- analyte 全量或明确受控 subset；
- source label / CAS / normalization；
- determination role；
- product category / form / matrix；
- include / conditional / exclude applicability；
- 前处理或适用性例外中会影响 Product Context 的条件；
- RegulatoryDocument identity；
- 与已有 MethodSubstance 的重叠；
- 是否真的满足 `reference_only → analyte_verified → applicability_verified → recommendation_ready` 的对应 Gate。

标题、新闻稿或公告目录不能替代正式全文。

## 7. 官方入口

### BJS 201901

SAMR 2019年第4号公告：  
`https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/bgt/art/2023/art_a5204e5dff584b91b222bf9b47c2c92b.html`

### KJ201901 / KJ201902

SAMR 2019年第41号公告：  
`https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2023/art_0ac8c49f7b2a4536a2bd1397ed010c2d.html`

### BJS 202409

SAMR 2024年第51号公告：  
`https://www.samr.gov.cn/spcjs/xxfb/art/2024/art_4e2c7543a9d6488fa91081db6f003a36.html`

### BJS 202501 / 202502 / 202504

SAMR 2025年第39号公告：  
`https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/spcjs/art/2025/art_0fa91ac2c946482894bb854d4f506c24.html`

### BJS 202601 / 202602

SAMR 2026年第24号公告：  
`https://www.samr.gov.cn/spcjs/xxfb/art/2026/art_9bd68f8517924598baf560008a034baf.html`

### 方法数据库

`https://www.samr.gov.cn/spcjs/bcjyff/`

## 8. B5-1 Acceptance

B5-1 只要求：

- verification queue 可由 validator 通过；
- 8 个仍处于 verification 的方法不进入 operational method index；
- 2 个历史 promotion trace 仍只计一次；
- Audit 的 Method Reference / Deep Verification denominator 仍为 7；
- candidate 数量变化不得改变 Recommendation；
- syntax / candidate / audit / full regression 通过。

B5-1 已通过 syntax / governance / full backend+frontend acceptance。现进入 B5-2：从 BJS 202504 等第一批方法开始正式全文深核。
