# 淘宝食药同源风险线索发现 MVP

本项目使用本地 **Python + Playwright + Chrome + PaddleOCR**，从真实淘宝搜索结果中采集商品详情图片与页面文本，并通过配置化规则发现可能需要人工复核的功效表达。

结果只表示页面风险线索，不认定商品违法、功效真实、存在非法添加或检出任何药物。

## 当前完成度

| 能力 | 实现 | 当前验证状态 |
| --- | --- | --- |
| 淘宝实时搜索与商品去重 | `src/taobao_live.py` | 已用真实搜索页验证 |
| 可见 Chrome/CDP 与登录状态复用 | `src/taobao_live.py` | 已验证 |
| 批量详情打开、滚动、DOM/Network 原图采集 | `src/phase1_experiment.py` | 已完成 10 个真实商品采集 |
| PaddleOCR | `src/phase2_ocr.py` | 已在真实详情图上验证 |
| 功效规则、证据来源与推荐区排除 | `src/phase3_analysis.py` | 已在真实商品上验证 |
| 统一命令行、状态隔离、断点续跑 | `main.py` / `src/main.py` | 已验证 |
| 网页数据快照 | `src/web_contract.py` | 已对真实运行目录验证 |
| 本地只读结果 API | `src/local_api.py` | 已对快照和真实图片验证 |
| 本地 Web MVP | `web/index.html` / `web/styles.css` / `web/app.js` | 已接入真实批次、图片、OCR、证据和日志 |

项目代码不依赖 Codex、ChatGPT 桌面应用、Codex Browser 或 Chrome 控制插件。页面出现登录或滑块验证时由用户在项目打开的可见浏览器中手动完成；项目不破解验证码。

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

项目使用本机 Chrome，不要求下载 Playwright 自带 Chromium。PaddleOCR 模型首次运行时按照其官方机制下载，后续使用本机缓存。

## 运行完整流程

```powershell
.\.venv\Scripts\python.exe main.py `
  --keyword 酸枣仁 `
  --candidate-limit 50 `
  --detail-limit 10 `
  --browser-mode cdp `
  --direct-browser
```

说明：

- `--candidate-limit` 表示搜索阶段最多保留多少个去重候选；`--detail-limit` 表示其中前多少个进入详情采集。
- 旧参数 `--limit` 暂时保留，等价于 `--candidate-limit`；新命令应优先使用新参数。
- `--direct-browser` 只让项目打开的浏览器绕过系统代理；如果淘宝在当前网络环境下本来就需要系统代理，可以去掉该参数。
- 项目默认低频逐件采集，遇到登录或验证会等待用户处理。
- `--skip-ocr` 只验证搜索和详情采集，不属于完整端到端验收。
- `--detail-limit 1` 可用于单商品冒烟测试。

## 断点续跑

只对已保存详情执行离线 OCR 和分析，不再访问淘宝：

```powershell
.\.venv\Scripts\python.exe main.py `
  --resume-run output\运行编号
```

继续采集尚未完成的商品详情：

```powershell
.\.venv\Scripts\python.exe main.py `
  --resume-run output\运行编号 `
  --resume-details `
  --browser-mode cdp `
  --direct-browser
```

用户按 `Ctrl+C` 后，正在处理且已有详情元数据的商品会恢复为可续跑的 `detail_collected` 状态。

## 详情滚动策略

采集器不再以页面 70% 或 80% 作为主要停止条件。它优先使用 `#imageTextInfo-container` 的实际底部，并在详情图片数量、已加载图片数量、图片 URL 和容器高度连续稳定后停止。找不到详情容器时，才依次使用推荐区标题、页面底部和 92% 页面比例作为兜底。

每个商品仍保留最大滚动次数，防止动态页面无限增长。新停止策略已通过单元测试，下一次真实商品采集时还需记录 `scrollStopReason` 做回归核对。

## 输出目录

每次运行位于 `output/<run_id>/`：

```text
batch_state.json       逐商品运行状态
products.json          批次结构化结果
products.csv           表格导出
summary.md             人工可读摘要
web_snapshot.json      网页直接读取的稳定数据契约
run.log                运行日志
search/                搜索候选、滚动状态和截图
  search_diagnostics.json  搜索停止原因、耗时、字段缺失与Selector Health
products/<商品ID>/
  meta.json            商品与采集元数据
  images/original/     当前商品详情原图
  page/                概览和分段截图
  ocr/                 单图 OCR 文本、JSON 和 manifest
  analysis.json        风险线索、证据来源和复核建议
```

`batch_state.json`、`products.json` 和 `web_snapshot.json` 使用原子替换写入，网页轮询不会读取到半截 JSON。

## Collector Baseline v0.2 诊断信息

每次实时搜索都会生成 `search/search_diagnostics.json`，记录：

- 请求候选数、实际去重候选数和进入详情数；
- 搜索滚动次数和耗时；
- 明确停止原因，例如 `candidate_limit_reached`、`stagnant_no_new_products`、`max_scrolls_reached`；
- 商品ID、标题、店铺和地区字段覆盖率；
- 登录、人工验证、页面结构异常或其他错误的分类原因。

Selector Health 只负责记录覆盖率并输出告警，不会自动替换选择器。

离线回归测试不访问淘宝，运行命令：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## 运行本地 Web MVP

为已有运行目录生成或刷新网页快照：

```powershell
.\.venv\Scripts\python.exe -m src.web_contract `
  --run-root output\20260828_cdp_smoke2 `
  --stage interrupted `
  --message "真实详情采集已完成，批量OCR可断点续跑"
```

启动本地页面和只读结果接口：

```powershell
.\.venv\Scripts\python.exe -m src.local_api --output-root output --port 8765
```

然后在浏览器打开：

```text
http://127.0.0.1:8765/
```

页面包含风险总览、商品监测、风险研判、采集任务，以及基础词库和统计分析两个待开发占位页。当前网页只能查看真实结果，不能启动采集；“开始采集”按钮因此明确禁用。

结果接口：

- `GET http://127.0.0.1:8765/api/health`：健康检查；
- `GET http://127.0.0.1:8765/api/runs`：运行列表；
- `GET http://127.0.0.1:8765/api/runs/<run_id>`：任务、统计和商品结果；
- `GET http://127.0.0.1:8765/api/runs/<run_id>/files/<relative_path>`：图片、OCR、CSV、JSON 和报告文件。

API 只绑定本机回环地址，当前只读，尚不能从网页启动或停止采集。页面交互确定后，再增加任务控制接口。

## 测试

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

## 真实运行记录（2026-08-28）

运行目录：`output/20260828_cdp_smoke2`

- 关键词：酸枣仁；
- 搜索页识别并去重：46 个商品；
- 入选：10 个商品；
- 完成详情采集：10 个；
- 保存当前商品详情原图：176 张；
- 详情采集失败：0；
- 至少 1 个商品完整完成 OCR、规则分析和报告输出；
- 后续批量 OCR 由用户在验证成功后主动停止，不把未完成商品记作端到端成功。

网页快照见 `output/20260828_cdp_smoke2/web_snapshot.json`。详细阶段结论见 [PROJECT_STATUS.md](PROJECT_STATUS.md)。
