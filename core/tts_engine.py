"""
凌霄智能影视翻译系统 - TTS引擎模块
支持多种TTS后端: edge-tts(在线) / F5-TTS(本地克隆) / GPT-SoVITS(本地克隆)
"""
import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Literal
from dataclasses import dataclass
import subprocess

ROOT_DIR = Path(__file__).parent.parent

@dataclass
class TTSConfig:
    """TTS配置"""
    backend: Literal["edge", "f5", "gpt_sovits"] = "edge"
    voice_id: str = "zh-CN-XiaoxiaoNeural"
    speed: float = 1.0
    pitch: float = 0.0
    volume: float = 100.0


class TTSEngine:
    """
    TTS引擎 - 统一接口封装多种后端
    """
    
    def __init__(self):
        self.config = TTSConfig()
        self._backends = {}
        self._init_backends()
        
    def _init_backends(self):
        """初始化各种后端"""
        # edge-tts总是可用
        self._backends["edge"] = EdgeTTSBackend()
        
        # 检查本地模型
        f5_path = ROOT_DIR / "models" / "f5-tts"
        if f5_path.exists():
            try:
                self._backends["f5"] = F5TTSBackend(f5_path)
            except Exception as e:
                print(f"F5-TTS初始化失败: {e}")
                
        gpt_path = ROOT_DIR / "models" / "gpt-sovits"
        if (gpt_path / "gpt" / "model.ckpt").exists():
            try:
                self._backends["gpt_sovits"] = GPTSoVITSBackend(gpt_path)
            except Exception as e:
                print(f"GPT-SoVITS初始化失败: {e}")
                
    def list_backends(self) -> List[str]:
        """获取可用后端列表"""
        return list(self._backends.keys())
        
    def list_voices(self, backend: str = None) -> List[Dict]:
        """获取音色列表"""
        if backend and backend in self._backends:
            return self._backends[backend].list_voices()
            
        # 返回所有后端的音色
        voices = []
        for name, backend_obj in self._backends.items():
            for v in backend_obj.list_voices():
                v["backend"] = name
                voices.append(v)
        return voices
        
    def synthesize(self, text: str, config: TTSConfig = None, 
                   output_path: str = None) -> Optional[str]:
        """
        合成语音
        
        Args:
            text: 要合成的文本
            config: TTS配置 (默认使用self.config)
            output_path: 输出路径
            
        Returns:
            输出音频路径
        """
        cfg = config or self.config
        
        if cfg.backend not in self._backends:
            print(f"后端不可用: {cfg.backend}")
            return None
            
        backend = self._backends[cfg.backend]
        return backend.synthesize(text, cfg, output_path)
        
    def clone_voice(self, name: str, sample_path: str, 
                   backend: str = "f5") -> Optional[str]:
        """
        克隆音色
        
        Args:
            name: 音色名称
            sample_path: 样本音频路径
            backend: 使用的后端
            
        Returns:
            音色ID
        """
        if backend not in self._backends:
            return None
            
        return self._backends[backend].clone_voice(name, sample_path)


class EdgeTTSBackend:
    """edge-tts后端 - 在线服务"""
    
    VOICES = {
        "zh-CN": [
            ("zh-CN-XiaoxiaoNeural", "晓晓 - 温柔女声"),
            ("zh-CN-YunxiNeural", "云希 - 活泼男声"),
            ("zh-CN-YunjianNeural", "云健 - 新闻播报"),
        ],
        "en-US": [
            ("en-US-AriaNeural", "Aria - 女声"),
            ("en-US-GuyNeural", "Guy - 男声"),
        ],
        "ja-JP": [
            ("ja-JP-NanamiNeural", "Nanami - 女声"),
        ],
        "ko-KR": [
            ("ko-KR-SunHiNeural", "SunHi - 女声"),
        ],
    }
    
    def list_voices(self) -> List[Dict]:
        voices = []
        for lang, voice_list in self.VOICES.items():
            for vid, name in voice_list:
                voices.append({
                    "id": vid,
                    "name": name,
                    "language": lang,
                    "type": "system",
                    "supports_clone": False
                })
        return voices
        
    def synthesize(self, text: str, config: TTSConfig, 
                   output_path: str = None) -> Optional[str]:
        try:
            import edge_tts
            import asyncio
            
            if output_path is None:
                output_path = str(ROOT_DIR / "output" / f"edge_{hash(text)}.mp3")
                
            communicate = edge_tts.Communicate(text, config.voice_id)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(communicate.save(output_path))
            
            return output_path
            
        except Exception as e:
            print(f"edge-tts合成失败: {e}")
            return None
            
    def clone_voice(self, name: str, sample_path: str) -> Optional[str]:
        """edge-tts不支持克隆"""
        return None


class F5TTSBackend:
    """F5-TTS后端 - 轻量级本地克隆"""
    
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self._model = None
        self._load_model()
        
    def _load_model(self):
        """加载F5-TTS模型"""
        # TODO: 实现F5-TTS模型加载
        pass
        
    def list_voices(self) -> List[Dict]:
        # 返回系统音色 + 用户克隆音色
        return [
            {"id": "f5_default", "name": "F5默认", "language": "zh", "type": "system"}
        ]
        
    def synthesize(self, text: str, config: TTSConfig, 
                   output_path: str = None) -> Optional[str]:
        # TODO: 实现F5-TTS合成
        return None
        
    def clone_voice(self, name: str, sample_path: str) -> Optional[str]:
        # TODO: 实现F5-TTS克隆
        return None


class GPTSoVITSBackend:
    """GPT-SoVITS后端 - 高质量本地克隆"""
    
    def __init__(self, model_path: Path):
        self.model_path = model_path
        self._gpt_model = None
        self._sovits_model = None
        
    def list_voices(self) -> List[Dict]:
        return [
            {"id": "gptsovits_default", "name": "GPT-SoVITS默认", "language": "zh", "type": "system"}
        ]
        
    def synthesize(self, text: str, config: TTSConfig, 
                   output_path: str = None) -> Optional[str]:
        # TODO: 实现GPT-SoVITS合成
        return None
        
    def clone_voice(self, name: str, sample_path: str) -> Optional[str]:
        # TODO: 实现GPT-SoVITS克隆
        return None


# 全局实例
_tts_engine = None

def get_tts_engine() -> TTSEngine:
    """获取全局TTS引擎"""
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine
