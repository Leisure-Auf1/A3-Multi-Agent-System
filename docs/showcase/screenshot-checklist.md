# A3-Agent v7.1.0 — Screenshot Checklist

Required screenshots for README, competition materials, and portfolio.

---

## Capture Settings

- **Resolution**: 1920×1080 (or native 2560×1600)
- **Format**: PNG (lossless)
- **Browser**: Chrome/Edge (light theme recommended)
- **Language**: Chinese UI (default)
- **Window**: Full browser window (not cropped to content)

---

## Required Screenshots

### 1. Welcome Page (首次启动)

**Path**: Launch A3 for the first time → Welcome page appears.

**Expected Content**:
- "A3 智能学习伙伴" title
- Two buttons: "🎭 先体验 Demo" + "🚀 开始配置"
- Clean, inviting design

**Use In**: README header, onboarding documentation

**Status**: ⬜

---

### 2. AI Model Settings (AI模型设置)

**Path**: Configure provider → Tab 4 (AI模型设置).

**Expected Content**:
- Provider selector (dropdown: DeepSeek, OpenAI, Spark, Mock)
- Model selector
- API key input (masked with ••••)
- "🔍 测试连接" button
- "💾 保存并开始使用" button
- Connection status indicator

**Use In**: README (security highlight), competition docs

**Status**: ⬜

---

### 3. Learning Assistant (学习助手)

**Path**: Main UI → Tab 1 (学习助手).

**Expected Content**:
- Text input area with placeholder: "描述你想学习的内容..."
- "🚀 开始分析" button
- Agent execution results (after submitting)
- Profile card showing 6 dimensions
- Learning plan with structured steps
- Resource cards (document, exercise, mindmap, etc.)

**Use In**: README (core feature), presentation slides

**Status**: ⬜

---

### 4. Student Profile (学习画像)

**Path**: Tab 2 (学习画像).

**Expected Content**:
- 6-dimension radar/spider chart or card layout
- Dimensions: 知识水平, 学习风格, 认知能力, 兴趣偏好, 学习动机, 时间可用性
- Profile summary in natural language
- Last updated timestamp

**Use In**: Competition docs (agent-design), presentation (Slide 4)

**Status**: ⬜

---

### 5. Competition Demo (比赛演示)

**Path**: Tab 5 (比赛演示).

**Expected Content**:
- "运行完整 Pipeline" button
- Agent execution timeline (horizontal bars, color-coded per agent)
- Agent output cards: ProfileAgent → PlannerAgent → ResourceAgent → EvaluationAgent → ReflectionAgent
- Total execution time display
- Frozen fixture indicator: "使用演示数据"

**Use In**: README (demo highlight), competition presentation

**Status**: ⬜

---

### 6. Dashboard (仪表盘)

**Path**: Tab 6 (仪表盘).

**Expected Content**:
- KPI cards: Correctness (正确率), Personalization (个性化), Coverage (覆盖率)
- Agent execution timeline (horizontal bars with timestamps)
- Explainability chain: decision tree or flow diagram
- Trust metrics panel
- Performance comparison (Mock vs LLM)

**Use In**: Documentation (evaluation-design), presentation (Slide 6)

**Status**: ⬜

---

### 7. Architecture Overview (架构概览)

**Path**: Tab 7 (架构概览).

**Expected Content**:
- 5-layer architecture diagram (vertical or horizontal layout)
- Each layer labeled: Presentation → Agent Pipeline → Intelligence → Trust → Data
- Agent details section (expandable)
- Technology stack listing
- Veritas-Core dependency indicator

**Use In**: README (architecture section), all presentation slides

**Status**: ⬜

---

## Optional Screenshots

### O1. Windows Desktop Launcher

**Path**: Double-click `A3-Agent.exe` → terminal window.

**Expected Content**:
- 5-stage launcher output:
  ```
  [1/5] Initializing user data... [OK]
  [2/5] Starting AI Backend... [OK]
  [3/5] API health check... [OK]
  [4/5] Starting Streamlit... [OK]
  [5/5] Opening browser: http://127.0.0.1:8501
  ```

**Use In**: README (Windows section), release notes

**Status**: ⬜

### O2. GitHub Release Page

**Path**: https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/tag/v7.1.0

**Expected Content**:
- Release title + description
- 4 asset download links (Linux .tar.gz, Linux .sha256, Windows .zip, Windows .sha256)
- Release notes with verification table

**Use In**: README (download section)

**Status**: ⬜

---

## Screenshot Naming Convention

```
screenshots/
├── 01-welcome.png
├── 02-settings.png
├── 03-learning-assistant.png
├── 04-student-profile.png
├── 05-competition-demo.png
├── 06-dashboard.png
├── 07-architecture.png
├── o1-windows-launcher.png
└── o2-github-release.png
```

---

## Post-Processing

1. **Crop**: Remove browser chrome (tabs, bookmarks bar) — keep only the application UI
2. **Resize**: Max width 1200px for GitHub README compatibility
3. **Compress**: PNG → lossless optimization (use `pngquant` or `optipng`)
4. **Annotate**: Add numbered labels for key UI elements (optional)
5. **Border**: Add 1px light gray border for definition against white backgrounds

---

## Tools

- **Windows**: Snipping Tool (Win+Shift+S) or Greenshot
- **Linux**: Flameshot or GNOME Screenshot
- **CLI**: `import -window root screenshot.png` (ImageMagick)
