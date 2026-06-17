"""
MiniMax 翻译模块
"""
import re
import logging
from typing import Union, Optional
from loguru import logger

from .config import MINIMAX_API_KEY, MINIMAX_API_BASE

# SRT 时间轴正则
SRT_TIME_PATTERN = re.compile(
    r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})"
)


class MiniMaxTranslator:
    """
    MiniMax 翻译 API 封装
    
    支持:
    - 文本翻译
    - SRT 字幕翻译（保持时间轴）
    
    使用方式:
        translator = MiniMaxTranslator(api_key="your_key")
        result = translator.translate("Hello world", target_lang="zh")
        result = translator.translate_subtitle(srt_content, target_lang="zh")
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or MINIMAX_API_KEY
        self.api_base = MINIMAX_API_BASE
        
        if not self.api_key:
            logger.warning("MiniMax API key not set, translation will use fallback")
    
    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "zh",
    ) -> str:
        """
        翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言，auto 自动检测
            target_lang: 目标语言
        
        Returns:
            翻译后的文本
        """
        if not text.strip():
            return ""
        
        if not self.api_key:
            # 使用免费翻译器
            try:
                from core.translator_free import get_translator
                free_translator = get_translator()
                return free_translator.translate(text, source_lang, target_lang)
            except Exception:
                logger.warning("Free translator unavailable, returning original text")
                return text
        
        import requests
        
        try:
            response = requests.post(
                f"{self.api_base}/text/chatcompletion_v2",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "MiniMax-Text-01",
                    "messages": [
                        {
                            "role": "user",
                            "content": f"Translate the following text to {'Chinese' if target_lang == 'zh' else target_lang}:\n\n{text}"
                        }
                    ],
                    "max_tokens": 4096,
                },
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            logger.error(f"MiniMax translation error: {e}")
            return text  # 失败时返回原文
    
    def translate_subtitle(
        self,
        srt_content: str,
        source_lang: str = "auto",
        target_lang: str = "zh",
    ) -> str:
        """
        翻译 SRT 字幕，保持时间轴格式
        
        Args:
            srt_content: SRT 格式的字幕内容
            source_lang: 源语言
            target_lang: 目标语言
        
        Returns:
            翻译后的 SRT 内容
        """
        if not srt_content.strip():
            return ""
        
        lines = srt_content.split("\n")
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # 检测时间轴行
            time_match = SRT_TIME_PATTERN.match(line)
            if time_match:
                # 保留时间轴
                result_lines.append(line)
                i += 1
                
                # 下一行是字幕文本
                if i < len(lines):
                    subtitle_text = lines[i].strip()
                    if subtitle_text:
                        # 翻译文本
                        translated = self._translate_text(subtitle_text, source_lang, target_lang)
                        result_lines.append(translated)
                    i += 1
            else:
                # 其他行（序号、空行等）直接保留
                result_lines.append(line)
                i += 1
        
        return "\n".join(result_lines)
    
    def _translate_text(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "zh",
    ) -> str:
        """
        翻译单条字幕文本（内部方法）
        
        处理合并多行的情况
        """
        # 合并多行字幕（同一时间框内的换行）
        lines = text.split("\n")
        all_text = " ".join(lines)
        
        # 调用翻译API
        translated = self.translate(all_text, source_lang, target_lang)
        
        return translated


class MiniMaxTranslatorBatch:
    """
    批量翻译优化版 - 一次翻译多条字幕减少API调用
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or MINIMAX_API_KEY
        self.api_base = MINIMAX_API_BASE
    
    def translate_subtitle(
        self,
        srt_content: str,
        source_lang: str = "auto",
        target_lang: str = "zh",
        batch_size: int = 10,
    ) -> str:
        """
        批量翻译 SRT - 更节省 token
        
        策略：将多条字幕合并成一段文本翻译，再拆分
        """
        if not srt_content.strip():
            return ""
        
        # 提取所有字幕块
        blocks = self._parse_srt(srt_content)
        
        # 批量翻译
        translated_blocks = []
        for i in range(0, len(blocks), batch_size):
            batch = blocks[i:i + batch_size]
            translated_batch = self._translate_batch(batch, source_lang, target_lang)
            translated_blocks.extend(translated_batch)
        
        # 重新组装 SRT
        return self._rebuild_srt(translated_blocks)
    
    def _parse_srt(self, srt_content: str) -> list:
        """解析 SRT 为字幕块列表"""
        blocks = []
        current_block = {"index": "", "time": "", "text": ""}
        
        for line in srt_content.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            time_match = SRT_TIME_PATTERN.match(line)
            if time_match:
                if current_block["text"]:
                    blocks.append(current_block)
                current_block = {"index": "", "time": line, "text": ""}
            elif line.isdigit():
                current_block["index"] = line
            else:
                current_block["text"] += (" " + line if current_block["text"] else line)
        
        if current_block["text"]:
            blocks.append(current_block)
        
        return blocks
    
    def _translate_batch(self, blocks: list, source_lang: str, target_lang: str) -> list:
        """批量翻译一组字幕块"""
        if not self.api_key:
            return [{"text": b["text"]} for b in blocks]
        
        # 构造批量翻译的提示
        texts = [b["text"] for b in blocks]
        prompt = "Translate each line to Chinese. Keep the line breaks.\n\n" + "\n".join(
            f"[{i+1}] {t}" for i, t in enumerate(texts)
        )
        
        import requests
        try:
            response = requests.post(
                f"{self.api_base}/text/chatcompletion_v2",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "MiniMax-Text-01",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            translated_text = data["choices"][0]["message"]["content"].strip()
            
            # 解析翻译结果
            translated = []
            for line in translated_text.split("\n"):
                line = line.strip()
                if line.startswith(f"[") and "]" in line:
                    # 去掉 [1] 前缀
                    line = line.split("]", 1)[1].strip()
                translated.append(line)
            
            # 确保数量匹配
            while len(translated) < len(texts):
                translated.append(texts[len(translated)])
            
            return [{"text": t} for t in translated[:len(blocks)]]
            
        except Exception as e:
            logger.error(f"Batch translation error: {e}")
            return [{"text": b["text"]} for b in blocks]
    
    def _rebuild_srt(self, blocks: list) -> str:
        """重新组装 SRT"""
        lines = []
        for i, block in enumerate(blocks, 1):
            lines.append(str(i))
            lines.append(block["time"] if "time" in block else "")
            lines.append(block["text"])
            lines.append("")
        return "\n".join(lines)


def parse_srt(srt_content: str) -> list:
    """
    解析 SRT 字幕内容
    
    Args:
        srt_content: SRT 文件内容
    
    Returns:
        [{"index": int, "time": str, "text": str}, ...]
    """
    import re
    
    SRT_TIME_PATTERN = re.compile(
        r"(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})"
    )
    
    blocks = []
    current_index = None
    current_time = None
    current_text = []
    
    for line in srt_content.strip().split("\n"):
        line = line.strip()
        
        if not line:
            # 空行，分隔符
            if current_index is not None:
                blocks.append({
                    "index": current_index,
                    "time": current_time,
                    "text": "\n".join(current_text).strip(),
                })
            current_index = None
            current_time = None
            current_text = []
            continue
        
        # 检查是否是序号
        if line.isdigit() and current_index is None:
            current_index = int(line)
            continue
        
        # 检查是否是时间轴
        time_match = SRT_TIME_PATTERN.match(line)
        if time_match and current_index is not None:
            current_time = line
            continue
        
        # 否则是文本
        if current_index is not None:
            current_text.append(line)
    
    # 最后一个 block
    if current_index is not None:
        blocks.append({
            "index": current_index,
            "time": current_time,
            "text": "\n".join(current_text).strip(),
        })
    
    return blocks


def create_srt(segments: list) -> str:
    """
    从片段列表创建 SRT 字幕
    
    Args:
        segments: [{"text": str, "start": float, "end": float}, ...]
                  或 [{"index": int, "time": str, "text": str}, ...]
    
    Returns:
        SRT 格式字符串
    """
    lines = []
    
    for i, seg in enumerate(segments, 1):
        # 如果有 start/end 时间（秒），转换格式
        if "start" in seg and "end" in seg:
            start = _format_timestamp(seg["start"])
            end = _format_timestamp(seg["end"])
            time_str = f"{start} --> {end}"
        elif "time" in seg:
            time_str = seg["time"]
        else:
            time_str = "00:00:00,000 --> 00:00:00,000"
        
        lines.append(str(i))
        lines.append(time_str)
        lines.append(seg["text"])
        lines.append("")
    
    return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
    """将秒数格式化为 SRT 时间戳"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"