"""LingXiao NLLB-200 本地翻译适配器（¥0、200 语言、CPU 推理可用）。

模型：facebook/nllb-200-distilled-600M（modelscope/HF 同名）
位置：models/nllb-200-distilled-600M/
依赖：transformers, sentencepiece, torch（已在 .venv-lingxiao）
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Optional


# 凌霄 CLI 的语言代码 → NLLB 200 语言代码（FLORES-200）
LANG_MAP: Dict[str, str] = {
    "zh": "zho_Hans",
    "zh-cn": "zho_Hans",
    "zh_cn": "zho_Hans",
    "zh-tw": "zho_Hant",
    "en": "eng_Latn",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "fr": "fra_Latn",
    "de": "deu_Latn",
    "es": "spa_Latn",
    "ru": "rus_Cyrl",
    "ar": "arb_Arab",
    "auto": "eng_Latn",  # NLLB 不能 auto 检测，默认按 en；上层应已检测好
}


def _norm(lang: str) -> str:
    if not lang:
        return "eng_Latn"
    s = lang.lower().replace("_", "-")
    if s in LANG_MAP:
        return LANG_MAP[s]
    return LANG_MAP.get(s.split("-")[0], "eng_Latn")


class NLLBTranslator:
    """NLLB-200-distilled-600M 本地翻译器。线程安全（lazy load + lock）。"""

    _model_lock = threading.Lock()

    def __init__(self, model_dir: str, device: Optional[str] = None):
        self.model_dir = Path(model_dir)
        if not self.model_dir.exists():
            raise FileNotFoundError(f"NLLB model dir missing: {self.model_dir}")
        self.device = device or "cpu"  # CPU 也够用 0.3-0.9s/句；GPU 可后续打开
        self._tok = None
        self._model = None

    def _ensure_loaded(self) -> None:
        if self._tok is not None and self._model is not None:
            return
        with self._model_lock:
            if self._tok is not None and self._model is not None:
                return
            from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
            self._tok = AutoTokenizer.from_pretrained(str(self.model_dir))
            self._model = AutoModelForSeq2SeqLM.from_pretrained(str(self.model_dir))
            self._model.eval()

    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "zh") -> str:
        text = (text or "").strip()
        if not text:
            return ""
        self._ensure_loaded()

        src_code = _norm(source_lang)
        tgt_code = _norm(target_lang)
        if src_code == tgt_code:
            return text

        # 设置源语言
        try:
            self._tok.src_lang = src_code
        except Exception:
            pass

        inputs = self._tok(text, return_tensors="pt", truncation=True, max_length=512)
        try:
            forced = self._tok.convert_tokens_to_ids(tgt_code)
        except Exception:
            forced = None

        gen_kwargs = {"max_new_tokens": 256, "num_beams": 1}
        if forced is not None:
            gen_kwargs["forced_bos_token_id"] = forced

        import torch
        with torch.inference_mode():
            out = self._model.generate(**inputs, **gen_kwargs)
        return self._tok.batch_decode(out, skip_special_tokens=True)[0].strip()
