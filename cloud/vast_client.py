"""
Vast.ai GPU 集群客户端
用于云端口型同步处理
"""
import os
import sys
import logging
import time
import requests
from typing import Optional, Callable, Union
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

# 尝试导入配置，失败时使用环境变量
try:
    from core.config import VAST_API_KEY
except ImportError:
    VAST_API_KEY = os.environ.get("VAST_API_KEY", "")

logger.add(sys.stderr.write, level="INFO")


@dataclass
class GPUInstance:
    id: int
    name: str
    gpu_name: str
    gpu_count: int
    price_per_hour: float
    reliability: float
    status: str


class VastAIClient:
    """
    Vast.ai GPU 集群管理
    
    使用方式:
        client = VastAIClient(api_key="your_key")
        instances = client.bid(gpu_type="RTX 4090", count=4, max_price=0.5)
    """
    
    BASE_URL = "https://console.vast.ai/api/v0"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or VAST_API_KEY
        if not self.api_key:
            raise ValueError("Vast.ai API key required")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
    
    def search_offers(
        self,
        gpu_name: str = "RTX 4090",
        min_reliability: float = 0.95,
        order_by: str = "price",
    ) -> list:
        """
        搜索可用的 GPU 实例
        
        Args:
            gpu_name: GPU 型号 (RTX 4090, RTX 3090, A100, etc)
            min_reliability: 最低可靠性
            order_by: 排序方式 (price, reliability, gpu_count)
        
        Returns:
            GPU 实例列表
        """
        params = {
            "gpu_name": gpu_name,
            "reliability": {"gte": min_reliability},
            "order_by": order_by,
        }
        
        try:
            resp = self.session.get(
                f"{self.BASE_URL}/bundles",
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            
            offers = data.get("offers", [])
            logger.info(f"Found {len(offers)} offers for {gpu_name}")
            
            return [
                GPUInstance(
                    id=o["id"],
                    name=o.get("machine_name", f"machine_{o['id']}"),
                    gpu_name=o["gpu_name"],
                    gpu_count=o["num_gpus"],
                    price_per_hour=o["dph_total"],
                    reliability=o.get("reliability", 0.99),
                    status=o["status"],
                )
                for o in offers[:20]  # 取前20个
            ]
            
        except Exception as e:
            logger.error(f"Search offers error: {e}")
            return []
    
    def bid(
        self,
        gpu_type: str = "RTX 4090",
        count: int = 1,
        max_price: float = 0.5,
        image: str = "tensorflow/tensorflow:latest-gpu",
    ) -> list:
        """
        竞价启动多个 GPU 实例
        
        Args:
            gpu_type: GPU 型号
            count: 需要的 GPU 数量
            max_price: 每 GPU 每小时最高价格
            image: Docker 镜像
        
        Returns:
            已启动的实例列表
        """
        # 先搜索可用实例
        offers = self.search_offers(gpu_name=gpu_type)
        
        # 筛选符合价格的
        suitable = [o for o in offers if o.price_per_hour <= max_price][:count]
        
        if len(suitable) < count:
            logger.warning(f"Only {len(suitable)} instances available under ${max_price}/hr")
        
        launched = []
        for offer in suitable:
            instance = self._launch_instance(offer.id, image)
            if instance:
                launched.append(instance)
        
        return launched
    
    def _launch_instance(self, offer_id: int, image: str) -> Optional[dict]:
        """启动单个实例"""
        payload = {
            "offer_id": offer_id,
            "image": image,
            "args": [],
            "force": False,
        }
        
        try:
            resp = self.session.post(
                f"{self.BASE_URL}/instances",
                json=payload,
                timeout=30,
            )
            
            if resp.status_code == 201:
                data = resp.json()
                instance_id = data.get("instance", {}).get("id")
                logger.info(f"Launched instance {instance_id}")
                return {"id": instance_id, "offer_id": offer_id, "status": "running"}
            else:
                logger.error(f"Launch failed: {resp.status_code} {resp.text}")
                return None
                
        except Exception as e:
            logger.error(f"Launch instance error: {e}")
            return None
    
    def get_instance_status(self, instance_id: int) -> dict:
        """获取实例状态"""
        try:
            resp = self.session.get(f"{self.BASE_URL}/instances/{instance_id}")
            resp.raise_for_status()
            return resp.json().get("instance", {})
        except Exception as e:
            logger.error(f"Get status error: {e}")
            return {}
    
    def terminate_instance(self, instance_id: int) -> bool:
        """终止实例"""
        try:
            resp = self.session.delete(f"{self.BASE_URL}/instances/{instance_id}")
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Terminate error: {e}")
            return False
    
    def upload_file(self, instance_id: int, local_path: str, remote_path: str) -> bool:
        """上传文件到实例"""
        try:
            with open(local_path, "rb") as f:
                resp = self.session.put(
                    f"{self.BASE_URL}/instances/{instance_id}/files{remote_path}",
                    data=f,
                    timeout=120,
                )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Upload error: {e}")
            return False
    
    def run_command(self, instance_id: int, command: str) -> tuple:
        """
        在实例上执行命令
        
        Returns:
            (stdout, stderr, exit_code)
        """
        try:
            resp = self.session.post(
                f"{self.BASE_URL}/instances/{instance_id}/commands",
                json={"cmd": command},
                timeout=60,
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return (
                    data.get("stdout", ""),
                    data.get("stderr", ""),
                    data.get("exit_code", 0),
                )
            return ("", resp.text, -1)
            
        except Exception as e:
            logger.error(f"Command error: {e}")
            return ("", str(e), -1)
    
    def get_ssh_connection(self, instance_id: int) -> dict:
        """获取 SSH 连接信息"""
        instance = self.get_instance_status(instance_id)
        
        return {
            "host": instance.get("ssh_host", ""),
            "port": instance.get("ssh_port", 22),
            "user": "root",
        }


class CloudLipsyncManager:
    """
    云端口型同步任务管理器
    
    负责:
    1. 分割视频
    2. 分发到多个 GPU 实例
    3. 收集结果
    4. 合并视频
    """
    
    def __init__(self, vast_api_key: str):
        self.vast = VastAIClient(vast_api_key)
        self.instances = []
    
    def process_video(
        self,
        video_path: Union[str, Path],
        audio_path: Union[str, Path],
        output_path: Union[str, Path],
        num_gpus: int = 4,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """
        云端处理口型同步
        
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
                progress_callback(100, "完成!")
            
            return merged
            
        finally:
            # Step 6: 清理实例
            for inst in self.instances:
                self.vast.terminate_instance(inst["id"])
    
    def _process_single_gpu(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        progress_callback: Optional[Callable],
    ) -> str:
        """单 GPU 处理"""
        # TODO: 实现 Wav2Lip 调用
        raise NotImplementedError("Single GPU processing not implemented yet")
    
    def _distribute_tasks(self, segments: list, instances: list) -> dict:
        """分发任务到多个实例"""
        tasks = {}
        
        for i, segment in enumerate(segments):
            inst = instances[i % len(instances)]
            inst_id = inst["id"]
            
            if inst_id not in tasks:
                tasks[inst_id] = []
            
            tasks[inst_id].append(segment)
        
        return tasks
    
    def _wait_and_collect(
        self,
        tasks: dict,
        progress_callback: Optional[Callable],
    ) -> list:
        """等待所有任务完成并收集结果"""
        results = []
        total_tasks = sum(len(t) for t in tasks.values())
        completed = 0
        
        while completed < total_tasks:
            # 检查每个实例状态
            for inst_id, segments in tasks.items():
                status = self.vast.get_instance_status(inst_id)
                # TODO: 检查任务完成状态
            
            time.sleep(30)
            
            if progress_callback:
                pct = 20 + int(70 * completed / total_tasks)
                progress_callback(pct, f"处理中... ({completed}/{total_tasks})")
            
            completed += 1  # 简化，实际需要追踪
        
        return results


def get_vast_client() -> VastAIClient:
    """获取 Vast.ai 客户端"""
    return VastAIClient()