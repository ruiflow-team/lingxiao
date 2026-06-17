"""
凌霄Web端管道 - 简化版流程
整合: Whisper ASR → MiniMax翻译 → Edge TTS → FFmpeg合成
"""
import os
import sys
import json
import asyncio
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Callable, List, Dict
from dataclasses import dataclass

from loguru import logger

# 引入现有模块
from core.asr import WhisperASR
from core.translator import MiniMaxTranslator, parse_srt, create_srt
from core.tts_engine import TTSEngine, get_tts_engine
from core.video_export import ExportTask


@dataclass
class PipelineResult:
    """管道执行结果"""
    success: bool
    output_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    tts_audio_path: Optional[str] = None
    source_text: Optional[str] = None
    translated_text: Optional[str] = None
    error: Optional[str] = None


class SimpleTranslationPipeline:
    """
    简化翻译管道 - Web端使用
    流程: 视频输入 → 提取音频 → ASR识别 → 翻译 → TTS合成 → 视频合成
    """
    
    def __init__(self, 
                 asr_model: str = "base",
                 device: str = "auto"):
        """初始化管道"""
        self.device = device
        self.temp_files: List[str] = []
        
        # 初始化各模块 (懒加载)
        logger.info("初始化简化翻译管道...")
        self.asr = WhisperASR(model_name=asr_model, device=device)
        self.translator = MiniMaxTranslator()
        self.tts = get_tts_engine()
        
    async def process(
        self,
        video_path: str,
        target_lang: str = "中文(普通话)",
        voice_style: str = "zh-CN-XiaoxiaoNeural",
        keep_original_audio: bool = True,
        original_volume: float = 0.3,
        tts_volume: float = 1.0,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> PipelineResult:
        """
        执行翻译流程
        
        Args:
            video_path: 输入视频路径
            target_lang: 目标语言
            voice_style: TTS音色
            keep_original_audio: 是否保留原声
            original_volume: 原声音量
            tts_volume: TTS音量
            output_path: 输出路径
            progress_callback: 进度回调 (progress_pct, message)
            
        Returns:
            PipelineResult 包含成功状态和输出路径
        """
        try:
            # 步骤1: 提取音频
            if progress_callback:
                progress_callback(5, "提取音频...")
            
            audio_path = await self._extract_audio(video_path)
            if not audio_path:
                return PipelineResult(success=False, error="音频提取失败")
            self.temp_files.append(audio_path)
            
            # 步骤2: ASR识别
            if progress_callback:
                progress_callback(15, "语音识别中...")
            
            asr_result = await asyncio.to_thread(
                self.asr.transcribe_audio,
                audio_path,
                language="auto"
            )
            source_text = asr_result.get("text", "")
            segments = asr_result.get("segments", [])
            
            if not source_text:
                return PipelineResult(success=False, error="识别结果为空")
            
            # 生成SRT
            srt_content = self._segments_to_srt(segments)
            
            # 步骤3: 翻译
            if progress_callback:
                progress_callback(30, "AI翻译中...")
            
            # 目标语言映射
            lang_code = self._map_lang_to_code(target_lang)
            
            # 批量翻译字幕
            translated_srt = await asyncio.to_thread(
                self._translate_segments,
                segments,
                lang_code
            )
            
            translated_text = "\n".join([s.get("text", "") for s in translated_srt])
            
            # 保存字幕文件
            srt_path = tempfile.mktemp(suffix=".srt")
            Path(srt_path).write_text(create_srt(translated_srt), encoding="utf-8")
            self.temp_files.append(srt_path)
            
            # 步骤4: TTS合成
            if progress_callback:
                progress_callback(60, "语音合成中...")
            
            # 将翻译后的文本合并用于TTS
            tts_text = translated_text.replace("\n", " ")
            
            tts_audio_path = tempfile.mktemp(suffix=".wav")
            tts_success = await asyncio.to_thread(
                self._synthesize_speech,
                tts_text,
                tts_audio_path,
                voice_style
            )
            
            if not tts_success or not os.path.exists(tts_audio_path):
                return PipelineResult(success=False, error="TTS合成失败")
            self.temp_files.append(tts_audio_path)
            
            # 步骤5: 视频合成
            if progress_callback:
                progress_callback(85, "合成视频中...")
            
            if not output_path:
                output_path = tempfile.mktemp(suffix="_translated.mp4")
            
            success = await self._merge_video_audio(
                video_path,
                tts_audio_path,
                output_path,
                keep_original_audio,
                original_volume,
                tts_volume
            )
            
            if not success:
                return PipelineResult(success=False, error="视频合成失败")
            
            # 清理临时文件
            self._cleanup_temp_files()
            
            if progress_callback:
                progress_callback(100, "完成!")
            
            return PipelineResult(
                success=True,
                output_path=output_path,
                subtitle_path=srt_path,
                tts_audio_path=tts_audio_path,
                source_text=source_text,
                translated_text=translated_text
            )
            
        except Exception as e:
            logger.error(f"管道处理失败: {e}")
            self._cleanup_temp_files()
            return PipelineResult(success=False, error=str(e))
    
    async def _extract_audio(self, video_path: str) -> Optional[str]:
        """从视频提取音频"""
        try:
            audio_path = tempfile.mktemp(suffix=".wav")
            
            cmd = [
                "ffmpeg", "-y",
                "-i", video_path,
                "-vn",
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                "-ac", "1",
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(audio_path):
                return audio_path
            return None
            
        except Exception as e:
            logger.error(f"提取音频失败: {e}")
            return None
    
    def _segments_to_srt(self, segments: List[Dict]) -> str:
        """将ASR结果转换为SRT格式"""
        lines = []
        for i, seg in enumerate(segments, 1):
            start = self._format_time(seg.get("start", 0))
            end = self._format_time(seg.get("end", 0))
            text = seg.get("text", "").strip()
            
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(text)
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_time(self, seconds: float) -> str:
        """格式化时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _map_lang_to_code(self, lang: str) -> str:
        """语言名称映射到代码"""
        mapping = {
            "中文(普通话)": "zh",
            "中文(粤语)": "zh",
            "中文(闽南语)": "zh",
            "英语": "en",
            "英语(美式)": "en",
            "英语(英式)": "en",
            "英语(澳式)": "en",
            "日语": "ja",
            "韩语": "ko",
            "法语": "fr",
            "德语": "de",
            "西班牙语": "es",
            "俄语": "ru",
            "意大利语": "it",
            "葡萄牙语": "pt",
            "阿拉伯语": "ar",
            "希腊语": "el",
            "土耳其语": "tr",
        }
        return mapping.get(lang, "en")
    
    def _translate_segments(self, segments: List[Dict], target_lang: str) -> List[Dict]:
        """翻译字幕段落"""
        results = []
        
        for seg in segments:
            text = seg.get("text", "").strip()
            if not text:
                results.append(seg)
                continue
            
            # 调用翻译API
            translated = self.translator.translate(text, "auto", target_lang)
            
            results.append({
                "start": seg.get("start"),
                "end": seg.get("end"),
                "text": translated
            })
        
        return results
    
    def _synthesize_speech(self, text: str, output_path: str, voice: str) -> bool:
        """TTS合成"""
        try:
            # 使用edge-tts
            import asyncio
            
            voice_mapping = {
                "zh-CN-XiaoxiaoNeural": "zh-CN-XiaoxiaoNeural",
                "zh-CN-YunxiNeural": "zh-CN-YunxiNeural",
                "en-US-JennyNeural": "en-US-JennyNeural",
                "en-US-GuyNeural": "en-US-GuyNeural",
                "ja-JP-NanamiNeural": "ja-JP-NanamiNeural",
            }
            
            voice_id = voice_mapping.get(voice, "zh-CN-XiaoxiaoNeural")
            
            # 运行edge-tts
            cmd = [
                sys.executable, "-m", "edge_tts",
                "--voice", voice_id,
                "--text", text,
                "--write-media", output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            return result.returncode == 0 and os.path.exists(output_path)
            
        except Exception as e:
            logger.error(f"TTS合成失败: {e}")
            return False
    
    async def _merge_video_audio(
        self,
        video_path: str,
        tts_audio: str,
        output_path: str,
        keep_original: bool,
        orig_vol: float,
        tts_vol: float
    ) -> bool:
        """合成视频"""
        try:
            if keep_original:
                # 混合原声和TTS
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", tts_audio,
                    "-filter_complex",
                    f"[0:a]volume={orig_vol}[a0];[1:a]volume={tts_vol}[a1];[a0][a1]amix=inputs=2:duration=first[outa]",
                    "-map", "0:v",
                    "-map", "[outa]",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    output_path
                ]
            else:
                # 只保留TTS
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", tts_audio,
                    "-map", "0:v",
                    "-map", "1:a",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    output_path
                ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            return result.returncode == 0 and os.path.exists(output_path)
            
        except Exception as e:
            logger.error(f"视频合成失败: {e}")
            return False
    
    def _cleanup_temp_files(self):
        """清理临时文件"""
        for f in self.temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except:
                pass
        self.temp_files.clear()


# 全局实例
_pipeline_instance = None

def get_pipeline(asr_model: str = "base", device: str = "auto") -> SimpleTranslationPipeline:
    """获取全局管道实例"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = SimpleTranslationPipeline(asr_model, device)
    return _pipeline_instance
