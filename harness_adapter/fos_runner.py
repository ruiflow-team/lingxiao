"""Minimal FOS runner entry for LingXiao.

This is intentionally local-first: Harness passes JSON payload, runner returns job ledger path.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pro_pipeline import ProfessionalTranslationPipeline


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True, help="JSON payload or path to JSON file")
    args = parser.parse_args()

    raw = Path(args.task).read_text(encoding="utf-8") if Path(args.task).exists() else args.task
    payload = json.loads(raw)
    root = ROOT
    pipe = ProfessionalTranslationPipeline(root)
    job = asyncio.run(pipe.process(
        payload["input_video"],
        target_lang=payload.get("target_lang", "zh"),
        source_lang=payload.get("source_lang", "auto"),
        mode=payload.get("mode", "subtitle+dubbing"),
        output_dir=payload.get("output_dir"),
        enable_lipsync=payload.get("enable_lipsync", False),
    ))
    print(json.dumps({"status": job.status, "job_id": job.job_id, "ledger": str(Path(job.output_dir) / "job.json")}, ensure_ascii=False))
    return 0 if job.status in ("completed", "degraded") else 1


if __name__ == "__main__":
    raise SystemExit(main())
