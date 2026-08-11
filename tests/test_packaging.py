"""Packaging smoke tests.

These verify artifacts produced by `python -m build` — run them against a
dist directory (e.g. `RC_TUI_DIST=/tmp/dist pytest tests/test_packaging.py`).
Without RC_TUI_DIST set, they are skipped.
"""

import os
import tarfile
import zipfile


def _dist_dir():
    return os.environ.get("RC_TUI_DIST")


def test_wheel_contains_extension_and_python_package():
    dist = _dist_dir()
    if not dist:
        return
    wheels = [f for f in sorted(os.listdir(dist)) if f.endswith(".whl")]
    assert wheels, f"no wheels in {dist}"
    with zipfile.ZipFile(os.path.join(dist, wheels[-1])) as zf:
        names = zf.namelist()
        so = [n for n in names if "_rctui_core" in n and n.endswith(".so")]
        assert so, f"wheel missing extension: {names}"
        assert "rc_tui/__init__.py" in names
        assert "rc_tui/py.typed" in names


def test_sdist_contains_sources_only():
    dist = _dist_dir()
    if not dist:
        return
    sdists = [f for f in sorted(os.listdir(dist)) if f.endswith(".tar.gz")]
    assert sdists, f"no sdists in {dist}"
    with tarfile.open(os.path.join(dist, sdists[-1])) as tf:
        names = tf.getnames()
        assert any("src/cpp/Buffer.cpp" in n for n in names)
        assert any(n.endswith("pyproject.toml") for n in names)
        assert not any(".venv" in n for n in names), "venv leaked into sdist"
        assert not any(n.endswith(".so") for n in names), "binary leaked into sdist"
        assert not any("__pycache__" in n for n in names)
