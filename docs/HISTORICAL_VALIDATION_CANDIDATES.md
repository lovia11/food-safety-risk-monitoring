# Historical Validation Candidate Audit

审计日期：2026-09-11  
当前代码基线：`38904fb5c648ea4a6f66b86d6107f387041cbda4`  
只读数据源：`D:\毕业设计\output`  

本报告只读取历史 JSON、TXT、Markdown、日志和目录结构。审计期间未复制或改写旧 Run，未修改当前 `output` 或 SQLite，未运行 OCR、Phase3、Recommendation，未访问淘宝。

## 1. 扫描范围

- 扫描了旧 `output` 下全部 **28 个一级目录**。
- 逐 Run 检查 Search、`batch_state.json`、`products.json`、`web_snapshot.json`、商品目录、`meta.json`、OCR manifest 和 `analysis.json`。
- Candidate 数量是从可用的 `search_candidates.json`、`products.json` 或 `web_snapshot.json` 中按 Product ID 合并得到；query-validation Run 会合并其子查询候选。旧 Batch 即使没有当前目录布局，也保留其嵌入式候选计数。
- 以“`products/<product_id>/analysis.json` 存在且可解析”为 Phase3 候选入口，再逐一核验真实 Detail/OCR artifact；不以是否具有当前版 `task_request.json` 或 Recommendation 作为 Phase3 成功判断。

## 2. 历史 Run 总览

表中 `商品/Meta/OCR/P3` 分别表示商品目录、`meta.json`、OCR manifest、可解析 `analysis.json` 数量。

| Run ID | 类型 | 阶段/结局 | Search | Candidates | Batch / Products / Web | 商品/Meta/OCR/P3 | 审计判断 |
| --- | --- | --- | ---: | ---: | --- | ---: | --- |
| `20260817T171318` | Standalone experiment | 单商品实验 | 否 | 1 | — / ✓ / — | 1/1/1/1 | 有效 Phase3 商品 |
| `20260817T180025_search` | Search-only | 仅搜索 | 是 | 20 | — / — / — | 0/0/0/0 | 只有 Search，不进入候选集 |
| `20260817T181659_batch` | Batch | completed；2 success、18待详情 | 无独立 Search 目录 | 20 | ✓ / ✓ / ✓ | 2/2/2/2 | 2 个有效 Phase3 商品 |
| `20260828_cdp_smoke1` | Smoke | 搜索诊断 | 是 | 0 | — / — / — | 0/0/0/0 | Smoke，无商品产物 |
| `20260828_cdp_smoke2` | Smoke | interrupted；状态文件含4详情、6待详情 | 是 | 17 | ✓ / ✓ / ✓ | 12/11/2/1 | Run 中断，但1个 Phase3 artifact 有效 |
| `20260828_live_direct1` | Standalone smoke | 搜索诊断 | 是 | 0 | — / — / — | 0/0/0/0 | 无商品产物 |
| `20260828_live_direct2` | Standalone smoke | 搜索诊断 | 是 | 0 | — / — / — | 0/0/0/0 | 无商品产物 |
| `20260828_live_smoke` | Smoke | 搜索诊断 | 是 | 0 | — / — / — | 0/0/0/0 | 无商品产物 |
| `20260828_live_smoke2` | Smoke | 搜索诊断 | 是 | 0 | — / — / — | 0/0/0/0 | 无商品产物 |
| `20260828_live_smoke3` | Smoke | 搜索诊断 | 是 | 0 | — / — / — | 0/0/0/0 | 无商品产物 |
| `20260828_live_smoke4` | Smoke | 搜索诊断 | 是 | 0 | — / — / — | 0/0/0/0 | 无商品产物 |
| `20260828_user_smoke1` | Smoke | 搜索诊断 | 是 | 0 | — / — / — | 0/0/0/0 | 无商品产物 |
| `20260901_collector_v02_e2e` | E2E | completed；2 success、8待详情 | 是 | 10 | ✓ / ✓ / ✓ | 2/2/2/2 | 2 个有效 Phase3 商品 |
| `20260901_collector_v02_test_a` | Collector test | failed | 否 | 0 | — / — / ✓ | 0/0/0/0 | 明确失败 |
| `20260901_collector_v02_test_a_retry1` | Collector test | collection_completed；3详情、17待详情 | 是 | 20 | ✓ / ✓ / ✓ | 3/3/0/0 | 仅完成详情，未执行 OCR/P3 |
| `20260901_collector_v02_test_b` | Collector test | collection_completed；5详情、41待详情 | 是 | 46 | ✓ / ✓ / ✓ | 5/5/0/0 | 仅完成详情，未执行 OCR/P3 |
| `20260902T005526_task` | Web Task | completed；2 success、8待详情 | 是 | 10 | ✓ / ✓ / ✓ | 2/2/2/2 | 2 个有效 Phase3 商品 |
| `20260902T192644_task` | Monitor Task | failed | 否 | 0 | — / — / ✓ | 0/0/0/0 | 明确失败 |
| `20260902T192913_task` | Monitor Task | completed；2 success、17待详情 | 是 | 19 | ✓ / ✓ / ✓ | 2/2/2/2 | 2 个有效 Phase3 商品 |
| `20260903_query_validation_c1_base` | Query reconnaissance | 查询验证 | 是 | 67 | — / — / — | 0/0/0/0 | 多 Query 搜索样本，无详情/P3 |
| `20260903_query_validation_c1_forms` | Query reconnaissance | 查询验证 | 是 | 20 | — / — / — | 0/0/0/0 | 多 Query 搜索样本，无详情/P3 |
| `20260903T014401_task` | Monitor Task | completed；1 success、4待详情 | 是 | 5 | ✓ / ✓ / ✓ | 1/1/1/1 | 1 个有效 Phase3 商品 |
| `20260905T160452_task` | Monitor Task | completed；1 success、4待详情 | 是 | 5 | ✓ / ✓ / ✓ | 1/1/1/1 | 1 个有效 Phase3 商品 |
| `20260905T161011_task` | Web Task | completed；3 success、2待详情 | 是 | 5 | ✓ / ✓ / ✓ | 3/3/3/3 | 3 个有效 Phase3 商品 |
| `20260905T162836_task` | Web Task | failed | 是 | 0 | — / — / ✓ | 0/0/0/0 | 明确失败 |
| `20260905T164200_task` | Web Task | failed | 是 | 0 | — / — / ✓ | 0/0/0/0 | 明确失败 |
| `20260905T164428_task` | Web Task | completed；2 success | 是 | 2 | ✓ / ✓ / ✓ | 2/2/2/2 | 2 个有效 Phase3 商品 |
| `20260907T165329_task` | Monitor Task | completed_with_errors；2 failed_collection | 是 | 2 | ✓ / ✓ / ✓ | 2/0/0/0 | 详情失败，不进入候选集 |

## 3. Phase3 成功商品统计

共发现 **17 份有效 Phase3 商品快照，涉及 14 个不同 Product ID**。`606232126144`、`600949052422`、`634471255780` 各自出现在两个 Run 中，适合后续验证跨 Run / Product Snapshot 行为。

全部 17 份快照均满足本报告的 Level A 最低条件：可解析 `analysis.json`、`meta.json`、实际存在的原图、至少一个成功 OCR 输入、`combined_text.txt` 和完整商品身份。OCR 的 `TXT/JSON` 只统计逐图产物，不把 `combined_text.txt` 或 manifest 算入。

### 3.1 商品身份与 Artifact Inventory

商品链接按历史 `productUrl` 的域名与 Product ID 规范为无跟踪参数链接，原始完整 URL 仍保存在各自 `analysis.json` / `meta.json` 中，未被修改。

| Source Run / Product ID | 商品（原始 productUrl） | 店铺 | Keyword / Rank | Crawl Time | Detail：原图/截图 | OCR：成功/总数；TXT/JSON | Effects / Keywords | Evidence（总/Seller/UGC） | 排除其他商品 | Review | 兼容 |
| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | --- | --- |
| `20260817T171318` / `606232126144` | [北京同仁堂酸枣仁膏古方桂圆百合茯苓茶桑葚阿胶膏方官方旗舰店](https://detail.tmall.com/item.htm?id=606232126144) | 同仁堂官方旗舰店 | 酸枣仁 / — | 2026-08-17T09:12:59Z | 17/8 | 15/15；15/15 | 助眠；催眠、睡眠 | 2/0/2 | 2 | 是 | A |
| `20260817T181659_batch` / `600949052422` | [正宗炒酸枣仁500g睡眠旗舰店正品粉汤茶熟山枣仁非中药材野生特级](https://detail.tmall.com/item.htm?id=600949052422) | 同芙旗舰店 | 酸枣仁 / — | 2026-08-17T10:12:04Z | 15/0 | 12/12；12/12 | 助眠；失眠、睡眠、辗转反侧 | 5/3/2 | 0 | 是 | A |
| `20260817T181659_batch` / `606232126144` | [北京同仁堂酸枣仁膏古方桂圆百合茯苓茶桑葚阿胶膏方官方旗舰店](https://detail.tmall.com/item.htm?id=606232126144) | 同仁堂官方旗舰店 | 酸枣仁 / — | 2026-08-17T09:12:59Z | 17/8 | 15/15；15/15 | 助眠；催眠、睡眠 | 2/0/2 | 2 | 是 | A |
| `20260828_cdp_smoke2` / `709093313179` | [中药材抓配抓独立包装](https://detail.tmall.com/item.htm?id=709093313179) | 国强大药房旗舰店 | 酸枣仁 / 1 | 2026-08-28T21:36:59+08:00 | 25/12 | 15/15；15/15 | — | 0/0/0 | 0 | 否 | A |
| `20260901_collector_v02_e2e` / `1072912482110` | [炒酸枣仁中药材官方旗舰店正宗野生酸枣仁饮片炒熟纯酸枣仁粉睡眠](https://detail.tmall.com/item.htm?id=1072912482110) | 仁创民声大药房旗舰店 | 酸枣仁 / 1 | 2026-09-02T00:01:03+08:00 | 11/6 | 10/10；10/10 | 助眠；睡眠 | 1/1/0 | 0 | 是 | A |
| `20260901_collector_v02_e2e` / `634471255780` | [南京同仁堂酸枣仁百合茯苓茶酸枣仁膏酸枣仁粉正品养生茶包旗舰店](https://detail.tmall.com/item.htm?id=634471255780) | 阿里健康大药房 | 酸枣仁 / 2 | 2026-09-02T00:01:47+08:00 | 14/8 | 13/13；13/13 | 助眠；入睡、助眠、失眠、安神、睡眠 | 8/6/2 | 10 | 是 | A |
| `20260902T005526_task` / `634471255780` | [南京同仁堂酸枣仁百合茯苓茶酸枣仁膏酸枣仁粉正品养生茶包旗舰店](https://detail.tmall.com/item.htm?id=634471255780) | 阿里健康大药房 | 酸枣仁 / 2 | 2026-09-02T00:57:01+08:00 | 14/8 | 13/13；13/13 | 助眠；入睡、助眠、失眠、安神、睡眠 | 8/6/2 | 10 | 是 | A |
| `20260902T005526_task` / `707564797952` | [野生酸枣仁正宗中药材炒熟纯酸枣仁粉官方旗舰店正品百合茯苓睡眠](https://detail.tmall.com/item.htm?id=707564797952) | 岷农人旗舰店 | 酸枣仁 / 1 | 2026-09-02T00:56:22+08:00 | 23/9 | 17/17；17/17 | 助眠；入睡、安睡、睡眠 | 4/3/1 | 3 | 是 | A |
| `20260902T192913_task` / `600949052422` | [正宗炒酸枣仁500g睡眠旗舰店正品粉汤茶熟山枣仁非中药材野生特级](https://detail.tmall.com/item.htm?id=600949052422) | 同芙旗舰店 | 酸枣仁 / 2 | 2026-09-02T19:30:58+08:00 | 15/7 | 13/13；13/13 | 助眠；失眠、睡眠、辗转反侧 | 5/2/3 | 2 | 是 | A |
| `20260902T192913_task` / `702353081235` | [正宗秦岭深山酸枣仁500g正品包邮酸枣仁粉新货无硫搭百合茯苓泡水](https://item.taobao.com/item.htm?id=702353081235) | 采药夫妻的放心药材 | 酸枣仁 / 1 | 2026-09-02T19:30:18+08:00 | 17/8 | 14/14；14/14 | 助眠；失眠、睡眠 | 3/0/3 | 2 | 是 | A |
| `20260903T014401_task` / `674221193698` | [正品霍山铁皮石斛枫斗官方旗舰店石斛纯粉干条石斛礼盒中药材500g](https://detail.tmall.com/item.htm?id=674221193698) | 别山斛旗舰店 | 铁皮石斛 / 1 | 2026-09-03T01:45:36+08:00 | 31/11 | 26/26；26/26 | — | 0/0/0 | 0 | 否 | A |
| `20260905T160452_task` / `813409599308` | [正宗北京同仁堂铁皮石斛礼盒送父母长辈中秋节实用见面礼滋补正品](https://detail.tmall.com/item.htm?id=813409599308) | 北京同仁堂健康旗舰店 | 铁皮石斛 / 1 | 2026-09-05T16:05:44+08:00 | 17/8 | 14/14；14/14 | — | 0/0/0 | 0 | 否 | A |
| `20260905T161011_task` / `1058871758703` | [无糖孕妇海盐苏打饼干养碱性零食胃酸孕期单独小包装咸味休闲食品](https://detail.tmall.com/item.htm?id=1058871758703) | 熙熙猴台味专卖店 | 减肥饼干 / 3 | 2026-09-05T16:12:24+08:00 | 15/7 | 13/13；13/13 | — | 0/0/0 | 0 | 否 | A |
| `20260905T161011_task` / `652781617371` | [低GI全麦饼干粗粮卡脂肪代餐减无添蔗糖脂压缩解馋孕妇早餐零食品](https://detail.tmall.com/item.htm?id=652781617371) | 碧翠园官方旗舰店 | 减肥饼干 / 2 | 2026-09-05T16:11:53+08:00 | 17/8 | 15/15；15/15 | — | 0/0/0 | 0 | 否 | A |
| `20260905T161011_task` / `673981586940` | [蛋白棒代餐燕麦能量饼干0低无糖精脂肪卡解馋热量谷物饱腹零食品](https://detail.tmall.com/item.htm?id=673981586940) | 兵王的炊事班旗舰店 | 减肥饼干 / 1 | 2026-09-05T16:11:16+08:00 | 30/10 | 27/27；27/27 | 减脂；减脂 | 1/0/1 | 0 | 是 | A |
| `20260905T164428_task` / `682581765399` | [【先咨询--辨体质】四君子汤调理脾胃四神汤茯苓白术健脾养胃茶](https://detail.tmall.com/item.htm?id=682581765399) | 花淡旗舰店 | 茯苓 / 1 | 2026-09-05T16:45:34+08:00 | 17/9 | 15/15；15/15 | — | 0/0/0 | 0 | 否 | A |
| `20260905T164428_task` / `982036041270` | [乐钦特级云南茯苓非中药材正品官方旗舰店无硫泡水干货白茯苓块茶](https://detail.tmall.com/item.htm?id=982036041270) | 阿里健康大药房 | 茯苓 / 2 | 2026-09-05T16:46:10+08:00 | 14/7 | 13/13；13/13 | 助眠；睡眠 | 1/1/0 | 0 | 是 | A |

风险原因归纳：7 个含 seller Evidence 的助眠 Snapshot 写明“当前商品范围内检测到助眠相关表达”；3 个 UGC-only 助眠 Snapshot 明确写明只在用户评价/问答中发现表达；`673981586940` 也明确写明只在用户评价/问答中发现减脂表达；6 个零 Evidence 商品均为“未检测到配置词库中的明确功效表达，仍需人工结合图片质量和未收录表达判断”。这些原因没有在审计中被改写或重新解释。

### 3.2 Evidence Ledger

以下逐条记录全部 **40 条**历史 Evidence。文本只给短摘录；source path 与 line number 保留旧 artifact 的原值。重复 Product 出现在不同 Run 时作为不同 Snapshot 记录。

| Run/Product | Effect | Keyword | Source Type | Origin | Source Path | 文本摘录 |
| --- | --- | --- | --- | --- | --- | --- |
| `20260817T171318/606232126144` | 助眠 | 睡眠 | dom_user_review | user_generated | `dom_text.txt:30` | 评价称“对睡眠有帮助” |
| `20260817T171318/606232126144` | 助眠 | 催眠 | dom_qa | user_generated | `dom_text.txt:38` | 问答称“催眠神器” |
| `20260817T181659_batch/600949052422` | 助眠 | 睡眠 | title | seller_managed | `meta.json#productName:1` | 标题含“睡眠” |
| `20260817T181659_batch/600949052422` | 助眠 | 睡眠 | dom_user_review | user_generated | `dom_text.txt:48` | “睡眠质量好” |
| `20260817T181659_batch/600949052422` | 助眠 | 失眠 | dom_user_review | user_generated | `dom_text.txt:52` | 评价称“对失眠有效果” |
| `20260817T181659_batch/600949052422` | 助眠 | 睡眠 | dom_product | seller_managed | `dom_text.txt:110` | 当前商品 DOM 标题含“睡眠” |
| `20260817T181659_batch/600949052422` | 助眠 | 辗转反侧 | ocr | seller_managed | `ocr/original_007.txt:4` | “整夜辗转反侧” |
| `20260817T181659_batch/606232126144` | 助眠 | 睡眠 | dom_user_review | user_generated | `dom_text.txt:30` | 评价称“对睡眠有帮助” |
| `20260817T181659_batch/606232126144` | 助眠 | 催眠 | dom_qa | user_generated | `dom_text.txt:38` | 问答称“催眠神器” |
| `20260901_collector_v02_e2e/1072912482110` | 助眠 | 睡眠 | title | seller_managed | `meta.json#productName:1` | 标题末尾含“睡眠” |
| `20260901_collector_v02_e2e/634471255780` | 助眠 | 睡眠 | dom_user_review | user_generated | `dom_text.txt:28` | 评价称“对睡眠还是很有好处” |
| `20260901_collector_v02_e2e/634471255780` | 助眠 | 入睡、睡眠 | dom_user_review | user_generated | `dom_text.txt:31` | 评价谈及“睡眠比较轻、入睡困难” |
| `20260901_collector_v02_e2e/634471255780` | 助眠 | 助眠、睡眠 | ocr | seller_managed | `ocr/original_001.txt:30` | “助眠膏、多梦、睡眠质量差” |
| `20260901_collector_v02_e2e/634471255780` | 助眠 | 睡眠 | ocr | seller_managed | `ocr/original_001.txt:41` | “酸枣仁茯苓茶深度睡眠” |
| `20260901_collector_v02_e2e/634471255780` | 助眠 | 失眠、安神 | ocr | seller_managed | `ocr/original_001.txt:43` | “失眠多梦易醒安神” |
| `20260901_collector_v02_e2e/634471255780` | 助眠 | 睡眠 | ocr | seller_managed | `ocr/original_001.txt:57` | “深度睡眠” |
| `20260901_collector_v02_e2e/634471255780` | 助眠 | 睡眠 | ocr | seller_managed | `ocr/original_001.txt:58` | “酸枣仁百合茯苓茶睡眠” |
| `20260901_collector_v02_e2e/634471255780` | 助眠 | 安神 | ocr | seller_managed | `ocr/original_001.txt:60` | OCR 含“安神” |
| `20260902T005526_task/634471255780` | 助眠 | 睡眠 | dom_user_review | user_generated | `dom_text.txt:28` | 评价称“对睡眠还是很有好处” |
| `20260902T005526_task/634471255780` | 助眠 | 入睡、睡眠 | dom_user_review | user_generated | `dom_text.txt:31` | 评价谈及“睡眠比较轻、入睡困难” |
| `20260902T005526_task/634471255780` | 助眠 | 助眠、睡眠 | ocr | seller_managed | `ocr/original_001.txt:30` | “助眠膏、多梦、睡眠质量差” |
| `20260902T005526_task/634471255780` | 助眠 | 睡眠 | ocr | seller_managed | `ocr/original_001.txt:41` | “酸枣仁茯苓茶深度睡眠” |
| `20260902T005526_task/634471255780` | 助眠 | 失眠、安神 | ocr | seller_managed | `ocr/original_001.txt:43` | “失眠多梦易醒安神” |
| `20260902T005526_task/634471255780` | 助眠 | 睡眠 | ocr | seller_managed | `ocr/original_001.txt:57` | “深度睡眠” |
| `20260902T005526_task/634471255780` | 助眠 | 睡眠 | ocr | seller_managed | `ocr/original_001.txt:58` | “酸枣仁百合茯苓茶睡眠” |
| `20260902T005526_task/634471255780` | 助眠 | 安神 | ocr | seller_managed | `ocr/original_001.txt:60` | OCR 含“安神” |
| `20260902T005526_task/707564797952` | 助眠 | 睡眠 | title | seller_managed | `meta.json#productName:1` | 标题含“睡眠” |
| `20260902T005526_task/707564797952` | 助眠 | 睡眠 | dom_qa | user_generated | `dom_text.txt:38` | 问答：“睡眠质量有改善吗” |
| `20260902T005526_task/707564797952` | 助眠 | 入睡 | dom_product | seller_managed | `dom_text.txt:64` | 当前商品选项含“难入睡梦多易醒” |
| `20260902T005526_task/707564797952` | 助眠 | 安睡 | ocr | seller_managed | `ocr/original_004.txt:2` | “安睡整个夜晚” |
| `20260902T192913_task/600949052422` | 助眠 | 睡眠 | title | seller_managed | `meta.json#productName:1` | 标题含“睡眠” |
| `20260902T192913_task/600949052422` | 助眠 | 睡眠 | dom_user_review | user_generated | `dom_text.txt:25` | “睡眠质量好” |
| `20260902T192913_task/600949052422` | 助眠 | 失眠 | dom_user_review | user_generated | `dom_text.txt:29` | 评价称“对失眠多梦有效果” |
| `20260902T192913_task/600949052422` | 助眠 | 失眠 | dom_user_review | user_generated | `dom_text.txt:32` | 评价称“对失眠有效果” |
| `20260902T192913_task/600949052422` | 助眠 | 辗转反侧 | ocr | seller_managed | `ocr/original_007.txt:4` | “整夜辗转反侧” |
| `20260902T192913_task/702353081235` | 助眠 | 睡眠 | dom_user_review | user_generated | `dom_text.txt:28` | 评价期待“睡眠质量有所改善” |
| `20260902T192913_task/702353081235` | 助眠 | 睡眠 | dom_qa | user_generated | `dom_text.txt:32` | 问答讨论“用来治疗睡眠” |
| `20260902T192913_task/702353081235` | 助眠 | 失眠 | dom_qa | user_generated | `dom_text.txt:33` | 问答讨论不同失眠情形 |
| `20260905T161011_task/673981586940` | 减脂 | 减脂 | dom_user_review | user_generated | `dom_text.txt:24` | “适用减脂人群” |
| `20260905T164428_task/982036041270` | 助眠 | 睡眠 | dom_product | seller_managed | `dom_text.txt:53` | 当前商品组合选项含“睡眠不佳” |

## 4. 助眠候选

统计口径分开如下：

- 命中任一助眠条件：**10 个 Snapshot / 7 个不同商品**。
- 其中存在 seller-managed 助眠 Evidence：**7 个 Snapshot / 5 个不同商品**。
- 仅 UGC 命中、没有 seller-managed 助眠 Evidence：`606232126144`（两个 Run）和 `702353081235`。

| 优先级 | Run/Product | Evidence | Seller/UGC | 主要来源 | 评价 |
| --- | --- | ---: | ---: | --- | --- |
| 1 | `20260902T005526_task/707564797952` | 4 | 3/1 | 标题、当前商品 DOM、OCR、Q&A | 最清楚的 seller 正样例；四种来源同时覆盖，原图可定位 |
| 2 | `20260902T005526_task/634471255780` | 8 | 6/2 | OCR、用户评价 | Evidence 最丰富；另排除10条其他商品推荐，适合验证隔离逻辑 |
| 3 | `20260817T181659_batch/600949052422` | 5 | 3/2 | 标题、DOM、OCR、评价 | 旧结构下的混合来源样例，适合历史兼容验证 |
| 4 | `20260901_collector_v02_e2e/634471255780` | 8 | 6/2 | OCR、用户评价 | 与后续 Web Task 内容一致，可验证同 Product 跨 Run 时间线 |
| 5 | `20260901_collector_v02_e2e/1072912482110` | 1 | 1/0 | 标题 | 极简 seller-only 正样例 |
| 6 | `20260905T164428_task/982036041270` | 1 | 1/0 | 当前商品 DOM | 非酸枣仁关键词下的助眠命中，可验证跨关键词呈现 |

`606232126144` 和 `702353081235` 不宜作为“最佳正样例”，因为命中全部来自评论或问答；它们更适合验证 UGC 辅助证据和 weak-evidence 呈现。

## 5. 当前 D2 Bridge 候选

按当前 `config/effect_risk_bridge.json` 的精确 `(effect_label, matched_keyword)` 组合扫描全部 40 条历史 Evidence，结果为：

| Bridge | 要求 | 匹配商品 |
| --- | --- | --- |
| 减肥 | `减脂 + 减肥 → weight_loss` | **0** |
| 壮阳 | `男性相关 + 壮阳 → male_function` | **0** |
| 补肾 | `男性相关 + 补肾 → male_function` | **0** |

历史有效 Phase3 数据中没有可直接跑通当前 D2 完整链的真实商品。

最接近的是 `20260905T161011_task/673981586940`：Effect 为“减脂”，但唯一 Evidence 的 matched keyword 也是“减脂”，不是 Bridge 要求的精确“减肥”；而且来源是用户评价。因此它是很好的 **D2 精确匹配负边界**，但不能被报告成可桥接正样例。搜索关键词“减肥饼干”本身也不能替代 Evidence matched keyword。

## 6. Analysis 成功但 0 Evidence

共有 **6 个 Snapshot / 6 个商品**满足：Detail 有效、OCR 至少一张成功、`analysis.json` 可解析、`detected_effects=[]`、Evidence=0。

| Run/Product | 商品 | 原图 | OCR | 选择价值 |
| --- | --- | ---: | ---: | --- |
| `20260828_cdp_smoke2/709093313179` | 中药材抓配抓独立包装 | 25 | 15/15 | 中断 Run 内仍有完整 Analysis 的边界样例 |
| `20260903T014401_task/674221193698` | 正品霍山铁皮石斛枫斗官方旗舰店… | 31 | 26/26 | 最强零 Evidence 基线：原图/OCR/截图最完整 |
| `20260905T160452_task/813409599308` | 正宗北京同仁堂铁皮石斛礼盒… | 17 | 14/14 | 当前 Web 包装较完整，已有 Recommendation 空态 artifact |
| `20260905T161011_task/1058871758703` | 无糖孕妇海盐苏打饼干… | 15 | 13/13 | “减肥饼干”搜索下的真实无命中样例 |
| `20260905T161011_task/652781617371` | 低GI全麦饼干粗粮卡脂肪代餐… | 17 | 15/15 | 标题有营销词但仍无配置功效命中 |
| `20260905T164428_task/682581765399` | 四君子汤调理脾胃四神汤… | 17 | 15/15 | 茯苓关键词下的无命中样例 |

首选 `674221193698`。它能清晰验证“完成 Detail + OCR + Phase3，但没有发现配置线索”，不会与“根本没有执行 Analysis”混淆。

## 7. 多 Evidence / seller + UGC 候选

### 多 Evidence

- Evidence ≥3：**6 个 Snapshot / 4 个不同商品**。
- 最丰富：`634471255780`，每个 Snapshot 8 条（6 seller、2 UGC），关键词覆盖助眠、入睡、睡眠、失眠、安神。
- `600949052422` 每个 Snapshot 5 条，覆盖标题、当前商品 DOM、OCR、用户评价。
- `707564797952` 有4条，覆盖标题、当前商品 DOM、OCR、用户问答。
- `702353081235` 有3条，但全部为 UGC，不宜作为 seller 正样例。

### seller + UGC 混合

共有 **5 个 Snapshot / 3 个不同商品**：

- `600949052422`：两个 Run 均为混合来源；分别为3/2和2/3。
- `634471255780`：两个 Run 均为6/2。
- `707564797952`：3/1。

这些样例可以直接检验 seller-managed 主要证据默认展开、UGC 辅助证据折叠，以及其他商品推荐 Evidence 被排除的呈现。

## 8. Artifact Compatibility

### 评级结果

- **Level A：17/17 Phase3 Snapshot。** 全部具有 `meta.json`、实际原图、成功 OCR artifact、有效 `analysis.json` 和完整商品身份。
- **Level B：0。** 按本次最低复用定义，没有只剩 Analysis 而缺核心 Detail/OCR 事实的候选。
- **Level C：其余没有有效 `analysis.json` 的 Search-only、collection-only、failed 或 interrupted 商品。** 它们可保留为失败/未执行状态样本，但不应进入 Historical Validation 商品集。

### 当前包装差异

- 17/17 具有 OCR `run_info.json` 与 `combined_text.txt`。
- 16/17 所在 Run 有 `web_snapshot.json`；最早的 `20260817T171318` 没有。
- 11/17 所在 Run 有 `task_request.json`；更早的6个 Snapshot 没有。
- 6/17 已有历史 `inspection_recommendation.json`；其余11个没有。
- 缺当前包装文件不改变旧 Detail/OCR/Phase3 事实，也不降低核心 artifact 的 Level A 评级。若进入第二阶段，应由受控适配层补索引/包装；本轮没有生成任何缺失文件。

## 9. 推荐 Validation Set

推荐 **5 个商品 Snapshot**。当前旧数据无法满足“D2 可桥接正样例”这一项，因此没有用近似关键词冒充；`673981586940` 被保留为 D2 精确匹配负边界。

| Source Run | Product ID | Product Name | Keyword | Crawl Time | Original Images | OCR Success / Total | Effects | Evidence Count | Seller Evidence | UGC Evidence | Bridge Potential | Compatibility | Validation Role | Why Selected |
| --- | --- | --- | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| `20260902T005526_task` | `707564797952` | 野生酸枣仁正宗中药材炒熟纯酸枣仁粉…睡眠 | 酸枣仁 | 2026-09-02T00:56:22+08:00 | 23 | 17/17 | 助眠 | 4 | 3 | 1 | 无助眠 Bridge | A | **最佳助眠 seller Evidence；seller/UGC 分层** | 标题、当前 DOM、OCR 都有 seller 证据；另有 Q&A；OCR 原图可精确定位 |
| `20260903T014401_task` | `674221193698` | 正品霍山铁皮石斛枫斗官方旗舰店… | 铁皮石斛 | 2026-09-03T01:45:36+08:00 | 31 | 26/26 | — | 0 | 0 | 0 | 无 | A | **Analysis 0 Evidence 基线** | Detail、OCR、Phase3 明确成功，但无 Effect/Evidence；与未分析状态边界最清楚 |
| `20260905T161011_task` | `673981586940` | 蛋白棒代餐燕麦能量饼干… | 减肥饼干 | 2026-09-05T16:11:16+08:00 | 30 | 27/27 | 减脂 | 1 | 0 | 1 | **不匹配**：关键词为“减脂”，非“减肥” | A | **D2 exact-match 负边界；UGC-only** | 验证搜索词不冒充 Evidence、近似词不被错误桥接、UGC 仍保持辅助证据 |
| `20260902T005526_task` | `634471255780` | 南京同仁堂酸枣仁百合茯苓茶… | 酸枣仁 | 2026-09-02T00:57:01+08:00 | 14 | 13/13 | 助眠 | 8 | 6 | 2 | 无助眠 Bridge | A | **多 Evidence UI 样例** | Evidence 数最多、关键词丰富，并有10条其他商品推荐被明确排除 |
| `20260817T181659_batch` | `600949052422` | 正宗炒酸枣仁500g睡眠旗舰店… | 酸枣仁 | 2026-08-17T10:12:04Z | 15 | 12/12 | 助眠 | 5 | 3 | 2 | 无助眠 Bridge | A | **旧 Batch / 跨 Run 兼容样例** | 旧结构中仍保有标题、DOM、OCR和评价 Evidence，可验证历史包装适配 |

如果必须缩到3件，保留 `707564797952`、`674221193698`、`673981586940`。如果目标是完整验证 D2 正链，则这批旧数据不足，不能通过降低精确匹配标准来补齐。

## 10. 最佳助眠样例详解

### 身份与产物

- 商品：野生酸枣仁正宗中药材炒熟纯酸枣仁粉官方旗舰店正品百合茯苓睡眠
- Product ID：`707564797952`
- Source Run：`20260902T005526_task`
- 采集时间：`2026-09-02T00:56:22+08:00`
- 店铺：岷农人旗舰店
- 原图：23张，文件均实际存在
- 页面截图：9张
- OCR：17/17成功，逐图 TXT/JSON 均为17份，`combined_text.txt` 存在
- Phase3：`detected_effects=["助眠"]`、`review_required=true`、Evidence=4（seller 3、UGC 1）
- Risk reason：当前商品范围内检测到助眠相关表达，建议人工复核其内容来源、页面语境和是否属于商品功效宣传。

### Evidence 溯源

| Keyword | Origin / Type | Source | 摘要 |
| --- | --- | --- | --- |
| 睡眠 | seller-managed / title | `meta.json#productName:1` | 商品标题直接含“睡眠” |
| 睡眠 | user-generated / dom_qa | `dom_text.txt:38` | 用户问答“睡眠质量有改善吗” |
| 入睡 | seller-managed / dom_product | `dom_text.txt:64` | 当前商品选项含“难入睡梦多易醒” |
| 安睡 | seller-managed / OCR | `ocr/original_004.txt:2` | “安睡整个夜晚” |

OCR Evidence 可直接回溯到：

- 原图：`D:\毕业设计\output\20260902T005526_task\products\707564797952\images\original\original_004.webp`
- OCR 文本：`D:\毕业设计\output\20260902T005526_task\products\707564797952\ocr\original_004.txt`
- OCR JSON：`D:\毕业设计\output\20260902T005526_task\products\707564797952\ocr\original_004.json`

三个文件均实际存在；OCR 文本第2行与 Analysis Evidence 完全一致，均为“安睡整个夜晚”。此外，Analysis 排除了3条 `dom_recommendation` 其他商品内容，说明当前商品证据与推荐商品噪声已经分开。

它适合作为第二版 UI 首个验证样例，因为一个 Snapshot 内即可检查：商品身份、真实图片、OCR全文、seller 主要证据、UGC 辅助证据、Evidence 来源标签、排除其他商品、Review 可用性和无 Recommendation Bridge 的合法空态。

### 当前 Bridge 能力

当前 `effect_risk_bridge.json` 只包含：

- `减脂 + 减肥 → weight_loss`
- `男性相关 + 壮阳 → male_function`
- `男性相关 + 补肾 → male_function`

不存在“助眠”映射。因此该商品 **当前只能验证 Effect/Evidence/Review UI，不能验证 Risk→Substance→Method 链。** 本报告没有新增或修改 Bridge。

## 11. 下一步迁移建议

本轮不执行迁移。第二阶段若获批准，建议：

1. 先建立仅含上述5个 `(sourceRunId, productId)` 的显式 allow-list，保持同 Product 的不同 Run 为独立 Snapshot。
2. 迁移前对 `meta.json`、原图、OCR manifest/TXT/JSON、`combined_text.txt`、`analysis.json` 做只读存在性与哈希清单；任何缺失都降级并停止该商品迁移。
3. 通过单独 validation root 或隔离数据库验证导入，不清空当前数据库，也不改变旧目录。
4. 历史 Recommendation 缺失应呈现“暂不可用”，不得在导入时伪造；若未来获准重新生成，必须作为新的派生产物记录，不覆盖旧 Analysis。
5. 首先验证 `707564797952` 的助眠 UI 和 `674221193698` 的0 Evidence 状态，再验证 `673981586940` 不会被错误桥接。
6. D2 正链仍需另行取得包含精确 `减肥`、`壮阳` 或 `补肾` Evidence 的真实样例；不得把搜索词或近似 Evidence 当成 Bridge 命中。

结论：历史数据具备足够完整的 Detail/OCR/Phase3 artifact，可以安全规划一个小型 Historical Validation Set；但它只能覆盖助眠 Effect/Evidence/Review、零 Evidence、Evidence 分层与旧结构兼容，**不能覆盖当前 D2 Risk→Substance→Method 正链**。
