#!/usr/bin/env python3
"""LingXiao professional CLI."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from core.doctor import run_doctor
from core.pro_pipeline import ProfessionalTranslationPipeline


def main() -> int:
    parser = argparse.ArgumentParser(prog="lingxiao", description="凌霄专业影视翻译桌面端核心 CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="检查本机依赖/模型/权限")
    d.add_argument("--json", action="store_true")

    p = sub.add_parser("process", help="处理一个视频")
    p.add_argument("input_video")
    p.add_argument("--target-lang", default="zh")
    p.add_argument("--source-lang", default="auto")
    p.add_argument("--mode", default="subtitle+dubbing", choices=["subtitle", "subtitle+dubbing", "dubbing", "lipsync"])
    p.add_argument("--output-dir", default=None)
    p.add_argument("--voice-id", default="zh-CN-XiaoxiaoNeural")
    p.add_argument("--asr-model", default="base")
    p.add_argument("--device", default="auto")
    p.add_argument("--lipsync", action="store_true")

    args = parser.parse_args()
    root = Path(__file__).resolve().parent

    if args.cmd == "doctor":
        report = run_doctor(root)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(report.markdown())
        return 0 if report.ok else 2

    if args.cmd == "process":
        def progress(p: int, msg: str) -> None:
            print(f"[{p:3d}%] {msg}", flush=True)

        pipe = ProfessionalTranslationPipeline(root, asr_model=args.asr_model, device=args.device)
        job = asyncio.run(pipe.process(
            args.input_video,
            target_lang=args.target_lang,
            source_lang=args.source_lang,
            mode=args.mode,
            output_dir=args.output_dir,
            voice_id=args.voice_id,
            enable_lipsync=args.lipsync or args.mode == "lipsync",
            progress=progress,
        ))
        print(json.dumps({"job_id": job.job_id, "status": job.status, "output_dir": job.output_dir, "errors": job.errors, "warnings": job.warnings}, ensure_ascii=False, indent=2))
        return 0 if job.status in ("completed", "degraded") else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
