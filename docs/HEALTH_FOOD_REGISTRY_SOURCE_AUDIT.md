# 保健食品官方注册/备案数据源审计

状态：CURRENT SUPPORT
审计日期：2026-09-13
适用阶段：V2-3 — HealthFood Identity & Official Registry Verification

## 1. 审计结论

国家市场监督管理总局（SAMR）“特殊食品信息查询平台”可作为本项目当前保健食品注册/备案核验的官方事实源。平台由市场监管总局页面和政务服务门户直接链接，公开查询页面在本次低频审计中无需登录、Cookie 或验证码，并通过结构化 JSON 接口返回注册/备案查询结果。

该接口属于官方网页的内部数据接口：当前未发现公开的 API 版本承诺、SLA 或调用频率说明。因此本项目只能把在线查询实现为低频、带超时、可缓存、可降级的数据提供器；不得把它当作永远可用的稳定开放 API，也不得绕过未来可能出现的验证码、登录或访问限制。

在线查询失败时，系统必须保留页面侧候选事实并投影为 `registry_lookup_unavailable`，不能阻断 OCR、Phase3、Review 或 Sampling。受治理的官方快照/人工导入记录使用同一标准化契约，作为离线测试和可降级回放来源。

## 2. 官方入口与监管语义

- 市场监管总局“特殊食品安全监督管理”页面将“特殊食品信息查询”直接链接到官方查询平台：<https://www.samr.gov.cn/tssps/index.html>
- 市场监管总局政务服务门户在保健食品注册与备案事项中同样提供该查询入口：<https://zwfw.samr.gov.cn/>
- 官方查询平台：<https://ypzsx.gsxt.gov.cn/specialfood/>
- 《保健食品注册与备案管理办法》规定了注册与备案的定义、注册证书内容、批准文号/备案号格式以及信息公开要求：<https://www.samr.gov.cn/zt/ndzt/2019n/bjspjsqjxcjwljxyjsckpxc/zcfg/art/2023/art_fca01dd2bbed437282f7ffd4d056f481.html>
- 《食品标识监督管理办法》要求特殊食品标签、说明书与注册/备案内容相一致，并规定保健食品标注注册号或备案号及专属标志：<https://www.samr.gov.cn/zw/zfxxgk/fdzdgknr/fgs/art/2025/art_4edcff1e8d894890a012aac1e974c1ff.html>
- 市场监管总局保健食品科普问答亦说明注册证书所载产品名称、保健功能等信息：<https://www.samr.gov.cn/tssps/kpxc/bjsp/art/2023/art_2108095b1cae44f3ab242553f80455ce.html>

据上述官方规则，本项目采用以下事实边界：保健食品依法实行注册与备案管理；注册证书记录产品名称、保健功能等登记信息；标签、说明书应与注册/备案内容一致，且不得涉及疾病预防、治疗功能。这些事实只定义身份字段及未来比较对象，不在 V2-3 自动生成违法或超范围结论。

以上监管材料只用于确定字段语义和官方来源权威性。本阶段不据此自动判断页面宣传是否合法，不执行 Claim 一致性、疾病声称或超范围声称判断。

## 3. 数据源十项审计

| 审计项 | 结论 |
| --- | --- |
| 1. 数据所有者 | 国家市场监督管理总局特殊食品信息查询平台。 |
| 2. 官方入口 | `https://ypzsx.gsxt.gov.cn/specialfood/`，由 SAMR 官网和政务服务门户直接链接。 |
| 3. 覆盖对象 | 保健食品注册、保健食品备案；平台还包含其他特殊食品，但本阶段不接入。 |
| 4. 访问方式 | 公开网页及其结构化 JSON 数据接口；本次审计无需登录、Cookie 或验证码。 |
| 5. 查询键 | 注册批准文号或备案号精确查询；只对格式明确且不含 OCR 歧义的候选发起查询。 |
| 6. 返回字段 | 标识号、产品名称、注册人/备案人、地址、保健功能、主要原料、适宜/不适宜人群、食用方法及食用量、规格、保质期、贮藏方法、注意事项、批准/备案日期等；备案响应字段可能少于注册响应。 |
| 7. 权威边界 | 官方记录是注册/备案事实源；页面证据仍是独立事实源。两者匹配只产生保守身份结论，不产生合法性结论。 |
| 8. 可用性约束 | 未发现公开 API 版本、SLA 或限流契约。只能低频调用、设置超时并缓存；遇到限制必须停止在线尝试并降级。 |
| 9. 可审计性 | 保存查询标识、查询时间、来源名称、来源 URL、原始响应 artifact、SHA-256，以及标准化记录。不得保存 Cookie、令牌或会话头。 |
| 10. 降级/替代 | `OfficialOnlineProvider` 为在线 best-effort；`ImportedOfficialRecordProvider` 读取受治理的官方响应快照。两者产出同一 provider contract。第三方数据库不得作为权威替代。 |

## 4. 当前在线接口事实

基础地址：

```text
https://ypzsx.gsxt.gov.cn/specialfood_server/
```

前端部署配置公开声明该基础地址。当前页面使用以下调用：

| 对象 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| 注册查询 | POST | `healthFood/queryHealthFood` | `pzwh` 为批准文号；支持产品名称、申请人、保健功能等页面筛选字段。 |
| 注册详情 | GET | `healthFood/detailsHealthFood?id={infosharId}` | 境内注册详情。 |
| 进口注册详情 | GET | `healthFood/detailsJinHealthFood?id={infosharId}` | 页面按进口标志选择的详情分支。 |
| 备案查询 | POST | `foodRecord/queryHealthFood` | `bah` 为备案号；支持产品名称、备案人等页面筛选字段。 |
| 备案详情 | GET | `foodRecord/detailsHealthFood?id={infosharId}` | 备案详情。 |

注册精确查询使用页面当前请求结构，除 `pzwh` 外的筛选值保持空字符串：

```json
{
  "currentPage": 1,
  "pageSize": 10,
  "cpmc": "",
  "sqrmcZw": "",
  "pzwh": "国食健注G20190188",
  "bjgn": "",
  "zyyl": "",
  "scqymcZw": "",
  "scqymcYw": "",
  "scg": "",
  "cpmcYw": "",
  "iofg": ""
}
```

备案精确查询使用同一页面公开请求结构，以 `bah` 传入备案号；其他筛选值为空：

```json
{
  "currentPage": 1,
  "pageSize": 10,
  "cpnameZw": "",
  "barZw": "",
  "bah": "食健备G201934001524",
  "shxydm": "",
  "iofg": ""
}
```

响应外层当前包含 `state`、`message` 和 `data`。查询结果的 `data.list` 提供 `infosharId`，随后以该 ID 获取详情。适配器必须验证响应类型和必要字段；页面接口结构变化、非 JSON、缺字段或多条不可消歧结果均不得静默构造官方记录。

## 5. 标识格式边界

本阶段识别并标准化：

- 当前境内/进口注册号：`国食健注G` / `国食健注J` + 4 位年份 + 4 位顺序号。
- 当前境内备案号：`食健备G` + 4 位年份 + 2 位省级行政区代码 + 6 位顺序号。
- 当前进口备案号：`食健备J` + 4 位年份 + `00` + 6 位顺序号。
- 历史批准文号：`国食健字G` / `国食健字J` + 8 位数字，只作为 `legacy_identifier_candidate`，不因格式本身成为已核验身份。

标准化仅允许 Unicode NFKC、去除空白/包围性标点和拉丁字母大写。OCR 中 `O/0`、`I/1` 等可疑替换不自动纠正，标记为 `ambiguous_ocr`，不得发起官方查询。`卫食健字` 等未纳入本阶段明确契约的历史格式不自动查询。

## 6. 已验证正例

本次以官方注册号 `国食健注G20190188` 进行一次低频精确查询，官方查询返回唯一结果：

- 产品名称：`谷宜甘牌谷胱甘肽茶多酚片`
- 注册人：`山东金城生物药业有限公司`
- 有效期至：`2030-01-19`
- 批准日期：`2025-01-20`
- 官方保健功能原文：`本品经动物实验评价，具有对化学性肝损伤有辅助保护作用的保健功能`

官方平台亦公开了该产品相关技术要求文件：<https://ypzsx.gsxt.gov.cn/specialfood_server//fileService/readFtp?code=BA99C4F878D9493588FD89F6210C5572&type=bjspzcGuoJsyq>

该正例用于建立脱敏后的受治理离线 fixture。fixture 必须保留来源 URL、检索日期、查询标识和原始响应 SHA-256；不得包含 Cookie、令牌或会话信息。官方保健功能按原文数组保存，不映射到 24 项功能或其他分类。

## 7. Provider 与缓存约束

统一 provider 结果至少包含：

```text
status: found | not_found | unavailable | malformed
queriedIdentifier
sourceName
sourceReference
queriedAt
record
rawArtifactPath
rawArtifactSha256
error
```

约束：

1. 查询只接受通过格式校验且无 OCR 歧义的单一标识。
2. 在线 provider 使用短超时、低频请求，不重试验证码或访问限制。
3. 缓存以标准化标识为键；新鲜缓存优先，避免同一商品或不同 run 重复查询。
4. 原始查询/详情响应写入可审计 artifact，SQLite 只保存标准化投影和 artifact 引用。
5. `not_found`、`unavailable`、`malformed` 均保留页面候选和诊断，不生成虚假官方记录。
6. 受治理导入 provider 只接受带来源、检索时间、标识和可校验 SHA-256 的官方快照。

## 8. 当前支持级别与重新审计触发条件

当前支持级别：**在线 best-effort + 受治理离线回放**。

以下任一情况必须重新审计并在适配器层降级，而不是绕过：

- 官方入口、基础地址或接口结构改变；
- 出现登录、验证码、访问频率限制或明确禁止自动访问的提示；
- 响应不再能唯一对应查询标识；
- 字段语义或标识格式发生监管变更；
- 需要引入新的官方来源、第三方来源或新的身份/Claim 结论。
