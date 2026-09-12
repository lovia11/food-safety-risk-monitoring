# 网络食品风险线索发现与抽检辅助筛查系统

本项目面向网络食品监管/企业分析场景，从商品搜索页与详情页保留页面证据，执行 OCR 和线索分析，结合受治理知识生成抽检辅助建议，并支持人工复核与抽检清单。

它发现的是**页面风险线索**。它不自动判定违法，不验证功效真实性，不表示实验室检出药物，也不是风险概率预测或自动执法系统。

## 快速启动

稳定验证环境为 Windows + Python 3.10.0。Node/npm 使用本机兼容版本；前端依赖由 `package-lock.json` 固定。

```powershell
Set-Location D:\毕业设计-ux
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Set-Location frontend
npm ci
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -m src.local_api --output-root output --port 8765
```

打开 `http://127.0.0.1:8765/`。首次浏览器采集/OCR 运行可能需要下载运行时资源；不要绕过淘宝登录、CAPTCHA 或人工验证。

## Backend

生产式本地入口：

```powershell
.\.venv\Scripts\python.exe -m src.local_api --output-root output --port 8765
```

服务由 `ThreadingHTTPServer` 提供，默认读取 `frontend/dist`，使用 SQLite schema 8，并从版本化配置加载监测、风险和检验知识。运行参数可用以下命令查看：

```powershell
.\.venv\Scripts\python.exe -m src.local_api --help
```

根目录 `main.py`/`src.main` 保留 CLI、测试和调试能力。Web 任务遇到登录/验证时由 `ManualActionGate` 协调，HTTP 线程不操作 Playwright page。

## Frontend

当前前端位于 `frontend/`，技术栈为 React、TypeScript、Vite、Tailwind CSS 4 与 Lucide React。开发模式可分别启动后端和 Vite：

```powershell
# terminal 1, repository root
.\.venv\Scripts\python.exe -m src.local_api --output-root output --port 8765

# terminal 2
Set-Location frontend
npm run dev
```

Vite 将 `/api` 代理到 `http://127.0.0.1:8765`。当前页面为商品总览、排查档案、抽检清单。

## OCR setup

OCR 的受支持稳定组合固定为：

```text
Python 3.10.0
paddlepaddle==3.2.0
paddleocr==3.7.0
paddlex==3.7.2
PP-OCRv6
BOS model source
CPU
```

`requirements-ocr.txt` 负责锁定关键版本，`requirements.txt` 会包含它。必须始终使用同一个解释器执行 `python -m pip` 和服务，不要混用系统 `pip`。可核对：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show paddlepaddle paddleocr paddlex
```

OCR 会记录运行环境和失败诊断。模型缓存属于本地运行环境，不提交仓库。

## Tests

```powershell
# repository root
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"

# frontend
Set-Location frontend
npm run test:workflow
npm run typecheck
npm run build
```

涉及 Historical Validation builder 时，同时运行当前对应的定向测试模块。各阶段完整 Gate 见 [Test and Acceptance V2](docs/TEST_ACCEPTANCE_V2.md)。

## 数据目录与事实源

- `output/<run_id>/`：原始采集与处理事实，包括页面、图片、OCR、分析与派生产物。
- `data/app.db`：查询索引，以及当前 Review/Sampling 业务状态；重建前必须保护人工决定。
- `config/`：运行时使用的受治理、版本化知识与监测配置。
- frozen Sampling export：导出时不可变的历史抽检清单事实。
- Historical Validation Set：真实测试/演示样例，不代表 production coverage。

不要提交 `output/`、数据库、浏览器 profile、OCR cache 或 `frontend/dist`。

## Canonical documentation

后续开发先读根目录 [AGENTS.md](AGENTS.md)，再按需要阅读：

- [Current System Status](docs/CURRENT_SYSTEM_STATUS.md)
- [Product Requirements V2](docs/PRODUCT_REQUIREMENTS_V2.md)
- [System V2 Architecture](docs/SYSTEM_V2_ARCHITECTURE.md)
- [Domain Model V2](docs/DOMAIN_MODEL_V2.md)
- [UX Specification V2](docs/UX_SPEC_V2.md)
- [Knowledge Governance](docs/KNOWLEDGE_GOVERNANCE.md)
- [Implementation Roadmap V2](docs/IMPLEMENTATION_ROADMAP_V2.md)
- [Test and Acceptance V2](docs/TEST_ACCEPTANCE_V2.md)
- [Architecture Decision Records](docs/decisions/README.md)
- [Project Status](PROJECT_STATUS.md)

`docs/archive/**` 仅为历史资料，永不作为当前规范。
