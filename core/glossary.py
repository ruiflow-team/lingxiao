"""凌霄翻译 Glossary 保护词机制。

把不该被翻译的专名（如 LingXiao / RUIFLOW / Wav2Lip）在送入翻译引擎前
替换成 placeholder（__GL00__ / __GL01__ ...），译后还原。

避免 NLLB 把 LingXiao 译成「林晓」、把 凌霄 译成「Ling Ling」。
"""
from __future__ import annotations
import re
from typing import Dict, List, Tuple


# 凌霄默认 glossary：(原文不分大小写, 还原后写法)
DEFAULT_GLOSSARY: List[Tuple[str, str]] = [
    ("LingXiao", "凌霄"),
    ("Lingxiao", "凌霄"),
    ("lingxiao", "凌霄"),
    ("凌霄", "凌霄"),       # 自我保护：避免反向被译错
    ("RUIFLOW", "RUIFLOW"),
    ("Ruiflow", "RUIFLOW"),
    ("瑞流", "RUIFLOW"),
    ("Wav2Lip", "Wav2Lip"),
    ("NLLB", "NLLB"),
    ("Whisper", "Whisper"),
    ("Edge TTS", "Edge TTS"),
]


class GlossaryProtector:
    """翻译前替换专名为 placeholder，翻译后还原。"""

    def __init__(self, entries: List[Tuple[str, str]] | None = None):
        self.entries = entries or DEFAULT_GLOSSARY

    def protect(self, text: str) -> Tuple[str, Dict[str, str]]:
        """text → (replaced_text, restore_map)；map 是 {placeholder: target}"""
        if not text:
            return text, {}
        result = text
        restore: Dict[str, str] = {}
        for i, (src, tgt) in enumerate(self.entries):
            placeholder = f"__GL{i:02d}__"
            # 大小写不敏感、词边界
            pattern = re.compile(re.escape(src), re.IGNORECASE)
            if pattern.search(result):
                result = pattern.sub(placeholder, result)
                restore[placeholder] = tgt
        return result, restore

    def restore(self, text: str, restore_map: Dict[str, str]) -> str:
        """把 placeholder 换回 target；同时把 NLLB 可能产生的 __ gl 00 __ 变体也吃掉。"""
        if not text:
            return text
        result = text
        for placeholder, tgt in restore_map.items():
            # 直接 placeholder
            result = result.replace(placeholder, tgt)
            # NLLB 可能加空格/小写：__gl00__, __ gl 00 __
            idx = placeholder[4:6]  # "00"
            for variant in (
                f"__gl{idx}__",
                f"__ GL{idx} __",
                f"__ gl {idx} __",
                f"GL{idx}",
                f"gl{idx}",
            ):
                result = result.replace(variant, tgt)
        return result


# Singleton
_default = GlossaryProtector()


def protect(text: str) -> Tuple[str, Dict[str, str]]:
    return _default.protect(text)


def restore(text: str, restore_map: Dict[str, str]) -> str:
    return _default.restore(text, restore_map)
