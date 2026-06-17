"""LingXiao professional job contracts.

Single source of truth for desktop / CLI / web / Harness execution.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import hashlib
import json
import time
import uuid

JobStatus = Literal["created", "running", "degraded", "failed", "completed"]
StepStatus = Literal["pending", "running", "skipped", "degraded", "failed", "completed"]
ArtifactKind = Literal["input", "audio", "subtitle", "translation", "tts", "video", "report", "log", "other"]


@dataclass
class LingXiaoArtifact:
    kind: ArtifactKind
    path: str
    label: str = ""
    sha256: Optional[str] = None
    bytes: Optional[int] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_path(cls, kind: ArtifactKind, path: str | Path, label: str = "", **meta: Any) -> "LingXiaoArtifact":
        p = Path(path)
        digest = None
        size = None
        if p.exists() and p.is_file():
            size = p.stat().st_size
            h = hashlib.sha256()
            with p.open("rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            digest = h.hexdigest()
        return cls(kind=kind, path=str(p), label=label, sha256=digest, bytes=size, meta=dict(meta))


@dataclass
class LingXiaoStep:
    name: str
    status: StepStatus = "pending"
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    message: str = ""
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def start(self, message: str = "") -> None:
        self.status = "running"
        self.started_at = time.time()
        self.message = message

    def finish(self, status: StepStatus = "completed", message: str = "", error: Optional[str] = None, **meta: Any) -> None:
        self.status = status
        self.finished_at = time.time()
        if message:
            self.message = message
        self.error = error
        self.meta.update(meta)


@dataclass
class LingXiaoJob:
    input_video: str
    target_lang: str = "zh"
    source_lang: str = "auto"
    mode: Literal["subtitle", "subtitle+dubbing", "dubbing", "lipsync"] = "subtitle+dubbing"
    enable_lipsync: bool = False
    job_id: str = field(default_factory=lambda: "lx_" + uuid.uuid4().hex[:12])
    status: JobStatus = "created"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    output_dir: str = "output/jobs"
    steps: List[LingXiaoStep] = field(default_factory=list)
    artifacts: List[LingXiaoArtifact] = field(default_factory=list)
    quality: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def step(self, name: str) -> LingXiaoStep:
        s = LingXiaoStep(name=name)
        self.steps.append(s)
        self.touch()
        return s

    def add_artifact(self, kind: ArtifactKind, path: str | Path, label: str = "", **meta: Any) -> LingXiaoArtifact:
        art = LingXiaoArtifact.from_path(kind, path, label=label, **meta)
        self.artifacts.append(art)
        self.touch()
        return art

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        if self.status not in ("failed",):
            self.status = "degraded"
        self.touch()

    def fail(self, message: str) -> None:
        self.errors.append(message)
        self.status = "failed"
        self.touch()

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def write_report(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return p
