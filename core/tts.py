"""
TTS 语音合成模块 - 使用 Edge TTS (免费中文支持好)
"""
import subprocess
import logging
import asyncio
import re
from pathlib import Path
from typing import Union, Optional
from loguru import logger

from core.config import TEMP_DIR


class EdgeTTS:
    """
    Edge TTS 封装 - 微软必应语音合成（免费、中文支持好）
    
    使用方式:
        tts = EdgeTTS()
        tts.synthesize("你好世界", "output.wav", voice="zh-CN-XiaoxiaoNeural")
    """
    
    # 中文常用音色
    VOICE_MAP = {
        "female_xiaoxiao": "zh-CN-XiaoxiaoNeural",      # 女声，通用
        "female_yunyang": "zh-CN-YunyangNeural",        # 女声，新闻
        "male_yunxi": "zh-CN-YunxiNeural",              # 男声
        "male_yunye": "zh-CN-YunyeNeural",              # 男声，正式
    }
    
    # 英文音色
    VOICE_MAP_EN = {
        "female_samantha": "en-US-SaraNeural",
        "male_david": "en-US-DavisNeural",
    }
    
    def __init__(self, voice: str = "female_xiaoxiao"):
        self.voice = self._resolve_voice(voice)
        self._ensure_dependency()
    
    def _ensure_dependency(self):
        """确保 edge-tts 已安装"""
        try:
            import edge_tts
            self.edge_tts = edge_tts
        except ImportError:
            subprocess.run([__import__('sys').executable, "-m", "pip", "install", "edge-tts", "-q"], check=True)
            import edge_tts
            self.edge_tts = edge_tts
    
    def _resolve_voice(self, voice: str) -> str:
        """解析音色名称"""
        if voice in self.VOICE_MAP:
            return self.VOICE_MAP[voice]
        if voice in self.VOICE_MAP_EN:
            return self.VOICE_MAP_EN[voice]
        # 直接是 voice ID
        if "-" in voice:
            return voice
        # 默认女声
        return "zh-CN-XiaoxiaoNeural"
    
    def synthesize(
        self,
        text: str,
        output_path: Union[str, Path],
        voice: Optional[str] = None,
        rate: str = "+0%",  # 语速: -50% 到 +100%
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ) -> str:
        """
        文字转语音
        
        Args:
            text: 待合成文本
            output_path: 输出音频路径
            voice: 音色名称 (female_xiaoxiao, male_yunxi, 等)
            rate: 语速调整 (如 "+10%", "-20%")
            volume: 音量调整
            pitch: 音调调整
        
        Returns:
            生成的音频文件路径
        """
        import edge_tts
        
        voice = voice or self.voice
        resolved_voice = self._resolve_voice(voice)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Synthesizing: {text[:50]}... -> {output_path}")
        
        async def _run():
            communicate = edge_tts.Communicate(
                text,
                resolved_voice,
                rate=rate,
                volume=volume,
                pitch=pitch,
            )
            await communicate.save(str(output_path))
        
        asyncio.run(_run())
        
        if output_path.exists():
            logger.info(f"TTS output: {output_path}")
            return str(output_path)
        else:
            raise RuntimeError("TTS generation failed")
    
    def synthesize_from_subtitle(
        self,
        srt_content: str,
        output_path: Union[str, Path],
        voice: Optional[str] = None,
        combine_sentences: bool = True,
    ) -> str:
        """
        从 SRT 字幕生成语音
        
        Args:
            srt_content: SRT 格式字幕
            output_path: 输出音频路径
            voice: 音色
            combine_sentences: 是否合并短句（让语音更自然）
        
        Returns:
            生成的音频文件路径
        """
        import edge_tts
        
        voice = voice or self.voice
        resolved_voice = self._resolve_voice(voice)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 提取字幕文本
        text_lines = self._extract_subtitle_text(srt_content)
        
        if not text_lines:
            raise ValueError("No text found in subtitle")
        
        if combine_sentences:
            # 合并成连贯文本，让 TTS 更自然
            full_text = " ".join(text_lines)
        else:
            full_text = "\n".join(text_lines)
        
        logger.info(f"Synthesizing {len(full_text)} chars from subtitle...")
        
        async def _run():
            communicate = edge_tts.Communicate(
                full_text,
                resolved_voice,
                rate="+0%",
            )
            await communicate.save(str(output_path))
        
        asyncio.run(_run())
        
        if output_path.exists():
            logger.info(f"Subtitle TTS output: {output_path}")
            return str(output_path)
        else:
            raise RuntimeError("Subtitle TTS generation failed")
    
    def _extract_subtitle_text(self, srt_content: str) -> list:
        """从 SRT 提取纯文本"""
        text_lines = []
        for line in srt_content.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 跳过序号
            if line.isdigit():
                continue
            # 跳过时间轴
            if "-->" in line:
                continue
            # 跳过 SRT 头部标记
            if line.startswith("WEBVTT"):
                continue
            text_lines.append(line)
        return text_lines
    
    @staticmethod
    def list_voices(language: str = "zh") -> list:
        """列出可用音色"""
        import edge_tts
        
        async def _list():
            voices = await edge_tts.list_voices()
            return [
                v for v in voices
                if v["Locale"].startswith(language)
            ]
        
        return asyncio.run(_list())


# 全局默认实例
_default_tts = None

def get_tts_client() -> EdgeTTS:
    """获取默认 TTS 客户端"""
    global _default_tts
    if _default_tts is None:
        _default_tts = EdgeTTS()
    return _default_tts


class VITSClient(EdgeTTS):
    """
    VITS 语音合成封装 - 继承 EdgeTTS 接口
    
    如果 VITS 模型可用则使用 VITS，否则降级到 EdgeTTS
    """
    
    def __init__(self, model_path: Optional[Path] = None, voice: str = "female"):
        super().__init__(voice=voice)
        self.model_path = model_path
        self.vits_available = False
        
        # VITS 暂不可用，保持 EdgeTTS 作为后备
        logger.info("VITS not available, using EdgeTTS")