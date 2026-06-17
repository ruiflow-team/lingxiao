#!/usr/bin/env python3
"""
下载状态监控脚本
"""
import os
from datetime import datetime

def check_size(path):
    try:
        return os.path.getsize(path)
    except:
        return 0

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}TB"

print(f"=== 模型下载状态 ({datetime.now().strftime('%H:%M:%S')}) ===\n")

# NLLB
nllb_path = "/Users/liuxiansheng/lingxiao/models/translation/facebook/nllb-200-distilled-600M/pytorch_model.bin"
nllb_size = check_size(nllb_path)
nllb_total = 2.1 * 1024 * 1024 * 1024  # 2.1GB
nllb_pct = nllb_size / nllb_total * 100
print(f"NLLB-200:     {format_size(nllb_size)} / {format_size(nllb_total)}  ({nllb_pct:.1f}%)")

# SpeechT5
st5_path = "/Users/liuxiansheng/lingxiao/models/tts/microsoft/speecht5_tts/pytorch_model.bin"
st5_size = check_size(st5_path)
st5_total = 600 * 1024 * 1024  # 600MB
st5_pct = st5_size / st5_total * 100
print(f"SpeechT5:     {format_size(st5_size)} / {format_size(st5_total)}  ({st5_pct:.1f}%)")

# Wav2Lip
wav2lip_path = "/Users/liuxiansheng/lingxiao/models/wav2lip/checkpoints/wav2lip_gan.pth"
wav2lip_size = check_size(wav2lip_path)
print(f"Wav2Lip:      {format_size(wav2lip_size)}  (✓已完成)")

# Whisper
whisper_path = "/Users/liuxiansheng/.cache/whisper/small.pt"
whisper_size = check_size(whisper_path)
print(f"Whisper:      {format_size(whisper_size)}  (✓已完成)")

print(f"\n总进度: {((nllb_size + st5_size) / (nllb_total + st5_total) * 100):.1f}%")
