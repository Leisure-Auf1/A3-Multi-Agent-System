# Demo Fixtures — Competition-Ready Demo Data

Frozen demo data for stable competition/workshop demonstrations.
These fixtures bypass the full agent pipeline and provide deterministic output.

## Files

| File | Purpose | Use Case |
|:-----|:--------|:---------|
| `sample_profile.json` | 6-dimension student profile | Demo ProfileAgent output |
| `learning_trace.json` | Full agent pipeline trace | Demo timeline visualization |
| `generated_resources.json` | 6 resource recommendations | Demo resource cards |

## Usage

### 1. Load fixtures in Streamlit demo

```python
import json
with open("demo/fixtures/sample_profile.json") as f:
    profile = json.load(f)

# Inject into Streamlit session_state for instant display
st.session_state.workflow_result = {
    "profile": profile,
    "learning_plan": {...},
    "resources": [...],
    "trace": [...],
}
```

### 2. Validate fixtures

```bash
python -c "
import json
for f in ['sample_profile.json', 'learning_trace.json', 'generated_resources.json']:
    with open(f'demo/fixtures/{f}') as fp:
        data = json.load(fp)
    print(f'✅ {f}: valid JSON, {len(str(data))} chars')
"
```

### 3. Competition demo flow

1. Launch A3 with mock provider
2. Load `sample_profile.json` → shows full 6-dimension profile
3. Load `learning_trace.json` → shows timeline with all agents
4. Load `generated_resources.json` → shows 6 resource cards

## Note

These fixtures are **frozen** — they represent a specific, tested demo state.
Do not modify without updating the demo script.
