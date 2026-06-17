"""LingXiao environment doctor for professional desktop releases."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from importlib.util import find_spec
from pathlib import Path
from shutil import which
from typing import Dict, List
import os
import subprocess


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    status: str
    fix: str = ""
    required: bool = True


@dataclass
class DoctorReport:
    ok: bool
    degraded: bool
    checks: List[DoctorCheck] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    def markdown(self) -> str:
        lines = ["# LingXiao Doctor Report", "", f"Overall: {'OK' if self.ok and not self.degraded else ('DEGRADED' if self.ok and self.degraded else 'FAILED')}", ""]
        for c in self.checks:
            icon = "✅" if c.ok else ("⚠️" if not c.required else "❌")
            lines.append(f"- {icon} **{c.name}**: {c.status}" + (f"；修复：{c.fix}" if c.fix else ""))
        return "\n".join(lines) + "\n"


def _probe_cmd(cmd: str) -> bool:
    return which(cmd) is not None


def _probe_ffmpeg() -> str:
    try:
        out = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=8)
        return out.stdout.splitlines()[0] if out.returncode == 0 and out.stdout else "ffmpeg callable"
    except Exception as e:
        return str(e)


def run_doctor(project_root: str | Path = ".") -> DoctorReport:
    root = Path(project_root).resolve()
    checks: List[DoctorCheck] = []

    checks.append(DoctorCheck("project_root", root.exists(), str(root)))
    checks.append(DoctorCheck("output_writable", os.access(root / "output", os.W_OK) if (root / "output").exists() else os.access(root, os.W_OK), str(root / "output"), "检查目录权限"))

    ffmpeg_ok = _probe_cmd("ffmpeg")
    checks.append(DoctorCheck("ffmpeg", ffmpeg_ok, _probe_ffmpeg() if ffmpeg_ok else "not found", "brew install ffmpeg"))
    ffprobe_ok = _probe_cmd("ffprobe")
    checks.append(DoctorCheck("ffprobe", ffprobe_ok, "found" if ffprobe_ok else "not found", "brew install ffmpeg"))

    # v0.1 is local-first and must boot in degraded mode without heavy AI deps.
    # Required = enough to run doctor / ffmpeg gates / sidecar-SRT workflow.
    required_modules = {
        "requests": "pip install requests",
        "numpy": "pip install numpy",
    }
    optional_modules = {
        "loguru": "pip install loguru",
        "soundfile": "pip install soundfile",
        "whisper": "pip install openai-whisper",
        "edge_tts": "pip install edge-tts",
        "PyQt5": "pip install PyQt5",
        "fastapi": "pip install fastapi uvicorn",
        "librosa": "pip install librosa",
        "deep_translator": "pip install deep-translator",
    }

    for mod, fix in required_modules.items():
        ok = find_spec(mod) is not None
        checks.append(DoctorCheck(f"python:{mod}", ok, "available" if ok else "missing", fix, required=True))
    for mod, fix in optional_modules.items():
        ok = find_spec(mod) is not None
        checks.append(DoctorCheck(f"python:{mod}", ok, "available" if ok else "missing / feature degraded", fix, required=False))

    models = root / "models"
    checks.append(DoctorCheck("models_dir", models.exists(), str(models), "运行模型下载或降级为在线/字幕模式", required=False))
    # doctor v2: 接受多个常见路径 + 文件大小 ≥ 50MB
    wav2lip_candidates = [
        models / "wav2lip" / "wav2lip_gan.pth",
        models / "wav2lip" / "checkpoints" / "wav2lip_gan.pth",
        models / "wav2lip" / "wav2lip.pth",
        models / "wav2lip" / "checkpoints" / "wav2lip.pth",
    ]
    wav2lip_found = next((p for p in wav2lip_candidates if p.exists() and p.stat().st_size >= 50 * 1024 * 1024), None)
    checks.append(DoctorCheck(
        "model:wav2lip",
        wav2lip_found is not None,
        str(wav2lip_found) if wav2lip_found else "missing / lipsync disabled",
        "下载 Wav2Lip 模型或检查路径 models/wav2lip/(checkpoints/)wav2lip(_gan).pth",
        required=False,
    ))

    required_failed = any((not c.ok and c.required) for c in checks)
    optional_failed = any((not c.ok and not c.required) for c in checks)
    return DoctorReport(ok=not required_failed, degraded=(optional_failed and not required_failed), checks=checks)


if __name__ == "__main__":
    print(run_doctor(Path(__file__).resolve().parents[1]).markdown())
