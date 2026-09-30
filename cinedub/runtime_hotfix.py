from __future__ import annotations

import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path

from .jobs import JobManager


def _av_major() -> tuple[str, int]:
    try:
        version = importlib.metadata.version("av")
        major = int(str(version).split(".", 1)[0])
        return version, major
    except Exception:
        return "missing", 0


def _repair_pyav(ctx, job_id: str, manager: JobManager) -> None:
    version, major = _av_major()
    if major >= 11:
        return
    manager._update(ctx, job_id, progress=2.0, message=f"ซ่อม Speech Runtime • PyAV {version} → av>=11")
    ctx.db.log("WARNING", "RUNTIME", f"PyAV {version} incompatible; upgrading to av>=11")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0  # type: ignore[attr-defined]
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "av>=11", "faster-whisper>=1.1.0"]
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=flags,
    )
    for line in (proc.stdout or "").splitlines()[-80:]:
        if line.strip():
            ctx.db.log("INFO", "RUNTIME", line[:1200])
    if proc.returncode != 0:
        raise RuntimeError(f"ซ่อม Speech Runtime ไม่สำเร็จ (pip {proc.returncode})")
    version, major = _av_major()
    if major < 11:
        raise RuntimeError(f"PyAV ยังไม่เข้ากันหลังซ่อม: {version}")
    manager._update(ctx, job_id, progress=3.0, message=f"Speech Runtime พร้อม • PyAV {version}")


def _patch_ui_refresh() -> None:
    """Keep realtime polling from replacing controls while the user edits them."""
    app_js = Path(__file__).resolve().parents[1] / "web" / "app.js"
    if not app_js.exists():
        return
    try:
        text = app_js.read_text(encoding="utf-8")
        marker = "/* cinedub-v0.2.3-form-safe-refresh */"
        if marker in text:
            return
        old = "setInterval(()=>refresh(false),1500); setInterval(fetchLogs,900);"
        new = """/* cinedub-v0.2.3-form-safe-refresh */
  const _cinedubEditing=()=>{const e=document.activeElement;return !!(e && ['SELECT','INPUT','TEXTAREA'].includes(e.tagName));};
  setInterval(()=>{if(!_cinedubEditing())refresh(false)},1500); setInterval(fetchLogs,900);"""
        if old in text:
            app_js.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    except Exception:
        pass


_patch_ui_refresh()

if not getattr(JobManager, "_cinedub_v023_patched", False):
    _original_auto_localize = JobManager._job_auto_localize

    def _auto_localize_v023(self: JobManager, ctx, job_id: str, payload):
        _repair_pyav(ctx, job_id, self)
        return _original_auto_localize(self, ctx, job_id, payload)

    JobManager._job_auto_localize = _auto_localize_v023  # type: ignore[assignment]
    JobManager._cinedub_v023_patched = True  # type: ignore[attr-defined]
