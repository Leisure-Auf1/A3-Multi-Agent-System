# A3 比赛最终检查清单

> Phase 18 — Competition Final Freeze
> A3 v3.0 · 2026-07-13

---

## 一、启动步骤（< 2 分钟）

```bash
# 1. 进入项目目录
cd projects/A3-Multi-Agent-System

# 2. 安装依赖（仅需 streamlit）
pip install streamlit

# 3. 启动比赛前端
streamlit run web/app_v3.py
```

**预期结果:** 浏览器自动打开，显示 "A3 智能学习伙伴" 三标签页面。

---

## 二、Demo 流程（5 分钟）

| 时间 | 场景 | 操作 | 标签页 |
|:-----|:-----|:-----|:------|
| 0:00-0:30 | 开场 | 展示 Hero 区域和 6 个能力卡片 | Tab 1 |
| 0:30-1:00 | 输入 | 点击 "🎓 多智能体AI" 快速示例 → 点击 "🚀 开始分析" | Tab 1 |
| 1:00-1:30 | Agent 工作 | 观察 4 个 Agent 状态依次完成 (EventBus 驱动) | Tab 1 |
| 1:30-2:30 | 画像展示 | 切换到 Tab 2 → 展示雷达图 + 6 维卡片 | Tab 2 |
| 2:30-4:00 | 学习空间 | 切换到 Tab 3 → 路径节点 + 6 类资源 + 可信度 | Tab 3 |
| 4:00-4:30 | 时间线 | 滚动到 Agent 执行时间线 → 展示 EventBus 数据 | Tab 3 |
| 4:30-5:00 | 缓冲 | Q&A 准备 | — |

---

## 三、API 配置

### 3.1 比赛模式（讯飞星火）

```bash
export LLM_PROVIDER=spark
export XF_API_KEY="your-xunfei-spark-api-key"
export LLM_MODEL=spark-pro
streamlit run web/app_v3.py
```

### 3.2 演示模式（离线/Mock）

```bash
# 默认即为 Mock 模式，无需任何配置
streamlit run web/app_v3.py
```

### 3.3 验证 API 配置

```bash
# 检查 Provider 状态
python -c "
from src.core.provider_factory import get_provider_info
import json
print(json.dumps(get_provider_info(), indent=2, ensure_ascii=False))
"
```

---

## 四、模式切换

| 模式 | 环境变量 | 引擎 | 适用场景 |
|:-----|:---------|:-----|:---------|
| 🚀 Spark | `LLM_PROVIDER=spark` + `XF_API_KEY` | XunfeiSparkProvider | 比赛正式演示 |
| 🤖 Mock | `LLM_PROVIDER=mock`（默认） | MockLLMProvider | 开发/离线/Demo 备份 |
| 📏 Rule | `LLM_PROVIDER=none` | None (pure rule) | Fallback 展示 |

**切换方式:** 在 App V3 启动前设置环境变量，或在 ProviderFactory 调用处传参。

---

## 五、应急方案

| 情况 | 现象 | 应对 |
|:-----|:-----|:-----|
| Spark API 无响应 | ProfileAgent 报错 | 自动 fallback 到 rule 模式，或重启为 Mock 模式 |
| Streamlit 崩溃 | 页面白屏 | 重新 `streamlit run web/app_v3.py` |
| 网络断开 | API 超时 | 切换 Mock 模式，强调 "多模型兼容 + fallback 设计" |
| 浏览器卡顿 | Tab 切换慢 | 刷新页面，数据在 Session State 中保留 |
| 评分质疑 | 评委认为 "Mock 不是真 AI" | 切换 Spark 模式（如有 API key）或解释 "LLMProvider 抽象层" |
| 时间不够 | 5 分钟超时 | 跳过 Trust Panel 和 Timeline，直接总结 |

---

## 六、答辩重点（5 个核心信息）

### 1. 多智能体，不是单 LLM
> "12 个专用 Agent 通过 EventBus 和 Memory 协同，每个 Agent 只做一件事，做到最好。"

### 2. 讯飞星火，多模型兼容
> "核心推理引擎采用讯飞星火 Spark Pro。LLMProvider 抽象层支持多模型切换，不修改 Agent 代码。"

### 3. 个性化，不是硬编码
> "6 维学习画像从自然语言自动提取，同一课程、不同学生 → 完全不同的路径和资源。"

### 4. 可信评估，不是黑盒
> "知识根基验证 + ReviewGate 三道门禁 + 幻觉风险监控。每份输出都有置信度分数。"

### 5. 自改进闭环
> "Evaluator 评分 → MetaReflector 分析 → ExperienceMemory 记录 → ImprovementLoop 改进。"

---

## 七、比赛日检查清单

### 技术准备
- [ ] 比赛电脑上 `pip install streamlit` 完成
- [ ] `python -m pytest tests/ -q` → 241 passed
- [ ] `streamlit run web/app_v3.py` 启动正常
- [ ] 三个 Tab 切换流畅
- [ ] 快速示例按钮工作
- [ ] Agent Pipeline 正确完成 4 步
- [ ] EventBus 时间线显示真实数据

### API 准备（如使用 Spark）
- [ ] `XF_API_KEY` 环境变量已设置
- [ ] API key 24 小时内验证过
- [ ] 备用 API key 准备
- [ ] Mock 模式备用方案确认

### 内容准备
- [ ] README.md 内容准确
- [ ] Demo 脚本熟记（5 分钟时间点）
- [ ] 8 个 Q&A 答案熟悉
- [ ] 知道如何切换 Mock/Spark/Rule 模式

### 外观准备
- [ ] 浏览器全屏（F11）
- [ ] 字体缩放 125%
- [ ] 终端窗口不显示
- [ ] 通知关闭

---

## 八、最终比赛版本信息

- **版本号:** A3 v3.0
- **Agent 数量:** 12
- **资源类型:** 6
- **测试数量:** 241 passed
- **知识库:** 6 章 / 46 概念 / 24 习题
- **前端:** Streamlit 3-tab product UI
- **核心模型:** Xunfei Spark Pro
- **比赛就绪度:** 98%
