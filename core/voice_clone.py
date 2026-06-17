"""
凌霄智能影视翻译系统 - 语音克隆模块
基于GPT-SoVITS架构实现快速语音克隆
"""
import os
import sys
import json
import torch
import torchaudio
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import tempfile
import shutil

# 配置路径
ROOT_DIR = Path(__file__).parent.parent
VOICE_DIR = ROOT_DIR / "voices"
VOICE_DIR.mkdir(exist_ok=True)

class VoiceCloneManager:
    """语音克隆管理器 - 管理音色库和克隆任务"""
    
    def __init__(self):
        self.voices_file = VOICE_DIR / "voice_library.json"
        self.voices = self._load_voice_library()
        self.gpt_sovits_path = ROOT_DIR / "models" / "gpt-sovits"
        self._check_model_status()
        
    def _load_voice_library(self) -> Dict:
        """加载音色库"""
        if self.voices_file.exists():
            with open(self.voices_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "system_voices": {},
            "user_voices": {},
            "version": "1.0"
        }
        
    def _save_voice_library(self):
        """保存音色库"""
        with open(self.voices_file, 'w', encoding='utf-8') as f:
            json.dump(self.voices, f, ensure_ascii=False, indent=2)
            
    def _check_model_status(self):
        """检查GPT-SoVITS模型状态"""
        self.model_ready = False
        required_files = [
            "gpt/model.ckpt",
            "sovits/model.pth",
            "bert/chinese-roberta-wwm-ext-large"
        ]
        
        for f in required_files:
            if not (self.gpt_sovits_path / f).exists():
                self.model_status = f"缺少: {f}"
                return
                
        self.model_ready = True
        self.model_status = "已就绪"
        
    def list_voices(self, language: str = None) -> List[Dict]:
        """
83e出所有音色
        
        Args:
            language: 按语言筛选 (None表示全部)
            
        Returns:
            音色列表
        """
        voices = []
        
        # 系统音色
        for vid, info in self.voices.get("system_voices", {}).items():
            if language is None or info.get("language") == language:
                voices.append({
                    "id": vid,
                    "name": info["name"],
                    "type": "system",
                    "language": info.get("language", "zh"),
                    "description": info.get("description", ""),
                    "sample_count": info.get("sample_count", 0)
                })
                
        # 用户克隆音色
        for vid, info in self.voices.get("user_voices", {}).items():
            if language is None or info.get("language") == language:
                voices.append({
                    "id": vid,
                    "name": info["name"],
                    "type": "cloned",
                    "language": info.get("language", "zh"),
                    "description": info.get("description", ""),
                    "created_at": info.get("created_at"),
                    "sample_duration": info.get("sample_duration", 0)
                })
                
        return voices
        
    def add_voice_sample(self, voice_id: str, audio_path: str, 
                        text: str = None) -> bool:
        """
        添加音色样本
        
        Args:
            voice_id: 音色ID
            audio_path: 音频文件路径
            text: 对应文本 (用于训练)
            
        Returns:
            是否成功
        """
        voice_path = VOICE_DIR / voice_id
        voice_path.mkdir(exist_ok=True)
        samples_dir = voice_path / "samples"
        samples_dir.mkdir(exist_ok=True)
        
        # 复制并转换音频
        try:
            import librosa
            audio, sr = librosa.load(audio_path, sr=32000)
            
            # 生成样本ID
            sample_id = f"sample_{len(list(samples_dir.glob('*.wav')))}"
            output_path = samples_dir / f"{sample_id}.wav"
            
            # 保存为32kHz单声道
            torchaudio.save(str(output_path), 
                          torch.tensor(audio).unsqueeze(0), 32000)
            
            # 保存元数据
            meta = {
                "text": text or "",
                "duration": len(audio) / 32000,
                "original_path": audio_path
            }
            with open(samples_dir / f"{sample_id}.json", 'w') as f:
                json.dump(meta, f)
                
            return True
            
        except Exception as e:
            print(f"添加样本失败: {e}")
            return False
            
    def clone_voice(self, name: str, sample_paths: List[str], 
                   language: str = "zh") -> Optional[str]:
        """
        克隆新音色
        
        Args:
            name: 音色名称
            sample_paths: 样本音频路径列表
            language: 语言代码
            
        Returns:
            音色ID (或None如果失败)
        """
        if not self.model_ready:
            print(f"GPT-SoVITS模型未就绪: {self.model_status}")
            return None
            
        # 生成音色ID
        import uuid
        voice_id = f"voice_{uuid.uuid4().hex[:8]}"
        
        # 添加样本
        total_duration = 0
        for path in sample_paths:
            if self.add_voice_sample(voice_id, path):
                import librosa
                audio, _ = librosa.load(path, sr=32000)
                total_duration += len(audio) / 32000
                
        # 保存到音色库
        self.voices["user_voices"][voice_id] = {
            "name": name,
            "language": language,
            "created_at": "2025-05-25",
            "sample_count": len(sample_paths),
            "sample_duration": round(total_duration, 2),
            "path": str(VOICE_DIR / voice_id)
        }
        self._save_voice_library()
        
        return voice_id
        
    def synthesize(self, voice_id: str, text: str, 
                   output_path: str = None) -> Optional[str]:
        """
        使用克隆音色合成语音
        
        Args:
            voice_id: 音色ID
            text: 要合成的文本
            output_path: 输出路径 (默认自动生成)
            
        Returns:
            输出音频路径
        """
        if not self.model_ready:
            return None
            
        # 检查音色是否存在
        voice_info = (self.voices["user_voices"].get(voice_id) or 
                     self.voices["system_voices"].get(voice_id))
        if not voice_info:
            print(f"音色不存在: {voice_id}")
            return None
            
        # 生成输出路径
        if output_path is None:
            import uuid
            output_path = str(ROOT_DIR / "output" / f"tts_{uuid.uuid4().hex[:8]}.wav")
            
        # TODO: 调用GPT-SoVITS推理
        # 这里需要集成真实的GPT-SoVITS推理代码
        
        return output_path
        
    def delete_voice(self, voice_id: str) -> bool:
        """删除音色"""
        if voice_id in self.voices["user_voices"]:
            # 删除文件
            voice_path = VOICE_DIR / voice_id
            if voice_path.exists():
                shutil.rmtree(voice_path)
                
            # 从库中移除
            del self.voices["user_voices"][voice_id]
            self._save_voice_library()
            return True
        return False
        
    def preview_voice(self, voice_id: str, sample_text: str = None) -> Optional[str]:
        """
        预览音色
        
        Returns:
            预览音频路径
        """
        if sample_text is None:
            sample_text = "这是一个语音预览测试，用于检验克隆效果。"
            
        return self.synthesize(voice_id, sample_text)


class VoiceCloneUI:
    """语音克隆UI组件 - 供PyQt5集成"""
    
    def __init__(self, manager: VoiceCloneManager):
        self.manager = manager
        
    def get_voice_selector_widget(self, parent=None):
        """获取音色选择器微件"""
        from PyQt5.QtWidgets import QComboBox, QWidget, QVBoxLayout, QLabel
        
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        label = QLabel("选择音色:")
        layout.addWidget(label)
        
        combo = QComboBox()
        voices = self.manager.list_voices()
        
        # 分组显示
        combo.addItem("系统音色", None)
        for v in voices:
            if v["type"] == "system":
                combo.addItem(f"  {v['name']}", v["id"])
                
        combo.addItem("我的克隆", None)
        for v in voices:
            if v["type"] == "cloned":
                combo.addItem(f"  {v['name']}", v["id"])
                
        layout.addWidget(combo)
        
        return widget, combo
        
    def show_clone_dialog(self, parent=None):
        """显示克隆对话框"""
        # TODO: 实现克隆对话框
        pass


# 全局实例
_voice_manager = None

def get_voice_manager() -> VoiceCloneManager:
    """获取全局语音管理器实例"""
    global _voice_manager
    if _voice_manager is None:
        _voice_manager = VoiceCloneManager()
    return _voice_manager


if __name__ == "__main__":
    # 测试
    manager = get_voice_manager()
    print(f"模型状态: {manager.model_status}")
    print(f"当前音色: {len(manager.list_voices())}")
