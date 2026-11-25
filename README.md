# 麒翼睿策 · Kylin Ops Agent
此项目获得第十五届‘中国软件杯’大学生软件设计大赛西部赛区三等奖

麒翼睿策（Kylin Ops Agent）是面向 Linux / 银河麒麟的智能运维平台，将资源监控、自然语言任务编排、命令风险审查、人工审批、工具执行和操作审计整合到同一个 Web 界面中。

用户可以描述运维目标，由 Agent 编排任务，并结合安全规则与 BERT 模型评估命令风险；需要授权的操作经管理员审批后执行，执行过程和结果保存为任务记录与审计日志。平台还提供实时资源监控、阈值告警，以及基于银河麒麟 FAQ 的本地知识检索，方便排查系统问题。

前端使用 Vue 3、Vite、Element Plus 和 Pinia；后端使用 FastAPI、SQLAlchemy 和 SQLite；风险分析使用 BERT 与 Captum Token 归因；知识检索使用 Sentence Transformers、FAISS 和重排模型。自然语言规划通过 DeepSeek API 完成，运维工具通过 MCP TCP 服务执行。

[使用说明](https://my.feishu.cn/docx/Zmh8dUnBnoK65ExHJ5wc2Cncn4b) · [架构图](docs/architecture.svg)

## 公网访问

**在线访问：[麒翼睿策 · Kylin Ops Agent](http://101.34.208.139/)**

平台需要登录后使用，不提供公开的默认账号密码。注册运维人员或审计人员需要部署人员提供对应角色的注册密钥。
- 运维人员密钥:OPERATOR_REGISTER_KEY
- 审计人员密钥:AUDITOR_REGISTER_KEY

## 项目功能

- 用户注册、登录、角色权限与管理员审批。
- CPU、内存、网络、磁盘和进程监控，支持 WebSocket 实时推送。
- 自然语言运维任务编排、命令安全审查、BERT 风险分析、执行记录与可用命令的回滚。
- 阈值告警、人工授权 Agent 接手、任务追踪和审计日志。
- 银河麒麟 FAQ 检索、运维任务记忆检索与写回。
- 工具启用 / 禁用、服务器文件管理、人员管理、站内消息和密码修改。


## 大文件下载
网盘模型包包含 BERT 推理模型单包 audit_model_v1.tar.gz，以及 RAG 模型分卷包 models.tar.gz.part-00 至 models.tar.gz.part-09。


| 外部资源 | 下载链接 | 解压后的目录 |
| --- | --- | --- |
| BERT 运维审计模型 | **https://pan.baidu.com/s/1zVwzuorSjWfCDEmZuHGSxA?pwd=sze8 提取码: sze8** | `audit_model_v1/` |
| RAG Embedding 与重排模型 | **https://pan.baidu.com/s/1zVwzuorSjWfCDEmZuHGSxA?pwd=sze8 提取码: sze8** | `models/` |

下载到项目根目录后，先解压 audit_model_v1.tar.gz，再执行 cat models.tar.gz.part-* > models.tar.gz ，合并分卷并解压 models.tar.gz。完成后应得到 audit_model_v1/、models/paraphrase-multilingual-MiniLM-L12-v2/ 与 models/ms-marco-MiniLM-L-6-v2/ 三个模型目录，分别用于 BERT 风险推理、RAG 向量检索与 RAG 重排。
```text
audit_model_v1/
  config.json
  model.safetensors
  vocab.txt
  ...
models/
  paraphrase-multilingual-MiniLM-L12-v2/
  ms-marco-MiniLM-L-6-v2/
```

## 本地部署

建议使用 Linux、Python 3.11 和 Node.js 20。系统工具依赖服务器已有命令及运行用户权限；例如 `systemctl`、`journalctl`、`ip`、`ss`、`lsblk` 等。部分操作需要管理员授权。

### 1. 安装依赖并配置

在项目根目录执行：

```bash
bash scripts/install_runtime.sh
cp .env.example .env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

编辑 `.env`：

- `SECRET_KEY`：填写上面生成的随机值，用于 JWT 签名，不能为空。
- `OPERATOR_REGISTER_KEY`、`AUDITOR_REGISTER_KEY`：分别配置运维人员、审计人员注册密钥；留空会关闭相应角色的自主注册。
- `DEEPSEEK_API_KEY`：填写 DeepSeek API 密钥；`DEEPSEEK_BASE_URL` 默认为 `https://api.deepseek.com`，`DEEPSEEK_MODEL` 默认为 `deepseek-flash`。
- `APPROVE_SECRET`：配置桌面弹窗审批接口密钥。

下载并放置上面的两份模型。启动脚本会读取根目录 `.env`，已有环境变量优先。自定义模型和数据库位置时使用绝对路径。

### 2. 构建前端

```bash
cd operations-and-maintenance
npm ci
npm run build
cd ..
```

### 3. 创建管理员并启动

```bash
venv/bin/python scripts/create_admin.py --username your-admin-name
bash scripts/start_all.sh
```

按提示设置自己的管理员密码

- 项目页面：<http://127.0.0.1:8000>
- 后端 API 文档：<http://127.0.0.1:8000/docs>
- 后端健康检查：<http://127.0.0.1:8000/health>
- 风险推理健康检查：<http://127.0.0.1:8001/health>

运维人员和审计人员可在注册页使用对应注册密钥创建账号。开发前端时，在后端启动后运行 `npm run dev`，访问终端显示的地址；Vite 会代理 API 和 WebSocket 到后端。

需要独立运行 MCP TCP 工具服务时：

```bash
cd program2
../venv/bin/python -m app.services.mcp_protocol_server
```

默认连接 `127.0.0.1:8765`。TCP 服务不可用时，后端会回退到本地真实工具执行。


## Docker 部署

先放好模型并填写 `.env`，然后执行：

```bash
docker compose up -d --build
docker compose exec backend python /app/scripts/create_admin.py --username your-admin-name
```

访问 <http://127.0.0.1:8000>。数据库保存在 `runtime/`，运维记忆保存在 `data/rag_store/`，两个模型目录以只读方式挂载。

**容器监控和命令执行针对容器自身环境。** 如需管理宿主机的进程、文件、日志和 systemd 服务，请使用本地部署方式运行后端。

## 目录结构

```text
operations-and-maintenance/  Vue 前端源码与 npm 锁文件
program2/                   FastAPI 后端、编排器、监控及 MCP 工具
inference_service.py        BERT 风险推理与 Token 归因
kylin_rag.py                FAQ 建库与检索
kylin_faq.index             FAQ 向量索引
kylin_faq_meta.pkl          FAQ 元数据
scripts/                    安装、启动、管理员创建与打包脚本
docs/                       架构图
tests/                      清理后的启动与监控回归检查
audit_model_v1/             外部下载，Git 忽略
models/                     外部下载，Git 忽略
data/rag_store/             运行时生成，Git 忽略
```

