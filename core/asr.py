"""
Whisper ASR 模块 - 使用 openai-whisper (Python版)
"""
import os
import logging
from pathlib import Path
from typing import Union, Optional
from loguru import logger

from core.config import TEMP_DIR

# 设置 whisper 使用的 ffmpeg 路径
import imageio_ffmpeg
os.environ["FFMPEG_BINARY"] = imageio_ffmpeg.get_ffmpeg_exe()


class WhisperASR:
    """
    Whisper ASR 封装 - Python 版
    
    使用 openai-whisper 库，支持 CPU/GPU 推理
    
    使用方式:
        asr = WhisperASR(model_name="base")
        result = asr.transcribe("audio.wav", "output.srt", language="en")
    """
    
    # 模型名称对应文件大小
    MODEL_SIZES = {
        "tiny": "~39 MB",
        "base": "~139 MB",
        "small": "~488 MB",
        "medium": "~1.5 GB",
        "large": "~2.9 GB",
    }
    
    def __init__(self, model_name: str = "base", device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._model_loaded = False
        
        logger.info(f"WhisperASR initialized (model: {model_name}, device: auto)")
    
    def _load_model(self):
        """懒加载模型"""
        if self._model_loaded:
            return
        
        import whisper
        import torch
        
        # 自动选择设备
        if self.device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Loading Whisper {self.model_name} on {self.device}...")
        
        try:
            self._model = whisper.load_model(self.model_name, device=self.device)
            self._model_loaded = True
            logger.info(f"Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def transcribe(
        self,
        audio_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        language: str = "auto",
        task: str = "transcribe",
    ) -> str:
        """
        语音识别
        
        Args:
            audio_path: 音频文件路径
            output_path: 输出字幕路径（.srt格式）
            language: 源语言，auto自动检测
            task: transcribe 或 translate
        
        Returns:
            SRT 格式的字幕内容
        """
        self._load_model()
        
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        # 生成输出路径
        if not output_path:
            output_path = TEMP_DIR / f"{audio_path.stem}.srt"
        else:
            output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Whisper 参数
        options = {
            "task": task,
            "fp16": self.device == "cuda",
        }
        
        if language != "auto":
            options["language"] = language
        
        logger.info(f"Transcribing: {audio_path}")
        
        try:
            # 使用 soundfile 直接读取音频（避免 ffmpeg 依赖）
            import soundfile as sf
            import numpy as np
            
            audio_data, sample_rate = sf.read(str(audio_path), dtype='float32')
            
            # 如果是立体声，转为单声道
            if len(audio_data.shape) > 1:
                audio_data = audio_data.mean(axis=1)
            
            # 确保是 16kHz
            if sample_rate != 16000:
                import librosa
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
            
            # 执行识别（传入音频数组）
            result = self._model.transcribe(audio_data, **options)
            
            # 生成 SRT 格式
            srt_content = self._result_to_srt(result)
            
            # 保存文件
            output_path.write_text(srt_content, encoding="utf-8")
            
            logger.info(f"SRT saved to: {output_path}")
            
            return srt_content
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            raise
    
    def transcribe_audio(
        self,
        audio_path: Union[str, Path],
        language: str = "auto",
    ) -> dict:
        """
        直接返回识别结果（不生成字幕文件）
        
        Returns:
            {
                "text": str,  # 完整文本
                "segments": [...],  # 分段信息
                "language": str  # 检测到的语言
            }
        """
        self._load_model()
        
        audio_path = Path(audio_path)
        
        options = {}
        if language != "auto":
            options["language"] = language
        
        # 使用 soundfile 直接读取音频（避免 ffmpeg 依赖）
        import soundfile as sf
        import numpy as np
        
        audio_data, sample_rate = sf.read(str(audio_path), dtype='float32')
        
        # 如果是立体声，转为单声道
        if len(audio_data.shape) > 1:
            audio_data = audio_data.mean(axis=1)
        
        # 确保是 16kHz
        if sample_rate != 16000:
            import librosa
            audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
        
        result = self._model.transcribe(audio_data, **options)
        
        return {
            "text": result["text"],
            "segments": result["segments"],
            "language": result.get("language", language),
        }
    
    def _result_to_srt(self, result: dict) -> str:
        """将 Whisper 结果转换为 SRT 格式"""
        segments = result.get("segments", [])
        
        if not segments:
            return ""
        
        srt_lines = []
        
        for i, segment in enumerate(segments, 1):
            start = self._format_timestamp(segment["start"])
            end = self._format_timestamp(segment["end"])
            text = segment["text"].strip()
            
            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")  # 空行分隔
        
        return "\n".join(srt_lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """将秒数格式化为 SRT 时间戳 (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def get_model_info(self) -> dict:
        """获取模型信息"""
        return {
            "name": self.model_name,
            "size": self.MODEL_SIZES.get(self.model_name, "unknown"),
            "device": self.device,
            "loaded": self._model_loaded,
        }
    
    @staticmethod
    def list_models() -> dict:
        """列出可用模型"""
        return WhisperASR.MODEL_SIZES.copy()