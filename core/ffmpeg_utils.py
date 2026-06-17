"""
FFmpeg 音视频处理工具
使用 imageio-ffmpeg 捆绑的 ffmpeg 二进制
"""
import subprocess
import logging
from pathlib import Path
from typing import Union, Optional
from loguru import logger

from core.config import TEMP_DIR

# 获取 imageio-ffmpeg 的 ffmpeg 路径
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
    logger.info(f"Using ffmpeg from imageio-ffmpeg: {FFMPEG_PATH}")
except ImportError:
    FFMPEG_PATH = "ffmpeg"  # 系统默认
    logger.warning("imageio-ffmpeg not found, using system ffmpeg")


def _find_ffprobe():
    """查找 ffprobe 路径"""
    import shutil
    # 1. 尝试系统 ffprobe
    if shutil.which("ffprobe"):
        return "ffprobe"
    # 2. 尝试从 ffmpeg 路径推断
    import imageio_ffmpeg
    ffmpeg_dir = Path(imageio_ffmpeg.get_ffmpeg_exe()).parent
    ffprobe_path = ffmpeg_dir / "ffprobe"
    if ffprobe_path.exists():
        return str(ffprobe_path)
    # 3. 尝试常见路径
    for p in ["/usr/local/bin/ffprobe", "/opt/homebrew/bin/ffprobe"]:
        if Path(p).exists():
            return p
    return "ffprobe"  # 最后 fallback


class FFmpegMerger:
    """
    FFmpeg 封装 - 音视频处理
    
    功能:
    - 提取音频
    - 合并音视频
    - 视频转码
    - 截取片段
    """
    
    def __init__(self, ffmpeg_path: str = None, ffprobe_path: str = None):
        self.ffmpeg = ffmpeg_path or FFMPEG_PATH
        self.ffprobe = ffprobe_path or _find_ffprobe()
    
    def extract_audio(
        self,
        video_path: Union[str, Path],
        audio_path: Optional[Union[str, Path]] = None,
        audio_format: str = "wav",
        sample_rate: int = 16000,
    ) -> str:
        """
        从视频提取音频
        
        Args:
            video_path: 视频文件路径
            audio_path: 输出音频路径
            audio_format: 音频格式 (wav, mp3, flac)
            sample_rate: 采样率
        
        Returns:
            生成的音频文件路径
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        if not audio_path:
            audio_path = TEMP_DIR / f"{video_path.stem}.{audio_format}"
        else:
            audio_path = Path(audio_path)
        
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.ffmpeg,
            "-i", str(video_path),
            "-vn",  # 禁用视频
            "-acodec", "pcm_s16le",  # PCM格式
            "-ar", str(sample_rate),  # 采样率
            "-ac", "1",  # 单声道
            "-y",  # 覆盖输出
            str(audio_path),
        ]
        
        logger.debug(f"Extracting audio: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"Audio extraction failed: {result.stderr}")
        
        logger.info(f"Audio extracted: {audio_path}")
        return str(audio_path)
    
    def merge_audio_video(
        self,
        video_path: Union[str, Path],
        audio_path: Union[str, Path],
        output_path: Union[str, Path],
        video_codec: str = "copy",
        audio_codec: str = "aac",
        video_bitrate: Optional[str] = None,
        audio_bitrate: str = "192k",
    ) -> str:
        """
        合并音视频
        
        Args:
            video_path: 视频文件路径
            audio_path: 音频文件路径
            output_path: 输出视频路径
            video_codec: 视频编码 (copy=保持原编码, libx264=重新编码)
            audio_codec: 音频编码 (aac, mp3, copy)
            video_bitrate: 视频码率 (如 "2M")
            audio_bitrate: 音频码率 (如 "192k")
        
        Returns:
            生成的视频文件路径
        """
        video_path = Path(video_path)
        audio_path = Path(audio_path)
        output_path = Path(output_path)
        
        for path in [video_path, audio_path]:
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.ffmpeg,
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", video_codec,
            "-c:a", audio_codec,
            "-y",
            str(output_path),
        ]
        
        # 添加码率参数
        if video_bitrate:
            cmd.insert(-2, "-b:v")
            cmd.insert(-2, video_bitrate)
        if audio_bitrate:
            cmd.insert(-2, "-b:a")
            cmd.insert(-2, audio_bitrate)
        
        logger.debug(f"Merging: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise RuntimeError(f"Video merge failed: {result.stderr}")
        
        logger.info(f"Video merged: {output_path}")
        return str(output_path)
    
    def get_video_info(self, video_path: Union[str, Path]) -> dict:
        """
        获取视频信息
        
        Returns:
            {"duration": float, "width": int, "height": int, "fps": float, ...}
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        # 尝试用 ffprobe（如果有）
        if self.ffprobe != "ffprobe" and Path(self.ffprobe).exists():
            return self._get_video_info_ffprobe(video_path)
        
        # fallback: 用 ffmpeg -i 获取信息
        return self._get_video_info_ffmpeg(video_path)
    
    def _get_video_info_ffprobe(self, video_path: Path) -> dict:
        """使用 ffprobe 获取视频信息"""
        cmd = [
            self.ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            logger.error(f"FFprobe error: {result.stderr}")
            return {}
        
        import json
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            logger.error(f"FFprobe JSON parse error: {result.stdout}")
            return {}
        
        # 提取视频流信息
        video_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})
        
        return {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "size": int(data.get("format", {}).get("size", 0)),
            "format": data.get("format", {}).get("format_name", ""),
            "width": int(video_stream.get("width", 0)),
            "height": int(video_stream.get("height", 0)),
            "fps": eval(video_stream.get("r_frame_rate", "0/1")) if video_stream.get("r_frame_rate") else 0,
            "video_codec": video_stream.get("codec_name", ""),
            "audio_codec": audio_stream.get("codec_name", ""),
            "audio_bitrate": audio_stream.get("bit_rate", ""),
        }
    
    def _get_video_info_ffmpeg(self, video_path: Path) -> dict:
        """使用 ffmpeg -i 获取视频信息（无需 ffprobe）"""
        import re
        
        cmd = [
            self.ffmpeg,
            "-i", str(video_path),
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        # ffmpeg -i 输出在 stderr
        output = result.stderr
        
        # 解析输出
        info = {
            "duration": 0,
            "size": video_path.stat().st_size,
            "format": video_path.suffix[1:],
            "width": 0,
            "height": 0,
            "fps": 0,
            "video_codec": "",
            "audio_codec": "",
            "audio_bitrate": "",
        }
        
        # 解析分辨率
        res_match = re.search(r'(\d{2,5})x(\d{2,5})', output)
        if res_match:
            info["width"] = int(res_match.group(1))
            info["height"] = int(res_match.group(2))
        
        # 解析时长
        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', output)
        if duration_match:
            h, m, s, cs = duration_match.groups()
            info["duration"] = int(h) * 3600 + int(m) * 60 + int(s) + int(cs) * 0.01
        
        # 解析帧率
        fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', output)
        if fps_match:
            info["fps"] = float(fps_match.group(1))
        
        # 解析视频编码
        video_match = re.search(r'Video:\s*(\w+)', output)
        if video_match:
            info["video_codec"] = video_match.group(1)
        
        # 解析音频编码
        audio_match = re.search(r'Audio:\s*(\w+)', output)
        if audio_match:
            info["audio_codec"] = audio_match.group(1)
        
        return info
    
    def split_video(
        self,
        video_path: Union[str, Path],
        output_dir: Union[str, Path],
        segment_duration: int = 600,  # 10分钟
    ) -> list:
        """
        分割视频为片段
        
        Args:
            video_path: 输入视频
            output_dir: 输出目录
            segment_duration: 每个片段时长（秒）
        
        Returns:
            片段文件路径列表
        """
        video_path = Path(video_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 获取视频时长
        info = self.get_video_info(video_path)
        duration = info.get("duration", 0)
        
        if duration <= segment_duration:
            # 不需要分割
            return [str(video_path)]
        
        cmd = [
            self.ffmpeg,
            "-i", str(video_path),
            "-c", "copy",  # 保持原编码，快速分割
            "-f", "segment",
            "-segment_time", str(segment_duration),
            "-reset_timestamps", "1",
            "-y",
            str(output_dir / f"{video_path.stem}_%03d{video_path.suffix}"),
        ]
        
        logger.debug(f"Splitting video: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg split error: {result.stderr}")
            raise RuntimeError(f"Video split failed: {result.stderr}")
        
        # 收集生成的片段
        segments = sorted(output_dir.glob(f"{video_path.stem}_*{video_path.suffix}"))
        logger.info(f"Video split into {len(segments)} segments")
        
        return [str(s) for s in segments]
    
    def concat_videos(
        self,
        video_paths: list,
        output_path: Union[str, Path],
    ) -> str:
        """
        拼接多个视频为一个
        
        Args:
            video_paths: 视频文件路径列表
            output_path: 输出文件路径
        
        Returns:
            拼接后的视频路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建临时文件列表
        list_file = TEMP_DIR / "concat_list.txt"
        with open(list_file, "w") as f:
            for path in video_paths:
                f.write(f"file '{path}'\n")
        
        cmd = [
            self.ffmpeg,
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-y",
            str(output_path),
        ]
        
        logger.debug(f"Concatenating: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg concat error: {result.stderr}")
            raise RuntimeError(f"Video concat failed: {result.stderr}")
        
        logger.info(f"Videos concatenated: {output_path}")
        return str(output_path)