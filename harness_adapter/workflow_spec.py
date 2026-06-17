"""Harness/FOS adapter contract for LingXiao localization lane."""
from __future__ import annotations

TASK_TYPES = {
    "lingxiao_subtitle_translate": {"mode": "subtitle", "gate": "subtitle_quality"},
    "lingxiao_dubbing_export": {"mode": "subtitle+dubbing", "gate": "dubbing_quality"},
    "lingxiao_lipsync_export": {"mode": "lipsync", "gate": "lipsync_quality"},
    "lingxiao_quality_check": {"mode": "quality", "gate": "artifact_ledger"},
    "lingxiao_batch_localization": {"mode": "batch", "gate": "batch_quality"},
}

GATES = [
    "input_gate",
    "asr_gate",
    "translation_gate",
    "tts_gate",
    "mux_gate",
    "quality_gate",
    "artifact_ledger_gate",
]


def build_task(input_video: str, target_lang: str = "zh", mode: str = "subtitle+dubbing") -> dict:
    return {
        "task_type": "lingxiao_dubbing_export" if mode != "subtitle" else "lingxiao_subtitle_translate",
        "payload": {
            "input_video": input_video,
            "target_lang": target_lang,
            "mode": mode,
        },
        "required_gates": GATES,
    }
