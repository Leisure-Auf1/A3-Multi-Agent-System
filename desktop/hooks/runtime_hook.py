"""
PyInstaller runtime hook for A3-Agent v1.0.0.

Ensures the bundle root (sys._MEIPASS) is on sys.path so that
application source directories (src/, web/) can be imported
in the frozen environment.

Reference in build command:
    --runtime-hook desktop/hooks/runtime_hook.py
"""

import os
import sys

_bundle_root = getattr(sys, "_MEIPASS", None)
if _bundle_root and _bundle_root not in sys.path:
    sys.path.insert(0, _bundle_root)

_parent = os.path.dirname(_bundle_root)
if _parent and _parent not in sys.path:
    sys.path.insert(0, _parent)
