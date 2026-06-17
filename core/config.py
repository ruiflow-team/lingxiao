"""
凌霄智能影视翻译系统 - 核心配置
"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 模型目录
MODEL_DIR = PROJECT_ROOT / "models"
WHISPER_MODEL_DIR = MODEL_DIR / "whisper"
VITS_MODEL_DIR = MODEL_DIR / "vits"
WAV2LIP_MODEL_DIR = MODEL_DIR / "wav2lip"

# Whisper.cpp 配置
WHISPER_CPP_DIR = PROJECT_ROOT / "deps" / "whisper.cpp"
WHISPER_MAIN = WHISPER_CPP_DIR / "build" / "bin" / "main"
WHISPER_MODEL_DEFAULT = WHISPER_MODEL_DIR / "ggml-base.en.bin"

# VITS 模型配置
VITS_MODEL_PATH = VITS_MODEL_DIR / "bert_vits2" / "model.pth"
VITS_CONFIG_PATH = VITS_MODEL_DIR / "bert_vits2" / "config.json"

# MiniMax API 配置
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_API_BASE = "https://api.minimaxi.chat/v1"

# Vast.ai 配置
VAST_API_KEY = os.environ.get("VAST_API_KEY", "")

# 临时文件目录
TEMP_DIR = PROJECT_ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# 输出目录
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# 日志
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 支持的视频格式
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}

# 支持的语言
SUPPORTED_LANGUAGES = {
    "en": "English",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian",
    "ar": "Arabic",
    "pt": "Portuguese",
    "it": "Italian",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
}

# 默认配置
DEFAULT_CONFIG = {
    "asr_model": "base",  # tiny, base, small, medium, large
    "asr_language": "auto",  # auto 或具体语言代码
    "translation_target": "zh",  # 翻译目标语言
    "tts_voice": "female_yunyang",  # 默认音色
    "tts_speed": 1.0,  # 语速
    "lip_sync": True,  # 是否启用口型同步
    "output_format": "mp4",  # mp4, mkv
    "video_quality": "high",  # low, medium, high
}

# GPU 配置
def check_gpu():
    """检测 GPU 可用性"""
    try:
        import torch
        if torch.cuda.is_available():
            return {
                "available": True,
                "name": torch.cuda.get_device_name(0),
                "vram_gb": torch.cuda.get_device_properties(0).total_memory / (1024**3),
            }
    except ImportError:
        pass
    
    # 检查 Apple Silicon
    try:
        import subprocess
        result = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
        if "Apple" in result.stdout:
            return {"available": True, "name": "Apple Silicon", "vram_gb": "shared"}
    except:
        pass
    
    return {"available": False, "name": "CPU", "vram_gb": 0}