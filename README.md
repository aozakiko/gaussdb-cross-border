# GaussDB 跨境电商订单监控中心

该项目基于 **FastAPI + 原生前端** 搭建了一个“跨境电商订单监控中心”，依托 GaussDB 的高可用分布式能力管理海量订单：

- 后端：使用 SQLAlchemy/Pydantic 定义跨境订单模型（订单号、渠道、目的国、币种、金额、物流状态、运单号、风控优先级等），提供 REST API、Jinja2 后台和 Flink 分析接口。
- 前端：纯静态 HTML/CSS/JS + Chart.js，内置仪表盘（GMV、在途、异常等 KPI）、订单录入表单、过滤列表、状态可视化。
- 数据：附带 `data/orders_seed.csv`，可一次性导入 GaussDB 进行演示；同时提供 `scripts/generate_seed.py` 生成更多数据。

## 目录结构

```
backend/            # FastAPI + SQLAlchemy + Flink 服务端
frontend/           # 原生 HTML/CSS/JS 单页应用
docker-compose.yml  # 一体化前后端 + GaussDB (开发用)
docker/gaussdb-pseudo-distributed.yml # 伪分布式 GaussDB 编排
```

## 快速开始（开发机）

1. **准备 GaussDB**：本仓库已在 `backend/.env` 中预配置了你给出的主库：`192.168.237.101:26000 / mydb / omm / 1234@abc`。如需修改，编辑该文件即可。
	- 若要在本地快速启动 demo 数据库，可运行 `docker compose --profile local-db up gaussdb` 启动内置的 openGauss 容器，然后把 `.env` 改回 `GAUSS_HOST=gaussdb`。
2. **推荐：使用 Conda 创建虚拟环境**（可避免系统 Python 缺少 SSL 等问题）：

```powershell
conda env create -f environment.yml
conda activate gaussdb-web
python -m pip install -r backend\requirements.txt  # 如需额外依赖
cd backend
uvicorn app.main:app --reload
```

3. **或使用 venv**：

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. **前端**：使用任意静态服务器（如 VS Code Live Server 或 `python -m http.server --bind 127.0.0.1 5173`）打开 `frontend/index.html`，在顶部输入 API 地址（默认 `http://localhost:8000`）。
5. **后端可视化控制台**：访问 `http://localhost:8000/`，即可在后台完成订单录入/状态切换/数据看板：
	- KPI：订单总数、在途、异常、累计 GMV；
	- 表单：订单号、渠道、目的国、币种、金额、运单号、履约专员、SLA 备注等；
	- 列表：支持 inline 状态切换、删除操作，可直观查看最新 50 条订单；
	- 图表：基于 Chart.js 显示跨境履约状态分布。

## Docker 化部署

```powershell
# 使用已有 GaussDB：只启动前后端，并读取 backend/.env 中的连接信息
docker compose up --build backend frontend

# 若需要本地容器版 GaussDB，则启用 local-db profile
docker compose --profile local-db up --build
```

- 后端镜像基于 `python:3.11-slim`，位于 `backend/Dockerfile`。它会在启动时加载 `backend/.env`。
- 前端镜像基于 `nginx:alpine`，位于 `frontend/Dockerfile`。
- `docker-compose.yml` 中的 `gaussdb` 服务被标记为 `local-db` profile，不会默认启动，避免与你真实的主备集群冲突。

## 伪分布式 GaussDB（容器化）

`docker/gaussdb-pseudo-distributed.yml` 提供了 **1 主 2 备** 的编排示例：

```powershell
cd docker
docker compose -f gaussdb-pseudo-distributed.yml up -d
```

> 初次启动后，请登录主节点执行 `gs_ctl build -b full -D /var/lib/opengauss/data -Z single_node` 来初始化备机，并确保 `pg_hba.conf` 中允许备机复制。更多调优可参考 openGauss 官方文档。

## Flink 分析任务

- `app/services/flink_job.py` 使用 PyFlink Table API 读取 `records` 数据，统计状态/负责人分布。
- 若运行环境未安装 PyFlink，会自动降级为原生 SQL 统计并在响应中说明原因。
- 通过 `FLINK_JOB_NAME`、`FLINK_PARALLELISM` 控制作业名称与并行度，便于对接独立 Flink 集群。

## 实验报告

完整的部署、配置与验证步骤见 `docs/实验报告.md`，涵盖：

1. 源码级编译安装 GaussDB（本地 VM，一主两备）
2. 容器化伪分布式部署（云开发者空间）
3. Web 前端、后端、Flink 作业实现细节
4. Docker 镜像制作与推送
5. 常见问题与排障

## 使用手册 & 数据字典

- `docs/跨境订单使用手册.md`：启动方式、前后端入口、典型工作流、导入测试数据步骤。
- `docs/跨境订单数据字段.md`：列出了 `records` 表所有字段（含类型、含义、示例）。

## 已有数据库字段升级

如果你的 GaussDB 集群在早期版本只包含基础字段（title/description/status 等），请首先运行以下脚本，为 `records` 表自动补齐跨境订单所需的 7 个新字段（订单号、渠道、目的国、币种、金额、运单号、下单时间）并添加唯一约束：

```powershell
conda activate gaussdb-web
cd backend
python scripts/upgrade_records_schema.py
```

脚本会：

- 按需新增列并设置默认值/非空约束；
- 为旧数据补写占位值（如 `order_number = LEGACY-<id>`）；
- 创建 `order_number` 唯一约束，保证 API 的幂等性；
- 多次执行也安全（幂等检查）。

运行成功后即可重新启动 FastAPI（或直接刷新后台仪表盘），再也不会出现 `column ... does not exist` 的 500 报错。

## 快速导入示例数据

完成库表结构升级后，如需一键导入 100 条跨境订单样例，可使用仓库附带的 CSV + 导入脚本：

```powershell
conda activate gaussdb-web
cd backend
python scripts/import_orders_seed.py
```

脚本会读取 `data/orders_seed.csv`，跳过已存在的订单号，仅插入缺失的记录。导入完成后刷新后台/前端即可查看实时统计与表格。

## 测试

```powershell
cd backend
pytest
```

> 运行测试前请确保真实 GaussDB 已就绪并在 `.env` 中配置好连接信息；如需单独运行文件，可执行 `set PYTHONPATH=%cd%\backend`（PowerShell 对应 `$env:PYTHONPATH = "$PWD\backend"`）。

测试会直接连接 GaussDB 并在执行前清空 `records` 表，请勿在生产库上运行。

## 样例数据导入

1. 生成或刷新数据集：

	```powershell
	conda activate gaussdb-web
	cd d:/HuaweiMoveData/Users/destiny/Desktop/gaussdb
	python scripts/generate_seed.py
	```

2. 通过 `psql` 导入到 GaussDB（确保目标库已存在 `records` 表结构）：

	```sql
	\copy records(title, description, status, priority, owner, order_number, sales_channel, destination_market, currency, order_amount, tracking_number, order_date)
	FROM 'data/orders_seed.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');
	```

3. 刷新前端或后台控制台即可看到 100 条跨境订单示例，便于进行过滤、状态更新、Flink 聚合等操作。

## 下一步

- 可扩展多币种汇率折算、SKU 维度分层、异常告警推送。
- 引入实时流（Flink Streaming 或 Spark Streaming）对在途/异常状态进行毫秒级监测。
- 衔接企业自建 ES/ClickHouse 做多维检索与 BI 展示。
