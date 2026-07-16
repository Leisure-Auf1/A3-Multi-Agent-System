# Render 免费 Web Service 部署指南

> 将 A3 Multi-Agent System 的 Streamlit Demo 部署到 [Render](https://render.com) 免费层。
> 全流程使用 Mock Provider，**零 API Key** 即可运行完整 5-Agent 管道。

---

## 1. 架构概览

```
Render Web Service (free)
  └── streamlit run app.py --server.port $PORT --server.address 0.0.0.0
        └── web/app_v3.py  main()
              └── A3Workflow.run(user_goal)
                    ProfileAgent → PlannerAgent → ResourceAgent
                    → ReviewGate → ReflectionAgent → Memory
                    → EventBus Trace（完整时间线）
```

- 入口文件：`app.py`（项目根目录，自动注入 `sys.path`，不依赖本地绝对路径）
- 部署配置：`render.yaml`（Render Blueprint，仓库根目录）
- 依赖：`requirements.txt`（仅 `streamlit`，其余为 Python 标准库）

---

## 2. Render 创建步骤

### 方式 A — Blueprint（推荐，一键）

1. 登录 [dashboard.render.com](https://dashboard.render.com)
2. **New → Blueprint**
3. 连接 GitHub 仓库 `Leisure-Auf1/A3-Multi-Agent-System`
4. Render 自动读取根目录 `render.yaml`，显示服务 `a3-multi-agent-system`
5. 点击 **Apply** — 自动构建并部署

### 方式 B — 手动创建 Web Service

1. **New → Web Service** → 选择本仓库
2. 按下表填写：

| 配置项 | 值 |
|:-------|:---|
| Name | `a3-multi-agent-system` |
| Runtime | `Python` |
| Branch | `main` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true` |
| Instance Type | `Free` |

3. 在 **Environment** 标签添加环境变量（见下节）
4. **Create Web Service**

部署成功后访问 `https://a3-multi-agent-system.onrender.com`（实际 URL 以 Render 分配为准）。

---

## 3. 环境变量说明

| 变量 | 默认值 | 说明 |
|:-----|:-------|:-----|
| `PYTHON_VERSION` | `3.12.7` | 固定 Python 版本，避免 Render 默认版本漂移 |
| `LLM_PROVIDER` | `mock` | LLM 提供方。`mock` = 内置模拟（零 Key）；`spark` = 讯飞星火 |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | `false` | 关闭 Streamlit 数据收集提示（headless 必需） |
| `XF_SPARK_API_KEY` | *(不设置)* | 仅当 `LLM_PROVIDER=spark` 时需要。在 Render Dashboard 中以 Secret 方式添加，**不要**写进 `render.yaml` |
| `PORT` | *(Render 自动注入)* | 不要手动设置 |

Demo 部署保持 `LLM_PROVIDER=mock` 即可，所有 Agent 均可完整运行。

---

## 4. 启动方式

Render 执行 `render.yaml` 中的命令：

```bash
# Build
pip install -r requirements.txt

# Start
streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
```

本地等价验证：

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
# 打开 http://localhost:8501
```

---

## 5. 常见错误

| 症状 | 原因 | 解决 |
|:-----|:-----|:-----|
| 部署后页面一直转圈 / 无响应 | Start Command 缺少 `--server.address 0.0.0.0`，Streamlit 只监听 localhost | 按上文 Start Command 补全 |
| `Port scan timeout` 部署失败 | 未使用 `$PORT`（写死了 8501） | Start Command 必须使用 `$PORT` |
| 启动卡在 "Welcome to Streamlit" 交互提示 | 非 headless 模式等待输入邮箱 | 加 `--server.headless true` 或设 `STREAMLIT_BROWSER_GATHER_USAGE_STATS=false` |
| `ModuleNotFoundError: No module named 'src'` | 未从仓库根目录启动 | Root Directory 留空（仓库根），入口用 `app.py`（内部已注入 `sys.path`） |
| 首次访问等待 30–60 秒 | 免费层闲置 15 分钟后休眠，冷启动 | 正常现象；演示前先访问一次预热 |
| 学习记录 / Memory 数据消失 | 免费层文件系统为**临时盘**，`storage/memory/` 在重新部署或休眠唤醒后重置 | Demo 可接受；需持久化则挂 Render Disk（付费）或外接数据库 |
| 构建失败 `pip` 版本报错 | Python 版本漂移 | 确认环境变量 `PYTHON_VERSION=3.12.7` |
| 讯飞模式无响应 | `XF_SPARK_API_KEY` 未配置或失效 | 检查 Render Environment 中的 Secret；或切回 `LLM_PROVIDER=mock` |

---

## 6. 验证清单（部署后）

打开服务 URL，在「学习助手」输入：

```
I want to learn Python backend development
```

确认页面展示：

- [ ] ProfileAgent — 学习者画像（6 维雷达）
- [ ] PlannerAgent — 学习路径节点
- [ ] ResourceAgent — 资源推荐卡片
- [ ] ReviewGate — 评审分数（evaluation）
- [ ] ReflectionAgent — 反思总结
- [ ] Trace — EventBus 完整时间线

---

## 7. 相关文档

- [系统架构](../architecture.md)
- HF Spaces 部署：见 `app.py` 注释（同一入口双平台复用）
