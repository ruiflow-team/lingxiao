"""
凌霄智能影视翻译系统 - 视频导出模块
FFmpeg合成翻译后视频
"""
import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal

ROOT_DIR = Path(__file__).parent.parent
OUTPUT_DIR = ROOT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class ExportTask:
    """导出任务配置"""
    task_id: str
    input_video: str
    subtitles: List[Dict]  # [{start, end, text}, ...]
    tts_audio: str  # 合成后的TTS音频
    output_path: str
    # 选项
    keep_original_audio: bool = True  # 保留原声
    original_volume: float = 0.3  # 原声音量
    tts_volume: float = 1.0  # TTS音量
    burn_subtitles: bool = False  # 是否烧录字幕
    subtitle_style: str = "default"  # 字幕样式
    

class VideoExporter(QThread):
    """视频导出线程"""
    
    progress = pyqtSignal(int, str)  # 进度百分比, 状态消息
    finished_signal = pyqtSignal(str, bool)  # 输出路径, 是否成功
    
    def __init__(self, task: ExportTask):
        super().__init__()
        self.task = task
        self._cancelled = False
        
    def run(self):
        """执行导出"""
        try:
            self.progress.emit(5, "准备导出...")
            
            # 检查FFmpeg
            if not self._check_ffmpeg():
                self.finished_signal.emit("", False)
                return
                
            # 构建导出命令
            self.progress.emit(10, "分析视频...")
            
            # 获取视频信息
            video_info = self._get_video_info(self.task.input_video)
            if not video_info:
                self.progress.emit(0, "无法读取视频信息")
                self.finished_signal.emit("", False)
                return
                
            self.progress.emit(20, "合成音频轨道...")
            
            # 合成音频
            mixed_audio = self._mix_audio()
            if not mixed_audio:
                self.finished_signal.emit("", False)
                return
                
            self.progress.emit(60, "合并视频与音频...")
            
            # 合并音视频
            success = self._merge_video_audio(mixed_audio)
            
            # 清理临时文件
            if os.path.exists(mixed_audio):
                os.remove(mixed_audio)
                
            if success and os.path.exists(self.task.output_path):
                self.progress.emit(100, "导出完成!")
                self.finished_signal.emit(self.task.output_path, True)
            else:
                self.finished_signal.emit("", False)
                
        except Exception as e:
            self.progress.emit(0, f"导出失败: {e}")
            self.finished_signal.emit("", False)
            
    def _check_ffmpeg(self) -> bool:
        """检查FFmpeg是否可用"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            self.progress.emit(0, "未检测到FFmpeg,请先安装")
            return False
            
    def _get_video_info(self, video_path: str) -> Optional[Dict]:
        """获取视频信息"""
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration,r_frame_rate",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if 'streams' in data and len(data['streams']) > 0:
                    return data['streams'][0]
        except:
            pass
        return None
        
    def _mix_audio(self) -> Optional[str]:
        """合成音频轨道"""
        temp_dir = tempfile.gettempdir()
        mixed_path = os.path.join(temp_dir, f"mixed_{self.task.task_id}.wav")
        
        if self.task.keep_original_audio and os.path.exists(self.task.input_video):
            # 提取原声并混合
            cmd = [
                "ffmpeg", "-y",
                "-i", self.task.input_video,
                "-i", self.task.tts_audio,
                "-filter_complex",
                f"[0:a]volume={self.task.original_volume}[original];"
                f"[1:a]volume={self.task.tts_volume}[tts];"
                "[original][tts]amix=inputs=2:duration=longest[mixed]",
                "-map", "[mixed]",
                "-ac", "2",
                "-ar", "48000",
                mixed_path
            ]
        else:
            # 仅使用TTS
            cmd = [
                "ffmpeg", "-y",
                "-i", self.task.tts_audio,
                "-ac", "2",
                "-ar", "48000",
                mixed_path
            ]
            
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0 and os.path.exists(mixed_path):
            return mixed_path
        return None
        
    def _merge_video_audio(self, audio_path: str) -> bool:
        """合并音视频"""
        cmd = [
            "ffmpeg", "-y",
            "-i", self.task.input_video,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            self.task.output_path
        ]
        
        # 如果需要烧录字幕
        if self.task.burn_subtitles and self.task.subtitles:
            srt_path = self._create_srt_file()
            if srt_path:
                # 重新构建带字幕的命令
                cmd = [
                    "ffmpeg", "-y",
                    "-i", self.task.input_video,
                    "-i", audio_path,
                    "-vf", f"subtitles={srt_path}",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-shortest",
                    self.task.output_path
                ]
                
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode != 0:
            error = result.stderr.decode('utf-8', errors='ignore')[:200]
            self.progress.emit(70, f"合并失败: {error}")
            return False
            
        return os.path.exists(self.task.output_path)
        
    def _create_srt_file(self) -> Optional[str]:
        """创建SRT字幕文件"""
        if not self.task.subtitles:
            return None
            
        temp_dir = tempfile.gettempdir()
        srt_path = os.path.join(temp_dir, f"subtitles_{self.task.task_id}.srt")
        
        with open(srt_path, 'w', encoding='utf-8') as f:
            for i, sub in enumerate(self.task.subtitles, 1):
                start = self._format_srt_time(sub.get('start', 0))
                end = self._format_srt_time(sub.get('end', 0))
                text = sub.get('text', '')
                
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
                
        return srt_path
        
    def _format_srt_time(self, seconds: float) -> str:
        """格式化SRT时间"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        
    def cancel(self):
        """取消导出"""
        self._cancelled = True


class ExportManager:
    """导出管理器"""
    
    def __init__(self):
        self.current_exporter: Optional[VideoExporter] = None
        self.export_history: List[Dict] = []
        
    def create_export_task(
        self,
        input_video: str,
        subtitles: List[Dict],
        tts_audio: str,
        output_name: str = None,
        options: Dict = None
    ) -> ExportTask:
        """创建导出任务"""
        import uuid
        
        task_id = uuid.uuid4().hex[:8]
        
        if output_name is None:
            timestamp = datetime.now().strftime("%m%d_%H%M")
            output_name = f"translated_{timestamp}.mp4"
            
        output_path = str(OUTPUT_DIR / output_name)
        
        return ExportTask(
            task_id=task_id,
            input_video=input_video,
            subtitles=subtitles,
            tts_audio=tts_audio,
            output_path=output_path,
            **(options or {})
        )
        
    def start_export(self, task: ExportTask, 
                    progress_callback: Callable = None,
                    finished_callback: Callable = None) -> VideoExporter:
        """开始导出"""
        self.current_exporter = VideoExporter(task)
        
        if progress_callback:
            self.current_exporter.progress.connect(progress_callback)
        if finished_callback:
            self.current_exporter.finished_signal.connect(finished_callback)
            
        self.current_exporter.start()
        return self.current_exporter
        
    def cancel_current(self):
        """取消当前导出"""
        if self.current_exporter and self.current_exporter.isRunning():
            self.current_exporter.cancel()
            
    def get_output_files(self) -> List[Dict]:
        """获取输出文件列表"""
        files = []
        for f in OUTPUT_DIR.glob("*.mp4"):
            stat = f.stat()
            files.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size,
                "created": stat.st_mtime
            })
        return sorted(files, key=lambda x: x["created"], reverse=True)


# 全局实例
_export_manager = None

def get_export_manager() -> ExportManager:
    """获取全局导出管理器"""
    global _export_manager
    if _export_manager is None:
        _export_manager = ExportManager()
    return _export_manager


if __name__ == "__main__":
    # 测试
    manager = get_export_manager()
    print(f"FFmpeg可用: {VideoExporter(ExportTask('', [], '', ''))._check_ffmpeg()}")
    print(f"输出目录: {OUTPUT_DIR}")
