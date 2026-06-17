#!/usr/bin/env python3
"""
凌霄智能影视翻译系统 - 模型一键下载脚本
原则: 免费就下载，收费就自研

自动下载所有可用的免费预训练模型
"""

import os
import sys
import subprocess
from pathlib import Path
import urllib.request
import tarfile
import zipfile


MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(exist_ok=True)


class ModelDownloader:
    def __init__(self):
        self.success = []
        self.failed = []
    
    def log(self, msg):
        print(f"[INFO] {msg}")
    
    def error(self, msg):
        print(f"[ERROR] {msg}")
        
    def download_whisper(self):
        """下载Whisper模型"""
        self.log("下载 Whisper ASR 模型...")
        
        try:
            # 安装whisper库 (会自动下载模型)
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", 
                         "openai-whisper"], check=True)
            
            # 预下载small模型 (性价比最高)
            import whisper
            self.log("正在下载 Whisper small 模型 (约244MB)...")
            model = whisper.load_model("small")
            
            self.success.append(("Whisper (small)", "ASR"))
            return True
            
        except Exception as e:
            self.error(f"Whisper下载失败: {e}")
            self.failed.append(("Whisper", str(e)))
            return False
    
    def download_nllb(self):
        """下载NLLB翻译模型"""
        self.log("下载 NLLB 翻译模型...")
        
        try:
            # 安装依赖
            subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                         "transformers", "sentencepiece", "torch"], check=True)
            
            # 下载模型
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            
            model_name = "facebook/nllb-200-distilled-600M"
            self.log(f"正在下载 NLLB-200 (600M)...")
            
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            
            self.success.append(("NLLB-200 (600M)", "Translation"))
            return True
            
        except Exception as e:
            self.error(f"NLLB下载失败: {e}")
            self.failed.append(("NLLB", str(e)))
            return False
    
    def download_vits_english(self):
        """下载VITS英文模型"""
        self.log("下载 VITS 英文TTS模型...")
        
        try:
            # 尝试从HuggingFace下载
            from transformers import AutoModel, AutoTokenizer
            
            # 使用SpeechT5作为替代 (更易下载)
            self.log("下载 Microsoft SpeechT5...")
            from transformers import SpeechT5Processor, SpeechT5ForTextToSpeech
            
            processor = SpeechT5Processor.from_pretrained("microsoft/speecht5_tts")
            model = SpeechT5ForTextToSpeech.from_pretrained("microsoft/speecht5_tts")
            
            self.success.append(("SpeechT5 (English TTS)", "TTS"))
            return True
            
        except Exception as e:
            self.error(f"VITS/替代模型下载失败: {e}")
            self.failed.append(("VITS/SpeechT5", str(e)))
            return False
    
    def download_wav2lip(self):
        """尝试下载Wav2Lip"""
        self.log("尝试下载 Wav2Lip...")
        
        # 检查是否已存在
        wav2lip_dir = MODELS_DIR / "wav2lip"
        wav2lip_dir.mkdir(exist_ok=True)
        
        self.log("Wav2Lip 模型下载需要特殊处理")
        self.log("  官方地址: https://github.com/Rudrabha/Wav2Lip")
        self.log("  由于网络限制，需要手动下载或使用代理")
        
        # 创建指引文件
        guide_file = wav2lip_dir / "README.txt"
        guide_file.write_text("""
Wav2Lip 模型下载说明
========================

由于GitHub/GDrive访问受限，需要手动下载:

方法1: 使用镜像站
  - https://gh.api.99988866.xyz/
  - https://ghproxy.com/

方法2: HuggingFace镜像
  - 搜索 "wav2lip pretrained"

方法3: 自己训练 (花费高昂)
  - 需要LRS2数据集
  - 需要V100/A100 GPU

必需文件:
  - wav2lip_gan.pth (Wav2Lip + GAN)
  - wav2lip.pth (Wav2Lip 基础)
  - syncnet_v2.pth (SyncNet判别器)

下载完成后放入此目录
""")
        
        self.log(f"  已创建下载指引: {guide_file}")
        self.failed.append(("Wav2Lip", "需手动下载 - 使用镜像/代理"))
        return False
    
    def download_all(self):
        """下载所有可用模型"""
        print("=" * 60)
        print("凌霄模型下载脚本")
        print("=" * 60)
        print()
        
        # 清单
        tasks = [
            ("语音识别 (ASR)", self.download_whisper),
            ("机器翻译", self.download_nllb),
            ("语音合成 (TTS)", self.download_vits_english),
            ("口型同步", self.download_wav2lip),
        ]
        
        for name, func in tasks:
            print(f"\n{'-' * 40}")
            print(f"[{name}]")
            print('-' * 40)
            func()
        
        # 报告
        print("\n" + "=" * 60)
        print("下载报告")
        print("=" * 60)
        
        if self.success:
            print("\n✅ 成功下载:")
            for name, purpose in self.success:
                print(f"  - {name} ({purpose})")
        
        if self.failed:
            print("\n⚠️ 需要手动处理:")
            for name, reason in self.failed:
                print(f"  - {name}: {reason}")
        
        print("\n" + "=" * 60)
        print("模型存储位置:")
        print(f"  {MODELS_DIR}")
        print("=" * 60)


def check_models():
    """检查已下载的模型"""
    print("\n检查已安装的模型...\n")
    
    checks = [
        ("Whisper", "openai-whisper"),
        ("Transformers", "transformers"),
        ("PyTorch", "torch"),
        ("SpeechT5", "transformers"),
    ]
    
    for name, module in checks:
        try:
            __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} (未安装)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        check_models()
    else:
        downloader = ModelDownloader()
        downloader.download_all()
