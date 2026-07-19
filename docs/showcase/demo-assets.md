# A3-Agent v7.1.0 — Demo Assets & Screenshots

Guide for capturing, organizing, and using screenshots and demo assets for competition submission and portfolio presentation.

---

## Required Screenshots (8)

| # | Page | File Name | Key Feature |
|:--|:-----|:----------|:------------|
| 1 | Welcome | `a3-welcome.png` | First-run onboarding wizard |
| 2 | Home | `a3-home.png` | Main learning assistant UI |
| 3 | Demo | `a3-demo-pipeline.png` | Competition one-click execution |
| 4 | Dashboard | `a3-dashboard.png` | KPI cards + timeline |
| 5 | Settings | `a3-settings.png` | Provider selector + keyring |
| 6 | Profile | `a3-profile.png` | 6-dimension radar chart |
| 7 | Learning Space | `a3-learning-space.png` | Path nodes + resources |
| 8 | Architecture | `a3-architecture.png` | 5-layer system diagram |

---

## Capture Instructions

```bash
# 1. Start A3 fresh (no config)
rm -f ~/.a3-agent/config/llm.json
streamlit run app.py --server.headless true

# 2. Wait for browser, enter Demo mode

# 3. Capture each page (Linux):
gnome-screenshot -w -f docs/images/a3-welcome.png    # Welcome page
gnome-screenshot -w -f docs/images/a3-demo-pipeline.png  # After running demo
gnome-screenshot -w -f docs/images/a3-dashboard.png   # Dashboard tab
gnome-screenshot -w -f docs/images/a3-settings.png    # Settings tab
gnome-screenshot -w -f docs/images/a3-profile.png     # Profile tab
gnome-screenshot -w -f docs/images/a3-learning-space.png  # Learning tab
gnome-screenshot -w -f docs/images/a3-architecture.png # Architecture tab
gnome-screenshot -w -f docs/images/a3-home.png        # Home tab

# 4. Optimize (optional):
for f in docs/images/*.png; do
    convert "$f" -resize 1280x "$f"
    pngquant --quality=80-95 --ext .png --force "$f"
done
```

## Windows Capture

```batch
REM Use Snipping Tool (Win+Shift+S) or:
REM Chrome DevTools → ⋮ → "Capture full size screenshot"
```

---

## Demo Video

See [demo-video-script.md](demo-video-script.md) for the 5-minute recording script.

**Recording settings**:
- 1920×1080, 30fps
- OBS Studio or GNOME Screen Recorder
- Separate microphone track for narration

---

## Architecture Diagram

The architecture diagram is embedded in:
- `web/architecture_overview.py` → rendered live in Streamlit
- `docs/competition/architecture.md` → ASCII art version
- `docs/showcase/architecture-presentation.md` → slide-ready format

---

## File Locations

```
docs/
├── images/                              ← Screenshots go here
├── showcase/
│   ├── demo-video-script.md             ← 5-min recording guide
│   ├── architecture-presentation.md     ← Slide deck outline
│   ├── internship-resume.md             ← Resume project description
│   └── demo-assets.md                   ← This file
├── screenshots.md                       ← Detailed capture specs
└── competition/
    ├── demo-script.md                   ← 5-min live presentation
    ├── architecture.md                  ← Technical architecture
    └── benchmark.md                     ← Performance data
```
