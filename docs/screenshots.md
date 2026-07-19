# A3-Agent v7.1.0 — Screenshots & UI

Screenshot guide for competition presentation and release assets.

## Required Screenshots (7)

| # | Page | What to capture | Key feature |
|:--|:-----|:----------------|:------------|
| 1 | 🏠 学习助手 | Full page with input + capabilities | Main UI, agent cards |
| 2 | 🏆 比赛演示 | Pipeline execution results | Agent timeline bars |
| 3 | 🎯 仪表盘 | KPI cards + explainability chain | Trust metrics |
| 4 | ⚙️ AI模型设置 | Provider selector + API key input | Keyring security |
| 5 | 👤 学习画像 | 6-dimension radar + detail cards | Automated profiling |
| 6 | 📚 学习空间 | Learning path nodes + resources | Personalized plan |
| 7 | 🏗️ 架构概览 | 5-layer architecture diagram | System depth |

## Capture Instructions

```bash
# 1. Start A3-Agent
streamlit run app.py --server.headless true

# 2. Open http://localhost:8501 in Chrome
# 3. Press F11 for fullscreen
# 4. For each page: wait for content to load, then screenshot

# Browser DevTools shortcut:
#   Ctrl+Shift+I → ⋮ → "Capture full size screenshot"
#   Or: gnome-screenshot -w -f docs/images/page-name.png
```

## Screenshot Specifications

- **Resolution**: 1920×1080 (or window capture at full width)
- **Format**: PNG
- **Location**: `docs/images/`
- **Naming**: `a3-{tab}-{feature}.png`

## File Names

```
docs/images/
├── a3-home-learning-assistant.png        # Tab 1: main UI
├── a3-competition-demo-pipeline.png      # Tab 5: demo results
├── a3-dashboard-trust-metrics.png        # Tab 6: KPI cards
├── a3-settings-provider-config.png       # Tab 4: provider selector
├── a3-profile-radar.png                  # Tab 2: 6-dimension profile
├── a3-learning-space-path.png            # Tab 3: learning path
├── a3-architecture-overview.png          # Tab 7: 5-layer diagram
└── a3-welcome-first-run.png              # First-run onboarding
```

## Quick Capture (Linux)

```bash
mkdir -p docs/images
# Start A3, then:
sleep 2
gnome-screenshot -w -f docs/images/a3-home-learning-assistant.png
```

## For Competition Submission

Use **7 screenshots** minimum. If file size is a concern, optimize with:

```bash
# Resize to 1280 width (keeps aspect ratio)
for f in docs/images/*.png; do
    convert "$f" -resize 1280x "$f"
done

# Or compress with pngquant
pngquant --quality=80-95 docs/images/*.png
```
