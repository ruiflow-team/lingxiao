"""
Wav2Lip 口型同步模块
"""
import subprocess
import sys
import logging
from pathlib import Path
from typing import Union, Optional
from loguru import logger

from .config import WAV2LIP_MODEL_DIR, TEMP_DIR


class Wav2LipClient:
    """
    Wav2Lip 口型同步封装
    
    使用方式:
        client = Wav2LipClient()
        client.process("input_video.mp4", "chinese_audio.wav", "output.mp4")
    """
    
    def __init__(
        self,
        model_path: Optional[Path] = None,
        checkpoint_path: Optional[Path] = None,
        gpu_id: int = 0,
    ):
        self.model_path = model_path or (WAV2LIP_MODEL_DIR / "wav2lip.pth")
        self.checkpoint_path = checkpoint_path or (WAV2LIP_MODEL_DIR / "checkpoints" / "wav2lip_gan.pth")
        self.gpu_id = gpu_id
        
        self.w2l_script = Path(__file__).parent.parent / "deps" / "Wav2Lip" / "inference.py"
        
        if not self.checkpoint_path.exists():
            logger.warning(f"Wav2Lip checkpoint not found at {self.checkpoint_path}, lip sync disabled")
            self.available = False
        else:
            self.available = True
            logger.info(f"Wav2LipClient initialized")
    
    def process(
        self,
        video_path: Union[str, Path],
        audio_path: Union[str, Path],
        output_path: Union[str, Path],
        resize_factor: int = 1,
        pad_top: int = 0,
        pad_bottom: int = 10,
        pad_left: int = 0,
        pad_right: int = 0,
        nosmooth: bool = False,
        face_detect_mode: str = "hog",  # hog, cnn
        progress_callback=None,
    ) -> str:
        """
        处理口型同步
        
        Args:
            video_path: 输入视频路径
            audio_path: 配音音频路径
            output_path: 输出视频路径
            resize_factor: 缩放因子
            pad_*: 填充参数
            nosmooth: 禁用平滑
            face_detect_mode: 人脸检测模式
            progress_callback: 进度回调
        
        Returns:
            输出视频路径
        """
        if not self.available:
            raise RuntimeError("Wav2Lip not available")
        
        video_path = Path(video_path)
        audio_path = Path(audio_path)
        output_path = Path(output_path)
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 构建命令
        # 构建命令 - 使用 /usr/bin/python3 确保能访问 cv2/scipy
        cmd = [
            "/usr/bin/python3", str(self.w2l_script),
            "--checkpoint_path", str(self.checkpoint_path),
            "--face", str(video_path),
            "--audio", str(audio_path),
            "--outfile", str(output_path),
            "--pads", str(pad_top), str(pad_bottom), str(pad_left), str(pad_right),
            "--resize_factor", str(resize_factor),
        ]
        
        if nosmooth:
            cmd.append("--nosmooth")
        
        logger.info(f"Running Wav2Lip: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            
            for line in process.stdout:
                line = line.strip()
                logger.debug(line)
                
                # 解析进度
                if "Processing" in line and "%" in line:
                    try:
                        pct = int(line.split("%")[0].split()[-1])
                        if progress_callback:
                            progress_callback(pct, f"口型同步中... {pct}%")
                    except:
                        pass
            
            process.wait()
            
            if process.returncode == 0 and output_path.exists():
                logger.info(f"Wav2Lip output: {output_path}")
                return str(output_path)
            else:
                raise RuntimeError("Wav2Lip processing failed")
                
        except Exception as e:
            logger.error(f"Wav2Lip error: {e}")
            raise
    
    @staticmethod
    def download_model():
        """下载 Wav2Lip 模型"""
        # Wav2Lip 需要从 GitHub 或 Google Drive 下载
        logger.info("Please download Wav2Lip model manually:")
        logger.info("1. Download from: https://github.com/Rudrabha/Wav2Lip")
        logger.info("2. Download checkpoint: https://drive.google.com/file/d/1i4Gzp0qMxxG8_2zOu2eLQIG5Y-2T4Wv0/view")
        logger.info("3. Place wav2lip_gan.pth in models/wav2lip/checkpoints/")


class Wav2LipCloud:
    """
    云端 Wav2Lip - 对接 Vast.ai 集群
    
    使用方式:
        cloud = Wav2LipCloud(vast_api_key="your_key")
        cloud.process("input.mp4", "audio.wav", "output.mp4")
    """
    
    def __init__(self, vast_api_key: str):
        self.vast_api_key = vast_api_key
        self._vast_client = None
        self.instances = []
    
    @property
    def vast(self):
        """懒加载 Vast.ai 客户端"""
        if self._vast_client is None:
            from cloud.vast_client import VastAIClient
            self._vast_client = VastAIClient(api_key=self.vast_api_key)
        return self._vast_client
    
    def process(
        self,
        video_path: Union[str, Path],
        audio_path: Union[str, Path],
        output_path: Union[str, Path],
        num_gpus: int = 2,
        progress_callback=None,
    ) -> str:
        """
        通过云端集群处理口型同步
        
        Args:
            video_path: 输入视频
            audio_path: 配音音频
            output_path: 输出路径
            num_gpus: 使用的 GPU 数量
            progress_callback: 进度回调
        
        Returns:
            输出视频路径
        """
        from core.ffmpeg_utils import FFmpegMerger
        
        video_path = Path(video_path)
        audio_path = Path(audio_path)
        output_path = Path(output_path)
        
        merger = FFmpegMerger()
        
        # Step 1: 分割视频
        if progress_callback:
            progress_callback(5, "分割视频...")
        
        import tempfile
        segments_dir = Path(tempfile.mkdtemp())
        segments = merger.split_video(video_path, segments_dir, segment_duration=300)  # 5分钟一段
        
        if len(segments) == 1:
            # 不需要分割，直接处理
            return self._process_single_gpu(segments[0], audio_path, output_path, progress_callback)
        
        # Step 2: 启动 GPU 集群
        if progress_callback:
            progress_callback(10, f"启动 {min(num_gpus, len(segments))} 个 GPU 实例...")
        
        # 启动实例
        self.instances = self.vast.bid(
            gpu_type="RTX 4090",
            count=min(num_gpus, len(segments)),
            max_price=0.5,
        )
        
        if not self.instances:
            raise RuntimeError("No GPU instances available")
        
        try:
            # Step 3: 分发任务
            tasks = self._distribute_tasks(segments, self.instances)
            
            # Step 4: 等待完成
            results = self._wait_and_collect(tasks, progress_callback)
            
            # Step 5: 合并结果
            if progress_callback:
                progress_callback(95, "合并视频...")
            
            merged = merger.concat_videos(results, output_path)
            
            if progress_callback:
                progress_callback(100, "完成！")
            
            return str(merged)
            
        finally:
            # 清理：停止所有实例
            self._cleanup_instances()
    
    def _process_single_gpu(
        self,
        video_segment: Path,
        audio_path: Path,
        output_path: Path,
        progress_callback,
    ) -> str:
        """在单 GPU 上处理（如果视频很短）"""
        if progress_callback:
            progress_callback(10, "启动 GPU 实例...")
        
        # 租用最便宜的 GPU
        offers = self.vast.search_offers(gpu_name="RTX 4090")
        if not offers:
            raise RuntimeError("No GPU available")
        
        instance = offers[0]
        
        if progress_callback:
            progress_callback(20, f"GPU {instance.gpu_name} 已启动")
        
        # SSH 到实例并运行 Wav2Lip
        # TODO: 实现 SSH + Wav2Lip 远程执行
        raise NotImplementedError("Single GPU processing not fully implemented")
    
    def _distribute_tasks(self, segments: list, instances: list) -> list:
        """分发任务到多个 GPU"""
        tasks = []
        for i, seg in enumerate(segments):
            gpu_idx = i % len(instances)
            tasks.append({
                "segment": seg,
                "instance": instances[gpu_idx],
                "status": "pending",
            })
        return tasks
    
    def _wait_and_collect(self, tasks: list, progress_callback) -> list:
        """等待所有任务完成并收集结果"""
        import time
        
        results = [None] * len(tasks)
        total = len(tasks)
        
        while True:
            done_count = sum(1 for r in results if r is not None)
            progress = 20 + int(70 * done_count / total)
            
            if progress_callback:
                progress_callback(progress, f"处理中... {done_count}/{total}")
            
            if done_count == total:
                break
            
            time.sleep(5)
        
        return [r for r in results if r is not None]
    
    def _cleanup_instances(self):
        """停止所有 GPU 实例"""
        for instance in self.instances:
            try:
                self.vast.stop_instance(instance["id"])
            except Exception as e:
                logger.warning(f"Failed to stop instance {instance.get('id')}: {e}")