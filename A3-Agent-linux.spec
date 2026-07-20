# -*- mode: python ; coding: utf-8 -*-
# A3-Agent v1.0.0 — Linux PyInstaller Spec
# Forward-slash paths for Linux/macOS compatibility.
# Build: pyinstaller A3-Agent-linux.spec
from PyInstaller.utils.hooks import collect_all

datas = [('app.py', '.'), ('src', 'src'), ('web', 'web'), ('utils', 'utils'), ('desktop', 'desktop'), ('knowledge_base', 'knowledge_base'), ('demo/fixtures', 'demo/fixtures'), ('.streamlit/config.toml', '.streamlit'), ('.env.example', '.'), ('LICENSE', '.')]
binaries = []
hiddenimports = ['desktop.config', 'fastapi', 'uvicorn', 'streamlit', 'veritas', 'veritas.llm', 'veritas.llm.factory', 'veritas.llm.provider', 'veritas.llm.mock_provider', 'veritas.llm.deepseek_provider', 'veritas.llm.openai_provider', 'veritas.llm.xunfei_provider', 'veritas.llm.rule_provider', 'veritas.memory', 'veritas.runtime', 'keyring', 'keyring.backend', 'keyring.backends', 'keyring.errors', 'keyring.credentials', 'SecretStorage', 'jeepney', 'jaraco.classes', 'jaraco.functools']
tmp_ret = collect_all('fastapi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('uvicorn')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('streamlit')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('veritas')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['desktop/launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['desktop/hooks/runtime_hook.py'],
    excludes=['pyarrow', 'scipy', 'pytest', 'matplotlib', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='A3-Agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='A3-Agent',
)
